"""
backend/tests/test_engine_v2.py

Milestone 4 Engine Verification Test Suite

Tests:
1. Multi-Model Hybrid Retrieval (`retrieval.py`):
   - Union retrieval combining InLegal-SBERT, MiniLM, and TF-IDF lexical.
   - Deduplication by clause_id.
   - Preservation of top-k union set (NOT truncated to top-1).
   - Vector caching by embedding_hash.
2. GLiNER Extraction & Numeric Rules (`gliner_engine.py`):
   - Entity extraction for time periods, monetary amounts, percentages, deadlines, roles.
   - Deterministic numeric comparison (POSH 10 days vs 3 months -> CONFLICT).
   - Wage payment timing and leave accumulation cap rules.
3. NLI Classification Gate & Evidence Guard (`nli_gate.py`):
   - NLI Cross-Encoder classification into COMPLIANT, CONFLICT, GAP, MISSING.
   - Non-hallucination guard returning evidence: [] for MISSING findings.
   - Topical filtering rejecting photocopier/scanner clauses for IT Act Sec 66E.
4. Scoring Engine (`scoring.py`):
   - Weighted sub-element coverage ratio calculation.
   - 4-parameter severity formula and breakdown dict.
   - Confidence tier assignment (High, Medium, Low).
"""

import os
import sys
import numpy as np

# Ensure backend directory is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'themis.settings')

import django
django.setup()

from django.test import TestCase
from django.core.management import call_command

from compliance.models import Requirement, SubElement, ClauseIndex
from compliance.retrieval import (
    retrieve_union_candidates,
    retrieve_for_requirement,
    retrieve_for_sub_element,
    get_clause_embedding,
    clear_embedding_cache,
    _EMBEDDING_CACHE,
)
from compliance.gliner_engine import (
    extract_entities,
    parse_time_period,
    parse_percentage,
    evaluate_numeric_comparison,
)
from compliance.nli_gate import (
    predict_nli_pair,
    evaluate_nli_candidates,
    classify_requirement_gate,
    is_topically_valid_clause,
)
from compliance.scoring import (
    compute_sub_element_coverage,
    compute_severity_score,
    determine_confidence_tier,
    evaluate_composite_sub_elements,
    score_finding,
)


class TestHybridRetrieval(TestCase):
    """Test suite for multi-model union retrieval, TF-IDF lexical search, and embedding caching."""

    def setUp(self):
        call_command('seed_kb')
        clear_embedding_cache()

        # Create mock ClauseIndex objects
        self.clauses = [
            ClauseIndex.objects.create(
                document_name="Test_Policy.pdf",
                clause_id="CL_001",
                section_title="Information Security Policy",
                page_no=1,
                raw_text="The organization maintains a documented information security policy reviewed annually.",
                embedding_hash="hash_001",
            ),
            ClauseIndex.objects.create(
                document_name="Test_Policy.pdf",
                clause_id="CL_002",
                section_title="Access Control Policy",
                page_no=2,
                raw_text="Access control measures including role-based permissions and multi-factor authentication are enforced.",
                embedding_hash="hash_002",
            ),
            ClauseIndex.objects.create(
                document_name="Test_Policy.pdf",
                clause_id="CL_003",
                section_title="Vulnerability Assessment",
                page_no=3,
                raw_text="Periodic independent VAPT and penetration testing audits shall be conducted by CERT-In empaneled auditors every 12 months.",
                embedding_hash="hash_003",
            ),
            ClauseIndex.objects.create(
                document_name="Test_Policy.pdf",
                clause_id="CL_004",
                section_title="Wage Payment",
                page_no=4,
                raw_text="Monthly wage payment shall be disbursed before expiry of the 7th day of each month.",
                embedding_hash="hash_004",
            ),
        ]

    def test_retrieval_union_contains_multiple_models(self):
        """Verify union retrieval retrieves candidates from InLegal-SBERT, MiniLM, and TFIDF."""
        query = "periodic independent VAPT audit security standard"
        results = retrieve_union_candidates(query, self.clauses, top_k=2, include_lexical=True)

        self.assertGreater(len(results), 0, "Retrieval union should return candidates")

        # Check fields of candidates
        for cand in results:
            self.assertIn("clause_id", cand)
            self.assertIn("inlegal_score", cand)
            self.assertIn("minilm_score", cand)
            self.assertIn("tfidf_score", cand)
            self.assertIn("max_score", cand)
            self.assertIn("retrieved_by", cand)
            self.assertIsInstance(cand["retrieved_by"], list)

        # Verify top candidate for VAPT query is CL_003
        top_cand = results[0]
        self.assertEqual(top_cand["clause_id"], "CL_003", "VAPT query should retrieve VAPT clause CL_003 as top candidate")

    def test_retrieval_deduplication(self):
        """Verify union candidate set contains no duplicate clause_ids."""
        query = "access control security policy"
        results = retrieve_union_candidates(query, self.clauses, top_k=4, include_lexical=True)

        clause_ids = [c["clause_id"] for c in results]
        unique_clause_ids = set(clause_ids)

        self.assertEqual(len(clause_ids), len(unique_clause_ids), "Retrieval results must be deduplicated by clause_id")

    def test_retrieval_not_truncated_to_top_1(self):
        """Verify candidate set returns all top-k union candidates and is NOT truncated to top-1 prior to NLI."""
        query = "information security policy access control"
        results = retrieve_union_candidates(query, self.clauses, top_k=3, include_lexical=True)

        self.assertGreater(len(results), 1, "Candidate set must return top-k union candidates, not truncated to top-1")

    def test_embedding_caching(self):
        """Verify clause embedding vectors are cached in memory using embedding_hash."""
        c = self.clauses[0]
        from compliance.model_registry import ModelRegistry
        inlegal = ModelRegistry.get_inlegal_sbert()

        cache_key = ("inlegal_sbert", c.embedding_hash)
        self.assertNotIn(cache_key, _EMBEDDING_CACHE)

        # Call get_clause_embedding first time
        vec1 = get_clause_embedding(c.raw_text, c.embedding_hash, "inlegal_sbert", inlegal)
        self.assertIn(cache_key, _EMBEDDING_CACHE)

        # Call get_clause_embedding second time
        vec2 = get_clause_embedding(c.raw_text, c.embedding_hash, "inlegal_sbert", inlegal)
        np.testing.assert_array_equal(vec1, vec2, "Cached vector must match exactly on subsequent lookup")


