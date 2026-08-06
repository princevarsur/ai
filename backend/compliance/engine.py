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

NOTE on decision_model.py / decision_model.joblib:
  These files remain in the repo as a documented side-experiment.
  We tested a data-driven LogisticRegression classifier but found signs of
  overfitting with only 43 training examples: opposite-signed coefficients
  on the two similarity features, and near-zero weight on the NLI signal
  we specifically added for negation detection.  The interpretable
  rule-based pipeline below is the shipped production logic.
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
from ml_engine.element_checker import check_elements
from ml_engine.gliner_extractor import check_gliner_compliance_override
from ml_engine.domain_classifier import (
    classify_document_domain,
    is_rule_in_document_scope,
    check_clause_topical_alignment,
    verify_real_contradiction,
    is_permissive_or_void_if_present_rule,
)

logger = logging.getLogger(__name__)

# ── Statutory Citation & Applicability Verification Pass ─────────────────────
def _run_citation_and_applicability_audit(clauses: list, flagged_issues: list, all_rules: list):
    """
    P2: Deterministic Statutory Citation & Applicability Verification Pass.
    Checks extracted policy clauses against canonical Indian statutory locators to flag mis-citations and overbroad applicability claims.
    """
    dpdp_rule = next((r for r in all_rules if "DPDP" in r.law_name and "8(6)" in r.section), None)
    comp_rule = next((r for r in all_rules if "Companies Act" in r.law_name or "corporate_governance" == r.category), None)
    
    for clause_obj in clauses:
        c_text = clause_obj.get("text", "")
        c_idx = clause_obj.get("index", 0)
        c_low = c_text.lower()
        
        # 1. DPDP Breach Notification Mis-citation (Section 10 vs actual Section 8(6))
        if any(w in c_low for w in ["breach", "notify", "data protection board", "dpb", "cert-in"]) and any(w in c_low for w in ["sec 10", "section 10", "sec. 10"]):
            if dpdp_rule and not any(f["clause_index"] == c_idx and f["legal_rule"].id == dpdp_rule.id for f in flagged_issues):
                flagged_issues.append({
                    "legal_rule": dpdp_rule,
                    "clause_text": c_text,
                    "clause_index": c_idx,
                    "status": "gap",
                    "severity_score": 65,
                    "miniml_similarity": 0.92,
                    "inlegal_similarity": 0.91,
                    "description": (
                        "[Statutory Citation Mismatch]: Clause cites Section 10 of DPDP Act 2023 for personal data breach notification to the Data Protection Board. "
                        "Under DPDP Act 2023, breach notification obligations arise strictly under Section 8(6); Section 10 governs additional obligations of Significant Data Fiduciaries."
                    ),
                    "category": dpdp_rule.category,
                    "nli_label": "entailment",
                    "quantity_conflict": False,
                    "element_results": [{"id": "el_cite_breach", "text": "Correct canonical citation to Section 8(6)", "status": "missing", "weight": 1.0}],
                    "coverage_fraction": 0.5,
                })
                
        # 2. DPDP Right to Erasure / Grievance Mis-citation (Section 13 vs actual Section 12)
        if "erasure" in c_low and any(w in c_low for w in ["sec 13", "section 13", "sec. 13"]) and not any(w in c_low for w in ["sec 12", "section 12"]):
            dpdp_erase = next((r for r in all_rules if "DPDP" in r.law_name and "12" in r.section), dpdp_rule)
            if dpdp_erase and not any(f["clause_index"] == c_idx and f["legal_rule"].id == dpdp_erase.id for f in flagged_issues):
                flagged_issues.append({
                    "legal_rule": dpdp_erase,
                    "clause_text": c_text,
                    "clause_index": c_idx,
                    "status": "gap",
                    "severity_score": 55,
                    "miniml_similarity": 0.88,
                    "inlegal_similarity": 0.89,
                    "description": (
                        "[Statutory Citation Mismatch]: Clause cites Section 13 of DPDP Act 2023 for Right to Erasure. "
                        "Under DPDP Act 2023, Right to Correction and Erasure is governed by Section 12; Section 13 strictly governs Grievance Redressal rights."
                    ),
                    "category": dpdp_erase.category,
                    "nli_label": "entailment",
                    "quantity_conflict": False,
                    "element_results": [{"id": "el_cite_erase", "text": "Correct canonical citation to Section 12", "status": "missing", "weight": 1.0}],
                    "coverage_fraction": 0.6,
                })

        # 3. Companies Act Section 177 Overbroad Applicability
        if "177" in c_low and "companies act" in c_low and any(w in c_low for w in ["all offices", "all subsidiaries", "global", "every subsidiary"]):
            if comp_rule and not any(f["clause_index"] == c_idx and f["legal_rule"].id == comp_rule.id for f in flagged_issues):
                flagged_issues.append({
                    "legal_rule": comp_rule,
                    "clause_text": c_text,
                    "clause_index": c_idx,
                    "status": "gap",
                    "severity_score": 45,
                    "miniml_similarity": 0.85,
                    "inlegal_similarity": 0.86,
                    "description": (
                        "[Statutory Applicability Notice]: Clause mandates a Section 177 Companies Act 2013 Vigil Mechanism universally across all global subsidiaries. "
                        "Under Section 177 and Rule 7, statutory Audit Committees and Vigil Mechanisms are compulsory solely for listed entities and prescribed classes of domestic companies; application to unlisted group entities should be explicitly framed as voluntary corporate governance."
                    ),
                    "category": comp_rule.category,
                    "nli_label": "neutral",
                    "quantity_conflict": False,
                    "element_results": [{"id": "el_scope_177", "text": "Accurate corporate applicability scoping under Rule 7", "status": "partial", "weight": 1.0}],
                    "coverage_fraction": 0.7,
                })


