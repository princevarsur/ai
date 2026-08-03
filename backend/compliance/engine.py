"""
THEMIS Compliance Engine — full scan pipeline orchestrator.

Combines all ML modules into a single scan workflow:
  1. Text extraction
  2. Clause splitting
  3. Rule-based keyword checking
  4. AI semantic matching
  5. Quantity check (deterministic numeric conflicts)
  6. NLI contradiction detection
  7. Risk scoring
  8. DB persistence (ScanReport + FlaggedIssues)
"""

import time
import logging

from laws.models import LegalRule
from compliance.models import ScanReport, FlaggedIssue
from policies.models import Policy

from ml_engine.text_extractor import extract_text
from ml_engine.clause_extractor import extract_clauses, get_clause_stats
from ml_engine.rule_checker import check_rules, get_rule_check_summary
from ml_engine.semantic_matcher import precompute_law_embeddings, batch_match_clauses
from ml_engine.risk_scorer import calculate_issue_severity, calculate_overall_score
from ml_engine.quantity_checker import check_quantity_conflict
from ml_engine.contradiction_checker import batch_check_entailment

logger = logging.getLogger(__name__)

# ── Decision model (trained LogisticRegression) ───────────────────────────
# Loaded lazily — falls back to threshold logic if model file absent.
# Re-train with: python ml_engine/decision_model.py

from pathlib import Path as _Path
import numpy as _np

_DECISION_MODEL_PATH = _Path(__file__).resolve().parent.parent / "data" / "decision_model.joblib"
_decision_model = None
_decision_model_loaded = False  # tracks whether load was attempted


def _get_decision_model():
    """Lazy-load saved LogisticRegression. Returns None if not found."""
    global _decision_model, _decision_model_loaded
    if _decision_model_loaded:
        return _decision_model
    _decision_model_loaded = True
    if _DECISION_MODEL_PATH.exists():
        try:
            import joblib
            _decision_model = joblib.load(_DECISION_MODEL_PATH)
            logger.info("Decision model loaded from %s", _DECISION_MODEL_PATH)
        except Exception as e:
            logger.warning("Could not load decision model: %s", e)
            _decision_model = None
    else:
        logger.info("No decision model found — using threshold pipeline")
    return _decision_model

# spaCy model for quantity extraction — loaded once
_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        import spacy
        _nlp = spacy.load("en_core_web_sm")
    return _nlp

# ── Law embedding cache (computed once, reused across scans) ─────────────

_law_cache = None


def _get_law_cache() -> dict:
    """Load and cache law embeddings. Recomputes if cache is empty."""
    global _law_cache
    if _law_cache is None:
        laws = LegalRule.objects.filter(is_active=True)
        law_data = [{"id": law.id, "text": law.requirement_text} for law in laws]
        _law_cache = precompute_law_embeddings(law_data)
        _law_cache["rules"] = {law.id: law for law in laws}
        logger.info("Law embeddings cached: %d rules", len(law_data))
    return _law_cache


def invalidate_law_cache():
    """Call when LegalRules are updated to force re-computation."""
    global _law_cache
    _law_cache = None


# ── Main scan pipeline ───────────────────────────────────────────────────