class TestGLiNEREngineAndNumericRules(TestCase):
    """Test suite for GLiNER zero-shot entity extraction and deterministic numeric comparison rules."""

    def setUp(self):
        call_command('seed_kb')

    def test_gliner_entity_extraction(self):
        """Verify GLiNER extracts entities (time period, monetary amount, percentage, deadline, statute reference, role)."""
        sample_text = (
            "Any aggrieved woman may submit a complaint of sexual harassment within 10 days to the Presiding Officer. "
            "Maximum statutory deduction from wages shall not exceed 50% under IT Act Section 43A."
        )
        entities = extract_entities(sample_text)

        self.assertIsInstance(entities, list)
        if entities:
            labels = {e["label"] for e in entities}
            self.assertTrue(any(l in labels for l in ["time period", "monetary amount", "percentage", "statute reference", "role/designation"]))

    def test_parse_time_period_and_percentage(self):
        """Verify numeric parsers extract values and units correctly."""
        res_days = parse_time_period("complaint filed within 10 days of incident")
        self.assertIsNotNone(res_days)
        self.assertEqual(res_days["value"], 10.0)
        self.assertEqual(res_days["unit"], "day")

        res_months = parse_time_period("statutory window of 3 months")
        self.assertIsNotNone(res_months)
        self.assertEqual(res_months["value"], 3.0)
        self.assertEqual(res_months["unit"], "month")

        res_7th = parse_time_period("disbursed before expiry of the 7th day of each month")
        self.assertIsNotNone(res_7th)
        self.assertEqual(res_7th["value"], 7.0)

        pct = parse_percentage("maximum deduction ceiling is 50%")
        self.assertEqual(pct, 50.0)

    def test_posh_complaint_window_conflict_rule(self):
        """Verify deterministic POSH rule: 10 days vs 3-month statutory minimum -> CONFLICT."""
        req_posh = Requirement.objects.filter(statute_citation__icontains="9(1)").first()
        self.assertIsNotNone(req_posh, "POSH Sec 9(1) requirement must exist in DB")

        # Case 1: Policy imposes 10-day window (shorter than 3 months) -> CONFLICT
        clause_10days = "An aggrieved woman must file a written complaint within 10 days of the incident."
        eval_conflict = evaluate_numeric_comparison(req_posh, clause_10days)

        self.assertTrue(eval_conflict["has_numeric_rule"])
        self.assertTrue(eval_conflict["is_conflict"], "10-day complaint window must trigger automatic CONFLICT against 3-month minimum")
        self.assertFalse(eval_conflict["is_compliant"])

        # Case 2: Policy complies with 3 months window -> COMPLIANT
        clause_3months = "Complaints of sexual harassment may be submitted within 3 months of the date of incident."
        eval_compliant = evaluate_numeric_comparison(req_posh, clause_3months)
        self.assertFalse(eval_compliant["is_conflict"])
        self.assertTrue(eval_compliant["is_compliant"])

    def test_wage_payment_timing_rule(self):
        """Verify wage payment timing: 7th day -> COMPLIANT, 15th day -> CONFLICT."""
        req_wages = Requirement.objects.filter(statute_citation__icontains="17(1)(d)").first()
        self.assertIsNotNone(req_wages)

        # 7th day -> COMPLIANT
        eval_7 = evaluate_numeric_comparison(req_wages, "Wages shall be paid on or before 7th day of each month.")
        self.assertTrue(eval_7["is_compliant"])
        self.assertFalse(eval_7["is_conflict"])

        # 15th day -> CONFLICT
        eval_15 = evaluate_numeric_comparison(req_wages, "Monthly wages will be disbursed on the 15th day of the following month.")
        self.assertTrue(eval_15["is_conflict"])

    def test_leave_accumulation_caps(self):
        """Verify earned leave accumulation cap rules (MH 45 days, KA 30 days)."""
        req_mh = Requirement.objects.filter(statute_citation__icontains="Maharashtra").first()
        self.assertIsNotNone(req_mh)

        # 60 days carry forward vs 45 days cap -> CONFLICT
        eval_mh = evaluate_numeric_comparison(req_mh, "Earned leave can be accumulated and carried forward up to 60 days.")
        self.assertTrue(eval_mh["is_conflict"])