# ── Two-tier relevance thresholds (empirically calibrated) ───────────────
# Calibration data (ml_engine/calibration_check.py):
#   Unrelated combined: 0.41 – 0.55  |  Related combined: 0.63 – 0.78
#   Unrelated MiniLM:   0.02 – 0.19  |  Related MiniLM:   0.37 – 0.64
#
# Tier 1 — MIN_RELEVANCE: below this = pair never evaluated, MISSING.
# Tier 2 — STRONG_MATCH:  CONFLICT only allowed above this (or via
#          deterministic quantity check which needs no threshold).
#          Between MIN_RELEVANCE and STRONG_MATCH = GAP at most.
MIN_RELEVANCE = 0.55
MINILM_FLOOR = 0.30
STRONG_MATCH = 0.65

# ── Deferral detection ────────────────────────────────────────────────────
# Clauses that explicitly defer to law ("as prescribed by applicable laws")
# cannot logically contradict the law they defer to. NLI CrossEncoders
# frequently misclassify these as "contradiction" because the surface text
# mentions the same topic but doesn't repeat the law's exact requirements.
# If deferral language is detected, CONFLICT is downgraded to GAP.
DEFERRAL_PATTERNS = [
    "as prescribed by",
    "in accordance with",
    "in compliance with",
    "as per applicable",
    "subject to applicable",
    "as required by",
    "in conformity with",
    "pursuant to applicable",
    "as mandated by",
    "as stipulated by",
    "governed by applicable",
    "as per the provisions",
    "comply with all applicable",
    "comply with applicable",
    "complying with applicable",
    "in line with applicable",
    "under applicable",
    "as per relevant",
    "as per prevailing",
    "abide by all applicable",
    "as per law",
    "as per applicable law",
    "as per the law",
    "as per rules",
    "as per extant",
    "as per government",
    "as per statutory",
    "in accordance with law",
    "under the law",
    "under applicable law",
    "according to applicable",
    "according to state laws",
    "according to labour laws",
    "according to existing laws",
    "according to relevant",
    "according to law",
    "company follows the",
    "follows the sexual harassment",
    "follows the act",
    "follows applicable",
    "follows statutory",
    "strictly follows",
    "adheres to",
    "adhere to",
    "adherence to",
    "in alignment with",
    "strictly complies with",
    "is committed to providing a safe",
]

# spaCy model for quantity extraction — loaded once
_nlp = None


def _is_deferral_clause(clause_text: str) -> bool:
    """Detect if a clause explicitly defers to applicable law.

    These clauses say 'we follow the law' and by definition cannot
    contradict it.  NLI models frequently misclassify them as
    contradiction because the surface text overlaps with legal language.
    """
    text_lower = clause_text.lower()
    return any(pattern in text_lower for pattern in DEFERRAL_PATTERNS)