def run_compliance_scan(policy_id: int, user) -> ScanReport:
    """
    Full compliance scan pipeline.

    Steps:
      1. Load policy, extract text from file
      2. Split into clauses
      3. Rule-based keyword check
      4. AI semantic matching (MiniLM + InLegal-SBERT)
      5. Determine status for each law requirement
      6. Score severity per issue
      7. Calculate overall compliance score
      8. Persist ScanReport + FlaggedIssues to DB
      9. Update policy metadata

    Args:
        policy_id: ID of the Policy to scan
        user: The User performing the scan

    Returns:
        ScanReport instance (saved to DB)
    """
    start_time = time.time()

    # ── Step 1: Load policy and extract text ──────────────────────────
    policy = Policy.objects.get(id=policy_id)
    logger.info("Scanning policy: %s (id=%d)", policy.title, policy.id)

    extraction = extract_text(str(policy.file.path))
    full_text = extraction["text"]

    # Update policy metadata
    if not policy.extracted_text:
        policy.extracted_text = full_text
        policy.file_type = extraction["file_type"]

    # ── Step 2: Split into clauses ───────────────────────────────────
    clauses = extract_clauses(full_text)
    clause_stats = get_clause_stats(clauses)
    total_clauses = clause_stats["total_clauses"]

    policy.clause_count = total_clauses
    policy.save(update_fields=["extracted_text", "file_type", "clause_count"])

    logger.info("Extracted %d clauses from policy", total_clauses)

    # ── Step 3: Rule-based keyword check ─────────────────────────────
    rule_results = check_rules(full_text, clauses)
    rule_summary = get_rule_check_summary(rule_results)

    # Index rule results by legal_rule_id for fast lookup
    rule_status_map = {
        r["legal_rule_id"]: r for r in rule_results
    }

    logger.info(
        "Rule check: %d present, %d missing",
        rule_summary["present_count"],
        rule_summary["missing_count"],
    )

    # ── Step 4: AI semantic matching ─────────────────────────────────
    law_cache = _get_law_cache()
    semantic_results = batch_match_clauses(
        clauses, law_cache, similarity_threshold=0.3
    )

    # Build best semantic match per legal_rule_id across all clauses
    best_semantic = _build_best_semantic_map(semantic_results)

    logger.info("Semantic matching complete for %d clauses", len(clauses))

    # ── Step 5-7: Determine status, run quantity+NLI checks, score ───
    all_rules = LegalRule.objects.filter(is_active=True)
    flagged_issues = []
    compliant_count = 0
    nlp = _get_nlp()

    # Track similarity scores for averages
    all_miniml_scores = []
    all_inlegal_scores = []

    # Pre-collect NLI pairs for rules above similarity threshold
    # (avoids per-call latency — batch at the end)
    nli_candidates = []   # [(rule_id, clause_text, law_text), ...]

    # First pass: collect candidates for NLI batching
    rule_data = {}  # rule.id → {keyword_found, best_match, miniml, inlegal, combined}
    for rule in all_rules:
        rule_result = rule_status_map.get(rule.id, {})
        keyword_found = rule_result.get("status") == "PRESENT"
        best_match = best_semantic.get(rule.id)

        miniml_sim = best_match["miniml_similarity"] if best_match else 0.0
        inlegal_sim = best_match["inlegal_similarity"] if best_match else 0.0
        combined_sim = best_match["combined_score"] if best_match else 0.0

        all_miniml_scores.append(miniml_sim)
        all_inlegal_scores.append(inlegal_sim)

        rule_data[rule.id] = {
            "rule": rule,
            "rule_result": rule_result,
            "keyword_found": keyword_found,
            "best_match": best_match,
            "miniml_sim": miniml_sim,
            "inlegal_sim": inlegal_sim,
            "combined_sim": combined_sim,
        }

        # Collect for NLI if semantically relevant (combined > 0.3)
        if combined_sim >= 0.3 and best_match:
            clause_text = best_match["clause_text"]
            nli_candidates.append((rule.id, clause_text, rule.requirement_text))

    # Batch NLI inference for all candidates in one call
    nli_pairs = [(clause, law) for _, clause, law in nli_candidates]
    nli_results = batch_check_entailment(nli_pairs)
    nli_map = {}
    for (rule_id, _, _), nli_result in zip(nli_candidates, nli_results):
        nli_map[rule_id] = nli_result

    # Second pass: make decisions
    decision_model = _get_decision_model()
    for rule in all_rules:
        rd = rule_data[rule.id]
        keyword_found = rd["keyword_found"]
        best_match = rd["best_match"]
        combined_sim = rd["combined_sim"]
        miniml_sim = rd["miniml_sim"]
        inlegal_sim = rd["inlegal_sim"]
        rule_result = rd["rule_result"]
        nli_result = nli_map.get(rule.id)

        clause_text, clause_index = _find_relevant_clause(
            rule, best_match, rule_result, clauses
        )

        status = None
        nli_label = nli_result["label"] if nli_result else ""
        qty_conflict = False
        catch_signal = "similarity"

        # ── Always run quantity check (deterministic, high precision) ────
        if rule.required_value is not None and combined_sim >= 0.3:
            qty = check_quantity_conflict(
                clause_text,
                rule.required_value,
                rule.required_unit,
                rule.comparison_type,
                nlp,
            )
            if qty["has_quantity"]:
                if qty["is_conflict"]:
                    status = "CONFLICT"
                    qty_conflict = True
                    catch_signal = "quantity check"
                else:
                    compliant_count += 1
                    continue

        # ── Decision: trained classifier or threshold fallback ────────────
        if status is None:
            if decision_model is not None:
                # Assemble feature vector matching decision_model.py training
                nli_contra = nli_result["raw_scores"]["contradiction"] if nli_result else 0.0
                nli_entail = nli_result["raw_scores"]["entailment"] if nli_result else 0.0
                nli_neut = nli_result["raw_scores"]["neutral"] if nli_result else 1.0
                feat = _np.array([[miniml_sim, inlegal_sim, nli_contra,
                                   nli_entail, nli_neut,
                                   float(qty_conflict), float(keyword_found)]])
                is_flagged = bool(decision_model.predict(feat)[0])
                catch_signal = "decision model"

                if not is_flagged:
                    compliant_count += 1
                    continue

                # Determine status label from NLI + quantity signals
                if nli_label == "contradiction" or qty_conflict:
                    status = "CONFLICT"
                elif keyword_found:
                    status = "GAP"
                else:
                    status = "MISSING"

            else:
                # ── Threshold fallback (priority chain) ──────────────────
                # Priority 2: NLI contradiction/entailment
                if nli_result is not None:
                    nli_conf = nli_result["confidence"]
                    if nli_label == "contradiction":
                        status = "CONFLICT"
                        catch_signal = f"NLI contradiction (confidence {nli_conf:.0%})"
                    elif nli_label == "entailment" and combined_sim >= 0.6:
                        compliant_count += 1
                        continue
                    elif nli_label == "neutral" or (
                        nli_label == "entailment" and combined_sim < 0.6
                    ):
                        status = "GAP"
                        catch_signal = "NLI neutral / low similarity"

                # Priority 3: Similarity + keyword fallback
                if status is None:
                    status = _determine_status(keyword_found, combined_sim)

        if status is None:
            compliant_count += 1
            continue

        # Calculate severity
        severity = calculate_issue_severity(
            rule_status=status,
            max_similarity=combined_sim,
            severity_weight=rule.severity_weight,
            keyword_found=keyword_found,
        )

        # Generate description mentioning which signal caught the issue
        description = _generate_description(
            rule, status, keyword_found, combined_sim,
            clause_text, rule_result, catch_signal, nli_result,
        )

        flagged_issues.append({
            "legal_rule": rule,
            "clause_text": clause_text,
            "clause_index": clause_index,
            "status": status.lower(),
            "severity_score": severity,
            "miniml_similarity": miniml_sim,
            "inlegal_similarity": inlegal_sim,
            "description": description,
            "category": rule.category,
            "nli_label": nli_label,
            "quantity_conflict": qty_conflict,
        })

    logger.info(
        "Analysis: %d compliant, %d flagged out of %d rules",
        compliant_count, len(flagged_issues), len(all_rules),
    )

    # ── Step 7: Calculate overall score ──────────────────────────────
    score_data = calculate_overall_score(
        total_rules=len(all_rules),
        flagged_issues=[
            {"severity_score": f["severity_score"], "category": f["category"]}
            for f in flagged_issues
        ],
        total_clauses=total_clauses,
    )

    # Average similarity scores
    miniml_avg = (
        sum(all_miniml_scores) / len(all_miniml_scores)
        if all_miniml_scores else 0.0
    )
    inlegal_avg = (
        sum(all_inlegal_scores) / len(all_inlegal_scores)
        if all_inlegal_scores else 0.0
    )

    duration = time.time() - start_time

    # ── Step 8: Persist to DB ────────────────────────────────────────
    report = ScanReport.objects.create(
        policy=policy,
        overall_score=score_data["overall_score"],
        risk_level=score_data["risk_level"],
        total_clauses=total_clauses,
        compliant_clauses=compliant_count,
        flagged_clauses=len(flagged_issues),
        scan_duration_seconds=round(duration, 2),
        miniml_avg_score=round(miniml_avg, 4),
        inlegal_avg_score=round(inlegal_avg, 4),
        scanned_by=user,
    )

    # Bulk create flagged issues
    issue_objects = []
    for fi in flagged_issues:
        issue_objects.append(FlaggedIssue(
            report=report,
            legal_rule=fi["legal_rule"],
            clause_text=fi["clause_text"],
            clause_index=fi["clause_index"],
            status=fi["status"],
            severity_score=fi["severity_score"],
            miniml_similarity=fi["miniml_similarity"],
            inlegal_similarity=fi["inlegal_similarity"],
            description=fi["description"],
            nli_label=fi.get("nli_label", ""),
            quantity_conflict=fi.get("quantity_conflict", False),
            is_resolved=False,
        ))

    if issue_objects:
        FlaggedIssue.objects.bulk_create(issue_objects)

    logger.info(
        "Scan complete: score=%.1f%% risk=%s duration=%.2fs issues=%d",
        report.overall_score, report.risk_level,
        report.scan_duration_seconds, len(issue_objects),
    )

    return report