class TestNLIGateAndEvidenceGuard(TestCase):
    """Test suite for Cross-Encoder NLI classification, non-hallucination evidence guard, and topical filtering."""

    def setUp(self):
        call_command('seed_kb')

    def test_nli_predict_pair(self):
        """Verify Cross-Encoder NLI pair prediction outputs valid label and probabilities."""
        clause = "The company has established a documented information security policy compliant with ISO 27001."
        hypothesis = "Documented information security policy exists."

        res = predict_nli_pair(clause, hypothesis)
        self.assertIn("label", res)
        self.assertIn("entailment_prob", res)
        self.assertIn("contradiction_prob", res)
        self.assertIn("neutral_prob", res)

        # Should be entailment
        self.assertEqual(res["label"], "entailment")
        self.assertGreaterEqual(res["entailment_prob"], 0.50)

    def test_non_hallucination_evidence_guard_on_missing(self):
        """Verify strict non-hallucination guard: return evidence: [] for any MISSING finding."""
        req = Requirement.objects.filter(statute_citation__icontains="66E").first()
        self.assertIsNotNone(req)

        # Irrelevant candidate clauses (relevance below floor)
        irrelevant_candidates = [
            {
                "clause_id": "CL_999",
                "section_title": "Cafeteria Operations",
                "page_no": 5,
                "raw_text": "Cafeteria meals are served from 12 PM to 2 PM daily.",
                "max_score": 0.05,
                "entailment_prob": 0.02,
                "contradiction_prob": 0.01,
                "neutral_prob": 0.97,
                "is_topically_valid": True,
            }
        ]

        gate_res = classify_requirement_gate(req, irrelevant_candidates, relevance_floor=0.35)

        self.assertEqual(gate_res["verdict"], "MISSING")
        self.assertEqual(gate_res["evidence"], [], "MISSING finding MUST return an empty evidence list [] with zero quotes!")

    def test_topical_filtering_sec_66e(self):
        """Verify topical filter rejects photocopier/scanner clauses from IT Act Sec 66E bodily privacy findings."""
        req_66e = Requirement.objects.filter(statute_citation__icontains="66E").first()
        self.assertIsNotNone(req_66e)

        photocopier_clause = "All employees using office photocopiers and scanner equipment must log their usage."
        self.assertFalse(
            is_topically_valid_clause(req_66e, photocopier_clause),
            "Photocopier/scanner clause MUST be rejected by topical filter for IT Act Sec 66E bodily privacy"
        )

        # Candidate list containing only photocopier clause
        candidates = [
            {
                "clause_id": "CL_042",
                "section_title": "Printing Facilities",
                "page_no": 4,
                "raw_text": photocopier_clause,
                "max_score": 0.60,
                "entailment_prob": 0.50,
            }
        ]

        eval_cands = evaluate_nli_candidates(candidates, "Protects bodily privacy", requirement=req_66e)
        self.assertFalse(eval_cands[0]["is_topically_valid"])

        gate_res = classify_requirement_gate(req_66e, eval_cands)
        self.assertEqual(gate_res["verdict"], "MISSING")
        self.assertEqual(gate_res["evidence"], [], "Photocopier clause rejection must yield MISSING with empty evidence []")


