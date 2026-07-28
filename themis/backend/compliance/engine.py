"""
THEMIS Compliance Engine — full scan pipeline orchestrator.

Combines all ML modules into a single scan workflow:
  1. Text extraction
  2. Clause splitting
  3. Rule-based keyword checking
  4. AI semantic matching
  5. Risk scoring
  6. DB persistence (ScanReport + FlaggedIssues)
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

logger = logging.getLogger(__name__)

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

    # ── Step 5-6: Determine status and score each issue ──────────────
    all_rules = LegalRule.objects.filter(is_active=True)
    flagged_issues = []
    compliant_count = 0

    # Track similarity scores for averages
    all_miniml_scores = []
    all_inlegal_scores = []

    for rule in all_rules:
        rule_result = rule_status_map.get(rule.id, {})
        keyword_found = rule_result.get("status") == "PRESENT"
        best_match = best_semantic.get(rule.id)

        # Get similarity scores
        miniml_sim = best_match["miniml_similarity"] if best_match else 0.0
        inlegal_sim = best_match["inlegal_similarity"] if best_match else 0.0
        combined_sim = best_match["combined_score"] if best_match else 0.0

        all_miniml_scores.append(miniml_sim)
        all_inlegal_scores.append(inlegal_sim)

        # Determine issue status
        status = _determine_status(keyword_found, combined_sim)

        if status is None:
            # COMPLIANT — keyword found AND strong semantic match
            compliant_count += 1
            continue

        # Find the clause text that triggered this
        clause_text, clause_index = _find_relevant_clause(
            rule, best_match, rule_result, clauses
        )

        # Calculate severity
        severity = calculate_issue_severity(
            rule_status=status,
            max_similarity=combined_sim,
            severity_weight=rule.severity_weight,
            keyword_found=keyword_found,
        )

        # Generate human-readable description
        description = _generate_description(
            rule, status, keyword_found, combined_sim,
            clause_text, rule_result,
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
    Determine compliance status for one rule.

    Returns:
        None if compliant, or "MISSING" / "CONFLICT" / "GAP"
    """
    if keyword_found and combined_sim >= 0.7:
        # Keyword present AND strong semantic alignment — compliant
        return None

    if not keyword_found and combined_sim < 0.4:
        # No keyword, no semantic similarity — completely missing
        return "MISSING"

    if keyword_found and combined_sim >= 0.6:
        # Keyword found but semantic match suggests the clause may
        # conflict with the requirement (topic match, different stance)
        return "CONFLICT"

    if keyword_found and combined_sim < 0.6:
        # Keyword found but weak semantic match — partial coverage
        return "GAP"

    if not keyword_found and combined_sim >= 0.4:
        # No exact keyword but semantically related — gap in coverage
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
) -> str:
    """Generate human-readable description of a flagged issue."""
    law_ref = f"{rule.law_name} {rule.section}"

    if status == "MISSING":
        return (
            f"The policy does not address the requirement under {law_ref}. "
            f"This section requires: {rule.requirement_text[:200]}. "
            f"No matching keywords or semantically similar clauses were "
            f"found in the document."
        )

    if status == "CONFLICT":
        # Show what the policy says vs what the law requires
        clause_preview = clause_text[:150].replace("\n", " ")
        return (
            f"Potential conflict detected with {law_ref}. "
            f"The policy states: \"{clause_preview}...\" "
            f"However, the law requires: \"{rule.requirement_text[:150]}...\" "
            f"(Semantic similarity: {combined_sim:.0%})"
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
            f"(Semantic similarity: {combined_sim:.0%})"
        )

    return f"Issue flagged for {law_ref}: {rule.requirement_text[:200]}"