# ── Internal helpers ─────────────────────────────────────────────────────


def _build_best_semantic_map(semantic_results: list[dict]) -> dict:
    """
    From batch_match_clauses output, find the BEST match per
    legal_rule_id across all clauses.

    Returns: {legal_rule_id: {"miniml_similarity", "inlegal_similarity",
              "combined_score", "clause_index", "clause_text"}}
    """
    best = {}

    for clause_result in semantic_results:
        clause_idx = clause_result["clause_index"]
        clause_text = clause_result["clause_text"]

        for match in clause_result.get("matches", []):
            rule_id = match["legal_rule_id"]
            combined = match["combined_score"]

            if rule_id not in best or combined > best[rule_id]["combined_score"]:
                best[rule_id] = {
                    "miniml_similarity": match["miniml_similarity"],
                    "inlegal_similarity": match["inlegal_similarity"],
                    "combined_score": combined,
                    "clause_index": clause_idx,
                    "clause_text": clause_text,
                }

    return best


def _determine_status(keyword_found: bool, combined_sim: float) -> str | None:
    """
    Similarity + keyword fallback — only called after quantity and NLI checks
    have had first priority.

    Returns:
        None if compliant, or "MISSING" / "CONFLICT" / "GAP"
    """
    if keyword_found and combined_sim >= 0.7:
        return None  # COMPLIANT

    if not keyword_found and combined_sim < 0.4:
        return "MISSING"

    if keyword_found and combined_sim >= 0.6:
        return "CONFLICT"

    if keyword_found and combined_sim < 0.6:
        return "GAP"

    if not keyword_found and combined_sim >= 0.4:
        return "GAP"

    return "MISSING"