class TestScoringEngine(TestCase):
    """Test suite for sub-element coverage ratio, transparent 4-parameter severity formula, and confidence tiers."""

    def setUp(self):
        call_command('seed_kb')

    def test_sub_element_coverage_scoring(self):
        """Verify sub-element coverage ratio calculation: coverage = sum(sat_w) / sum(all_w)."""
        sub_element_results = [
            {"element_key": "k1", "weight": 0.40, "satisfied": True},
            {"element_key": "k2", "weight": 0.30, "satisfied": True},
            {"element_key": "k3", "weight": 0.15, "satisfied": False},
            {"element_key": "k4", "weight": 0.15, "satisfied": False},
        ]

        cov = compute_sub_element_coverage(sub_element_results)
        self.assertAlmostEqual(cov, 0.70, places=3, msg="0.40 + 0.30 out of 1.0 = 0.70 coverage")

    def test_severity_formula_and_breakdown(self):
        """
        Verify transparent 4-parameter severity formula:
        severity = 0.4 * mandatory_weight + 0.3 * (1 - coverage) + 0.2 * penalty_weight + 0.1 * nli_conf
        """
        res = compute_severity_score(
            mandatory_weight=1.0,
            coverage=0.50,         # coverage_loss = 0.50
            penalty_tier='high',    # penalty_weight = 1.0
            nli_conf=0.85
        )

        expected_raw = (0.4 * 1.0) + (0.3 * 0.50) + (0.2 * 1.0) + (0.1 * 0.85)
        # = 0.40 + 0.15 + 0.20 + 0.085 = 0.835
        expected_score = round(expected_raw * 100.0, 2)  # 83.50

        self.assertEqual(res["severity_score"], expected_score)

        breakdown = res["severity_breakdown"]
        self.assertEqual(breakdown["mandatory_weight"], 1.0)
        self.assertEqual(breakdown["coverage_loss"], 0.50)
        self.assertEqual(breakdown["penalty_weight"], 1.0)
        self.assertEqual(breakdown["nli_conf"], 0.85)

    def test_confidence_tiers(self):
        """Verify confidence tiers (High, Medium, Low)."""
        self.assertEqual(determine_confidence_tier(0.85), 'High')
        self.assertEqual(determine_confidence_tier(0.60), 'Medium')
        self.assertEqual(determine_confidence_tier(0.30), 'Low')

    def test_score_finding_payload_structure(self):
        """Verify score_finding outputs structured payload conforming to THEMIS API contract."""
        req = Requirement.objects.filter(statute_citation__icontains="43A").first()
        self.assertIsNotNone(req)

        sub_status = [
            {"element_key": "security_policy_doc", "satisfied": True, "weight": 0.25},
            {"element_key": "control_measures", "satisfied": True, "weight": 0.25},
            {"element_key": "prescribed_standard", "satisfied": False, "weight": 0.25},
            {"element_key": "periodic_independent_vapt", "satisfied": False, "weight": 0.25},
        ]
        evidence = [
            {"clause_id": "CL_001", "section_title": "Security", "page_no": 1, "raw_text": "Text"}
        ]

        payload = score_finding(
            requirement=req,
            verdict="GAP",
            coverage=0.50,
            nli_conf=0.80,
            evidence=evidence,
            sub_element_status=sub_status
        )

        self.assertEqual(payload["requirement_id"], req.statute_citation)
        self.assertEqual(payload["verdict"], "GAP")
        self.assertEqual(payload["confidence_tier"], "High")
        self.assertIn("severity", payload)
        self.assertIn("severity_breakdown", payload)
        self.assertEqual(payload["coverage"], 0.50)
        self.assertEqual(len(payload["evidence"]), 1)


if __name__ == '__main__':
    import unittest
    unittest.main()