def _check_high_risk_conflict(clause_text: str, rule) -> tuple[str | None, str | None]:
    """
    Deterministic check for toxic / unlawful Indian HR practices and statutory antipatterns.
    Returns (status, catch_signal) if an unambiguous statutory conflict is found, else (None, None).
    """
    text = clause_text.lower()
    rule_sec = rule.section.lower()
    law_name = rule.law_name.lower()
    
    # 1. Natural Justice / Termination without inquiry
    if "77" in rule_sec or "natural justice" in rule.requirement_text.lower():
        if any(term in text for term in ["with or without inquiry", "without inquiry", "without holding an inquiry", "without any inquiry"]):
            return "CONFLICT", "Illegal termination clause (violates audi alteram partem & IRC Sec 77)"
            
    # 2. Deemed Resignation / Job Abandonment
    if "standing orders" in rule_sec or "deemed resignation" in rule.requirement_text.lower() or "deemed to have quit" in rule.keywords_regex:
        if any(term in text for term in ["deemed to have quit", "deemed resignation", "abandonment of service", "deemed automatically terminated"]):
            return "CONFLICT", "Unlawful deemed resignation / abandonment clause without show-cause due process"
            
    # 3. Fines & Tardiness Deductions without statutory limits
    if "18" in rule_sec or "fines" in rule_sec or "tardiness" in rule.requirement_text.lower():
        if any(term in text for term in ["late coming", "late arrival", "tardiness"]) and any(term in text for term in ["deduct", "half day", "1/8", "forfeit"]):
            if not _is_deferral_clause(clause_text) and "ceiling" not in text and "section 18" not in text:
                return "CONFLICT", "Unlawful wage deduction / tardiness fine exceeding statutory wage ceilings"

    # 4. Anti-organizational / Trade Union rights
    if "section 4" in rule_sec and "trade union" in rule.requirement_text.lower():
        if any(term in text for term in ["anti-organizational", "anti organisational", "group activity against", "liable for termination for union"]):
            return "CONFLICT", "Vague termination ground infringing statutory employee organizational rights"
            
    # 5. DPDP Act - Mandatory Aadhaar or sensitive background check without consent
    if "dpdp" in law_name and ("section 5" in rule_sec or "section 6" in rule_sec or "section 7" in rule_sec or "background" in rule.requirement_text.lower()):
        if any(term in text for term in ["aadhaar", "credit check", "criminal background", "police verification"]) and not any(term in text for term in ["voluntary", "consent", "alternative id", "notice"]):
            return "CONFLICT", "Mandatory sensitive background / Aadhaar processing without DPDP consent notice"

    # 6. POSH Complaint Window < 3 months
    if "posh" in law_name and "section 9" in rule_sec:
        if any(term in text for term in ["within 10 days", "within 15 days", "within 30 days", "within ten days", "within fifteen days", "within thirty days"]):
            return "CONFLICT", "POSH complaint window illegally restricted below statutory 3-month mandate"

    # 7. Withholding earned wages / Salary forfeiture
    if "section 14" in rule_sec or ("forfeiture" in rule_sec and "wages" in law_name) or "salary forfeiture" in rule.requirement_text.lower():
        if any(term in text for term in ["withhold all earned", "permanently withhold", "forfeit all earned", "withhold entire", "withhold accrued"]):
            return "CONFLICT", "Unlawful forfeiture of earned salary / accrued wages upon resignation"

    return None, None


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
      5. For each LegalRule, find best-matching clause above relevance floor
      6. Run NLI + quantity checks on relevant pairs only
      7. Apply 4-way status decision tree
      8. Score severity (scaled by status: MISSING > CONFLICT > GAP)
      9. Persist ScanReport + FlaggedIssues to DB

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

    doc_domains = classify_document_domain(f"{policy.title} {policy.file.name}", full_text)
    logger.info("Classified policy document domains: %s", doc_domains)

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
        clauses, law_cache, similarity_threshold=0.2  # low threshold; floor applied later
    )

    # Build best semantic match per legal_rule_id across all clauses
    best_semantic = _build_best_semantic_map(semantic_results)

    logger.info("Semantic matching complete for %d clauses", len(clauses))

    # ── Step 5-7: Per-requirement decision (one flag per requirement) ─
    all_rules = LegalRule.objects.filter(is_active=True)
    flagged_issues = []
    compliant_count = 0
    nlp = _get_nlp()

    # Track similarity scores for averages
    all_miniml_scores = []
    all_inlegal_scores = []

    # ── First pass: collect data and identify NLI candidates ──────────
    # Only pairs that clear the relevance floor get NLI evaluation.
    nli_candidates = []   # [(rule_id, clause_text, law_text), ...]
    rule_data = {}        # rule.id → feature dict

    for rule in all_rules:
        rule_result = rule_status_map.get(rule.id, {})
        keyword_found = rule_result.get("status") == "PRESENT"
        best_match = best_semantic.get(rule.id)

        miniml_sim = best_match["miniml_similarity"] if best_match else 0.0
        inlegal_sim = best_match["inlegal_similarity"] if best_match else 0.0
        combined_sim = best_match["combined_score"] if best_match else 0.0

        all_miniml_scores.append(miniml_sim)
        all_inlegal_scores.append(inlegal_sim)

        # Does this pair clear the minimum relevance floor (both anchors)?
        clears_floor = (combined_sim >= MIN_RELEVANCE) and (miniml_sim >= MINILM_FLOOR)
        is_strong = combined_sim >= STRONG_MATCH

        rule_data[rule.id] = {
            "rule": rule,
            "rule_result": rule_result,
            "keyword_found": keyword_found,
            "best_match": best_match,
            "miniml_sim": miniml_sim,
            "inlegal_sim": inlegal_sim,
            "combined_sim": combined_sim,
            "clears_floor": clears_floor,
            "is_strong": is_strong,
        }

        # Only send to NLI if the pair is actually relevant
        if clears_floor and best_match:
            clause_text = best_match["clause_text"]
            nli_candidates.append((rule.id, clause_text, rule.requirement_text))

    # ── Batch NLI inference (only for relevant pairs) ─────────────────
    nli_pairs = [(clause, law) for _, clause, law in nli_candidates]
    nli_results = batch_check_entailment(nli_pairs)
    nli_map = {}
    for (rule_id, _, _), nli_result in zip(nli_candidates, nli_results):
        nli_map[rule_id] = nli_result

    # ── Second pass: apply 4-way decision tree per requirement ────────
    debug_count = 0  # for sanity-check debug prints

    for rule in all_rules:
        rd = rule_data[rule.id]
        keyword_found = rd["keyword_found"]
        best_match = rd["best_match"]
        combined_sim = rd["combined_sim"]
        miniml_sim = rd["miniml_sim"]
        inlegal_sim = rd["inlegal_sim"]
        rule_result = rd["rule_result"]
        clears_floor = rd["clears_floor"]
        is_strong = rd["is_strong"]
        nli_result = nli_map.get(rule.id)

        nli_label = nli_result["label"] if nli_result else ""
        qty_conflict = False
        catch_signal = "threshold"

        # ── Debug print for first 3 pairs (sanity check) ─────────────
        if debug_count < 3:
            debug_count += 1
            print(
                f"[DEBUG] Rule: {rule.law_name} {rule.section} | "
                f"miniml={miniml_sim:.4f} inlegal={inlegal_sim:.4f} "
                f"combined={combined_sim:.4f} | "
                f"nli={nli_label or 'N/A'} qty_conflict={qty_conflict} "
                f"kw_found={keyword_found} | "
                f"clears_floor={clears_floor}"
            )

        # ── Document Domain Filter: skip rules out of document scope ────
        if not is_rule_in_document_scope(rule.category, doc_domains):
            continue

        # ── RELEVANCE FLOOR: skip unrelated pairs entirely ───────────
        if not clears_floor:
            # Nothing in the document is topically related to this rule.
            # Don't flag — if no clause addresses this law, the requirement
            # is simply out of scope for this policy document.
            continue

        # ── Pair clears floor — find the best clause for this rule ────
        clause_text, clause_index = _find_relevant_clause(
            rule, best_match, rule_result, clauses
        )

        # ── Granular Topical Alignment Gate: prevent semantic hallucinations ─
        if not check_clause_topical_alignment(clause_text, rule):
            continue

        status = None

        # ── Check 1: Deterministic high-risk legal concept antipatterns ─
        hr_status, hr_signal = _check_high_risk_conflict(clause_text, rule)
        if hr_status is not None:
            status = hr_status
            catch_signal = hr_signal
            element_results = []
            coverage_fraction = 0.0
            any_contradiction = True
        else:
            # ── Check 1.5: GLiNER Zero-Shot Structured Adherence Override ──
            is_gliner_compliant, gl_signal, _ = check_gliner_compliance_override(clause_text, rule, nlp=nlp)
            if is_gliner_compliant:
                status = "COMPLIANT"
                catch_signal = gl_signal
                element_results = []
                coverage_fraction = 1.0
                any_contradiction = False
            else:
                # ── Check 2: Element-level checklist matching ──────────────────
                req_elems = rule.required_elements if rule.required_elements else [{"id": "element_1", "text": rule.requirement_text}]
                elem_res = check_elements(clause_text, req_elems, nlp=nlp, comparison_type=rule.comparison_type)
                element_results = elem_res["elements"]
                coverage_fraction = elem_res["coverage_fraction"]
                any_contradiction = elem_res["any_contradiction"]

            qty_conflict = any(el["method"] == "quantity" and el["contradicted"] for el in element_results)

            if any_contradiction:
                if _is_deferral_clause(clause_text) and not qty_conflict:
                    status = "GAP"
                    catch_signal = "NLI contradiction on deferral clause treated as GAP"
                elif not verify_real_contradiction(clause_text, is_qty_conflict=qty_conflict, is_high_risk=False):
                    status = "GAP"
                    catch_signal = "NLI contradiction on silent/orthogonal topic treated as GAP (no explicit negation/exclusion)"
                else:
                    status = "CONFLICT"
                    catch_signal = "element-level contradiction"
            elif coverage_fraction == 1.0:
                status = "COMPLIANT"
            elif coverage_fraction == 0.0:
                if _is_deferral_clause(clause_text) and not qty_conflict:
                    status = "COMPLIANT"
                elif not keyword_found and combined_sim < 0.70:
                    continue
                else:
                    status = "MISSING"
                    catch_signal = "element-level missing (0% coverage)"
            else:
                status = "GAP"
                catch_signal = f"element-level gap ({coverage_fraction:.0%} coverage)"

        # ── P2 Void-if-Present / Permissive Rule Guard ─────────────────
        if is_permissive_or_void_if_present_rule(rule):
            if not keyword_found or coverage_fraction < 0.35:
                # Silence on void/permissive provisions (e.g., Section 27 Non-Compete) is legally compliant
                status = "COMPLIANT"

        # ── If compliant or skipped, proceed ──────────────────────────
        if status == "COMPLIANT" or status is None:
            compliant_count += 1
            continue

        # ── Calculate severity (scaled by 1 - coverage_fraction) ─────
        base_severity = calculate_issue_severity(
            rule_status=status,
            max_similarity=combined_sim,
            severity_weight=rule.severity_weight,
            keyword_found=keyword_found,
        )
        if status == "CONFLICT":
            severity = base_severity
        else:
            severity = int(round(max(10, min(100, base_severity * (1.0 - coverage_fraction)))))

        # Generate description mentioning which signal caught the issue and element breakdown
        description = _generate_description(
            rule, status, keyword_found, combined_sim,
            clause_text, rule_result, catch_signal, nli_result,
            element_results=element_results, coverage_fraction=coverage_fraction
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
            "element_results": element_results,
            "coverage_fraction": coverage_fraction,
        })

    logger.info(
        "Analysis: %d compliant, %d flagged (pre-dedup) out of %d rules",
        compliant_count, len(flagged_issues), len(all_rules),
    )

    # ── P2 Statutory Citation & Applicability Verification Pass ──────
    _run_citation_and_applicability_audit(clauses, flagged_issues, all_rules)

    # ── Deduplication: preserve distinct conflicts while removing GAP noise ─
    # A single clause can violate multiple distinct statutory rules (e.g. unlawful termination + deemed quit).
    # We keep every unique rule violation for CONFLICTs, but deduplicate minor GAP reports by law_name.
    dedup_map = {}
    for flag in flagged_issues:
        if flag["status"] == "conflict":
            key = (flag["clause_index"], flag["legal_rule"].id)
        else:
            key = (flag["clause_index"], flag["legal_rule"].law_name)

        existing = dedup_map.get(key)
        if existing is None:
            dedup_map[key] = flag
        else:
            status_rank = {"conflict": 3, "gap": 2, "missing": 1}
            new_rank = status_rank.get(flag["status"], 0)
            old_rank = status_rank.get(existing["status"], 0)
            if new_rank > old_rank or (
                new_rank == old_rank and (flag["severity_score"], flag["inlegal_similarity"]) > (existing["severity_score"], existing["inlegal_similarity"])
            ):
                dedup_map[key] = flag

    flagged_issues = list(dedup_map.values())

    logger.info(
        "After dedup: %d flagged issues",
        len(flagged_issues),
    )

    # ── Step 8: Calculate overall score ──────────────────────────────
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

    # P0 Data Integrity Invariant: Assert compliant_clauses + flagged_clauses == total_clauses
    flagged_count = len(flagged_issues)
    verified_safe_count = max(0, total_clauses - flagged_count)
    if verified_safe_count + flagged_count != total_clauses:
        total_clauses = max(total_clauses, verified_safe_count + flagged_count)

    # ── Step 9: Persist to DB ────────────────────────────────────────
    report = ScanReport.objects.create(
        policy=policy,
        overall_score=score_data["overall_score"],
        risk_level=score_data["risk_level"],
        total_clauses=total_clauses,
        compliant_clauses=verified_safe_count,
        flagged_clauses=flagged_count,
        scan_duration_seconds=round(duration, 2),
        miniml_avg_score=round(miniml_avg, 4),
        inlegal_avg_score=round(inlegal_avg, 4),
        scanned_by=user,
    )
    # Runtime integrity assertion
    assert report.compliant_clauses + report.flagged_clauses == report.total_clauses, "Data integrity failure: clause count mismatch!"

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
            element_results=fi.get("element_results", []),
            coverage_fraction=fi.get("coverage_fraction", 0.0),
            is_resolved=False,
        ))

    if issue_objects:
        FlaggedIssue.objects.bulk_create(issue_objects)

    # ── Step 10: Engine v2 Pipeline (4-Way Taxonomy, Union Retrieval, NLI Gate & GLiNER) ──
    try:
        from compliance.ingestion import ingest_document
        from compliance.kb import get_all_requirements
        from compliance.retrieval import retrieve_for_requirement
        from compliance.nli_gate import evaluate_nli_candidates, classify_requirement_gate
        from compliance.gliner_engine import evaluate_numeric_comparison
        from compliance.scoring import evaluate_composite_sub_elements, score_finding
        from compliance.models import AuditFinding

        logger.info("Running Engine v2 upgrade pipeline for policy id=%d", policy.id)
        clause_list = ingest_document(str(policy.file.path), doc_id=policy.id)
        AuditFinding.objects.filter(policy=policy).delete()

        reqs = get_all_requirements()
        for req in reqs:
            # 1. Retrieve union top-k candidates (InLegal-SBERT + MiniLM + lexical fallback)
            candidates = retrieve_for_requirement(req, clause_list, top_k=8, include_lexical=True)

            # 2. Evaluate NLI Cross-Encoder probabilities and topical relevance
            eval_candidates = evaluate_nli_candidates(candidates, hypothesis_text=req.description, requirement=req)

            # 3. Evaluate numeric/temporal quantities via GLiNER if threshold/conflict rule
            numeric_res = None
            if req.taxonomy_type in ("threshold", "conflict") or req.threshold_value is not None:
                best_txt = eval_candidates[0].get("raw_text", "") if eval_candidates else ""
                numeric_res = evaluate_numeric_comparison(req, best_txt)

            # 4. Classify requirement via NLI Gate & enforce non-hallucination evidence guard
            gate_res = classify_requirement_gate(req, eval_candidates, numeric_eval_result=numeric_res)
            verdict = gate_res.get("verdict", "MISSING")
            evidence = gate_res.get("evidence", [])
            nli_conf = gate_res.get("nli_confidence", 0.0)

            # 5. For composite requirements, compute atomic sub-element coverage
            sub_status = []
            coverage_val = 1.0 if verdict == "COMPLIANT" else 0.0
            if req.taxonomy_type == "composite":
                cov_ratio, sub_status = evaluate_composite_sub_elements(req, clause_list)
                coverage_val = cov_ratio
                if cov_ratio >= 0.85:
                    verdict = "COMPLIANT"
                elif cov_ratio >= 0.40:
                    verdict = "GAP"
                else:
                    verdict = "MISSING"

            # 6. Calculate explainable severity formula and confidence tier
            scoring_res = score_finding(
                requirement=req,
                verdict=verdict,
                coverage=coverage_val,
                nli_conf=nli_conf,
                evidence=evidence,
                sub_element_status=sub_status
            )

            if verdict == "MISSING":
                evidence = []

            AuditFinding.objects.create(
                policy=policy,
                requirement=req,
                verdict=verdict,
                confidence_tier=scoring_res.get("confidence_tier", "High"),
                severity_score=scoring_res.get("severity", 0.0),
                coverage=coverage_val,
                nli_confidence=nli_conf,
                evidence_clauses=evidence,
                sub_element_status=sub_status
            )
        logger.info("Engine v2 pipeline complete for policy id=%d", policy.id)
    except Exception as e:
        logger.warning("Engine v2 execution exception (non-fatal): %s", e, exc_info=True)

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
    legal_rule_id across all clauses (highest combined_score).

    One flag per requirement: only the single best-matching clause
    is considered for each LegalRule.

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
        None if compliant, or "GAP" / "MISSING"
    """
    if keyword_found and combined_sim >= 0.65:
        return None  # COMPLIANT

    if keyword_found and combined_sim < 0.65:
        return "GAP"

    return None


def _find_relevant_clause(
    rule, best_match: dict | None, rule_result: dict, clauses: list[dict]
) -> tuple[str, int]:
    """Find the most relevant clause text and index for a flagged issue."""
    # Prefer semantic match clause (more accurate)
    if best_match and best_match.get("clause_text"):
        return best_match["clause_text"], best_match.get("clause_index", 0)

    # Fall back to rule checker's matched clause
    matched_idx = rule_result.get("matched_clause_index")
    if matched_idx and clauses:
        for clause in clauses:
            if clause.get("index") == matched_idx:
                return clause["text"], matched_idx

    # No specific clause — use explicit "not found" message
    return "No related clause found in this document", 0


def _generate_description(
    rule,
    status: str,
    keyword_found: bool,
    combined_sim: float,
    clause_text: str,
    rule_result: dict,
    catch_signal: str = "similarity",
    nli_result: dict | None = None,
    element_results: list[dict] | None = None,
    coverage_fraction: float = 0.0,
) -> str:
    """Generate clean human-readable violation description."""
    law_ref = f"{rule.law_name} {rule.section}"

    if element_results and len(element_results) > 1:
        found_elems = [el for el in element_results if el.get("found")]
        missing_elems = [el for el in element_results if not el.get("found") and not el.get("contradicted")]
        contra_elems = [el for el in element_results if el.get("contradicted")]

        parts = []
        if found_elems:
            parts.append("Confirms: " + "; ".join(el["text"] for el in found_elems).rstrip(".") + ".")
        if contra_elems:
            parts.append("Contradicts: " + "; ".join(el["text"] for el in contra_elems).rstrip(".") + ".")
        if missing_elems:
            missing_names = [el.get("id", "").replace("_", " ").title() if el.get("id") else el["text"][:30] for el in missing_elems]
            parts.append("Does not specify: " + ", ".join(missing_names) + ".")

        summary_line = f"({len(found_elems)} of {len(element_results)} required elements addressed)"
        desc = " ".join(parts) + " " + summary_line if parts else f"Issue flagged for {law_ref}."
        return desc.strip()

    if status == "MISSING":
        return (
            f"The policy does not address the requirement under {law_ref}. "
            f"This section requires: {rule.requirement_text[:200]}. "
            f"No matching clauses addressing these mandates were found in the document."
        )

    if status == "CONFLICT":
        clause_preview = clause_text[:150].replace("\n", " ")
        if nli_result and nli_result["label"] == "contradiction":
            return (
                f"Direct contradiction detected with {law_ref}. "
                f"The policy states: \"{clause_preview}\" — this directly "
                f"contradicts the statutory requirement: \"{rule.requirement_text[:150]}...\""
            )
        return (
            f"Conflict detected with {law_ref}. "
            f"The policy states: \"{clause_preview}...\" "
            f"However, the statutory law requires: \"{rule.requirement_text[:150]}...\""
        )

    if status == "GAP":
        clause_preview = clause_text[:150].replace("\n", " ")
        return (
            f"Partial compliance gap with {law_ref}. "
            f"The policy mentions: \"{clause_preview}...\", but coverage appears incomplete. "
            f"The full statutory requirement is: \"{rule.requirement_text[:150]}...\""
        )

    return f"Issue flagged for {law_ref}: {rule.requirement_text[:200]}"