def _find_relevant_clause(
    rule, best_match: dict | None, rule_result: dict, clauses: list[dict]
) -> tuple[str, int]:
    """Find the most relevant clause text and index for a flagged issue."""
    # Prefer semantic match clause (more accurate)
    if best_match and best_match.get("clause_text"):
        text = best_match["clause_text"]
        # Truncate very long clauses
        if len(text) > 500:
            text = text[:500] + "..."
        return text, best_match.get("clause_index", 0)

    # Fall back to rule checker's matched clause
    matched_idx = rule_result.get("matched_clause_index")
    if matched_idx and clauses:
        for clause in clauses:
            if clause.get("index") == matched_idx:
                text = clause["text"]
                if len(text) > 500:
                    text = text[:500] + "..."
                return text, matched_idx

    # No specific clause — use a placeholder
    return (
        f"[No matching clause found in document for: "
        f"{rule.law_name} {rule.section}]"
    ), 0


def _generate_description(
    rule,
    status: str,
    keyword_found: bool,
    combined_sim: float,
    clause_text: str,
    rule_result: dict,
    catch_signal: str = "similarity",
    nli_result: dict | None = None,
) -> str:
    """Generate human-readable description mentioning which signal caught the issue."""
    law_ref = f"{rule.law_name} {rule.section}"
    signal_note = f"(Caught by: {catch_signal})"

    if status == "MISSING":
        return (
            f"The policy does not address the requirement under {law_ref}. "
            f"This section requires: {rule.requirement_text[:200]}. "
            f"No matching keywords or semantically similar clauses were "
            f"found in the document. {signal_note}"
        )

    if status == "CONFLICT":
        clause_preview = clause_text[:150].replace("\n", " ")
        if nli_result and nli_result["label"] == "contradiction":
            conf_pct = f"{nli_result['confidence']:.0%}"
            return (
                f"Direct contradiction detected with {law_ref}. "
                f"The policy states: \"{clause_preview}\" — this directly "
                f"contradicts the requirement: \"{rule.requirement_text[:150]}...\" "
                f"{signal_note}, confidence {conf_pct}."
            )
        return (
            f"Conflict detected with {law_ref}. "
            f"The policy states: \"{clause_preview}...\" "
            f"However, the law requires: \"{rule.requirement_text[:150]}...\" "
            f"(Semantic similarity: {combined_sim:.0%}) {signal_note}"
        )

    if status == "GAP":
        clause_preview = clause_text[:150].replace("\n", " ")
        kw_note = (
            "Relevant keywords were found"
            if keyword_found
            else "No exact keywords were found"
        )
        return (
            f"Partial compliance gap with {law_ref}. "
            f"{kw_note}, but the coverage appears incomplete. "
            f"The policy mentions: \"{clause_preview}...\" "
            f"The full requirement is: \"{rule.requirement_text[:150]}...\" "
            f"(Semantic similarity: {combined_sim:.0%}) {signal_note}"
        )

    return f"Issue flagged for {law_ref}: {rule.requirement_text[:200]} {signal_note}"
