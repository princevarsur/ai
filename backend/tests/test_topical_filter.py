"""
Tests for topical keyword filtering to prevent false positive matches.

Test Cases:
1. Paternity leave clause should NOT match POSH Act Section 9(1) complaint window
2. Maternity leave clause should NOT match POSH Act Section 9(1) complaint window
3. Actual harassment clause SHOULD match POSH Act Section 9(1)
4. IT equipment clause should NOT match IT Act Section 66E bodily privacy
5. CCTV surveillance clause SHOULD match IT Act Section 66E bodily privacy
"""

from django.test import TestCase
from compliance.topical_filter import has_required_keywords, filter_topically_invalid_candidates


class TopicalKeywordFilterTestCase(TestCase):
    
    def test_paternity_leave_rejected_for_posh_act(self):
        """Paternity leave clause should be rejected for POSH Act Section 9(1) complaint window."""
        clause_text = (
            "2.4 Paternity Leave Male employees are entitled to 5 days of paid paternity leave "
            "to be availed within 30 days of the birth of a child."
        )
        statute_citation = "POSH Act 2013 Section 9(1)"
        
        result = has_required_keywords(clause_text, statute_citation)
        self.assertFalse(
            result,
            "Paternity leave clause should be rejected for POSH Act (missing harassment keywords)"
        )
    
    def test_maternity_leave_rejected_for_posh_act(self):
        """Maternity leave clause should be rejected for POSH Act Section 9(1)."""
        clause_text = (
            "Female employees are entitled to 26 weeks of paid maternity leave "
            "as per the Maternity Benefit Act 1961."
        )
        statute_citation = "POSH Act 2013 Section 9(1)"
        
        result = has_required_keywords(clause_text, statute_citation)
        self.assertFalse(
            result,
            "Maternity leave clause should be rejected for POSH Act (missing harassment keywords)"
        )
    
    def test_harassment_clause_accepted_for_posh_act(self):
        """Actual harassment complaint clause should be accepted for POSH Act Section 9(1)."""
        clause_text = (
            "Any aggrieved woman may file a written complaint of sexual harassment "
            "to the Internal Complaints Committee within 3 months of the incident."
        )
        statute_citation = "POSH Act 2013 Section 9(1)"
        
        result = has_required_keywords(clause_text, statute_citation)
        self.assertTrue(
            result,
            "Harassment complaint clause should be accepted for POSH Act (contains required keywords)"
        )
    
    def test_photocopier_rejected_for_it_act_66e(self):
        """Photocopier/printer clause should be rejected for IT Act Section 66E bodily privacy."""
        clause_text = (
            "Employees must not use photocopiers, scanners, or printers "
            "for personal work during office hours."
        )
        statute_citation = "IT Act 2000 Section 66E"
        
        result = has_required_keywords(clause_text, statute_citation)
        self.assertFalse(
            result,
            "Photocopier clause should be rejected for IT Act 66E (missing privacy/surveillance keywords)"
        )
    
    def test_cctv_clause_accepted_for_it_act_66e(self):
        """CCTV surveillance clause should be accepted for IT Act Section 66E."""
        clause_text = (
            "CCTV cameras are installed in common areas for security purposes. "
            "Employees' privacy is protected and cameras do not record private areas."
        )
        statute_citation = "IT Act 2000 Section 66E"
        
        result = has_required_keywords(clause_text, statute_citation)
        self.assertTrue(
            result,
            "CCTV clause should be accepted for IT Act 66E (contains privacy/surveillance keywords)"
        )
    
    def test_general_leave_rejected_for_maternity_act(self):
        """General leave clause should be rejected for Maternity Benefit Act."""
        clause_text = (
            "Employees are entitled to 12 days of casual leave per year "
            "which can be availed with prior approval from the manager."
        )
        statute_citation = "Maternity Benefit Act 1961 Section 12"
        
        result = has_required_keywords(clause_text, statute_citation)
        self.assertFalse(
            result,
            "General leave clause should be rejected for Maternity Benefit Act (missing maternity keywords)"
        )
    
    def test_maternity_clause_accepted_for_maternity_act(self):
        """Maternity leave clause should be accepted for Maternity Benefit Act."""
        clause_text = (
            "Female employees are entitled to 26 weeks of paid maternity leave "
            "for pregnancy and childbirth, as per statutory requirements."
        )
        statute_citation = "Maternity Benefit Act 1961 Section 12"
        
        result = has_required_keywords(clause_text, statute_citation)
        self.assertTrue(
            result,
            "Maternity clause should be accepted for Maternity Benefit Act (contains maternity keywords)"
        )
    
    def test_unknown_statute_allows_all_clauses(self):
        """Clauses for statutes without keyword filters should always be accepted."""
        clause_text = "Random clause about employee benefits."
        statute_citation = "Unknown Act 2025 Section 123"
        
        result = has_required_keywords(clause_text, statute_citation)
        self.assertTrue(
            result,
            "Clauses for unknown statutes should be accepted (no keyword filter defined)"
        )
    
    def test_filter_candidates_removes_irrelevant(self):
        """filter_topically_invalid_candidates should remove irrelevant candidates."""
        candidates = [
            {
                'clause_id': 'cl_001',
                'raw_text': 'Paternity leave for 5 days within 30 days of birth.',
                'max_score': 0.72
            },
            {
                'clause_id': 'cl_002',
                'raw_text': 'Sexual harassment complaints must be filed within 3 months to the ICC.',
                'max_score': 0.85
            },
            {
                'clause_id': 'cl_003',
                'raw_text': 'Casual leave can be availed after manager approval.',
                'max_score': 0.68
            },
        ]
        statute_citation = "POSH Act 2013 Section 9(1)"
        
        filtered = filter_topically_invalid_candidates(candidates, statute_citation)
        
        # Only cl_002 should remain (contains harassment/complaint/ICC keywords)
        self.assertEqual(len(filtered), 1, "Only 1 candidate should pass the topical filter")
        self.assertEqual(filtered[0]['clause_id'], 'cl_002')
    
    def test_filter_candidates_preserves_all_if_no_filter(self):
        """filter_topically_invalid_candidates should preserve all candidates if no keyword filter exists."""
        candidates = [
            {'clause_id': 'cl_001', 'raw_text': 'Clause A', 'max_score': 0.72},
            {'clause_id': 'cl_002', 'raw_text': 'Clause B', 'max_score': 0.85},
        ]
        statute_citation = "Unknown Act 2025 Section 1"
        
        filtered = filter_topically_invalid_candidates(candidates, statute_citation)
        
        self.assertEqual(len(filtered), 2, "All candidates should be preserved for unknown statutes")


class TopicalFilterIntegrationTestCase(TestCase):
    """Integration tests verifying topical filter prevents false positive NLI evaluations."""
    
    def setUp(self):
        from compliance.models import Requirement
        
        # Create POSH Act Section 9(1) requirement
        self.posh_req = Requirement.objects.create(
            statute_citation="POSH Act 2013 Section 9(1)",
            title="Complaint Filing Window",
            description=(
                "An aggrieved woman may, in writing, make a complaint of sexual harassment "
                "at workplace to the Internal Committee within a period of three months "
                "from the date of incident."
            ),
            taxonomy_type="conflict",
            domain="workplace_safety",
            penalty_tier="high",
            mandatory_weight=1.0,
            threshold_value=90.0,
            threshold_unit="days",
            threshold_op="min"
        )
    
    def test_paternity_leave_not_flagged_integration(self):
        """Integration test: Paternity leave clause should not trigger NLI evaluation for POSH Act."""
        from compliance.nli_gate import evaluate_nli_candidates
        
        candidates = [
            {
                'clause_id': 'cl_pat_001',
                'section_title': '2.4 Paternity Leave',
                'page_no': 12,
                'raw_text': (
                    "2.4 Paternity Leave Male employees are entitled to 5 days of paid paternity leave "
                    "to be availed within 30 days of the birth of a child."
                ),
                'char_offsets': [2400, 2550],
                'start_char': 2400,
                'end_char': 2550,
                'inlegal_score': 0.45,
                'minilm_score': 0.68,
                'tfidf_score': 0.12,
                'max_score': 0.68,
                'avg_score': 0.565,
                'retrieved_by': ['minilm']
            }
        ]
        
        hypothesis = self.posh_req.description
        
        evaluated = evaluate_nli_candidates(candidates, hypothesis, requirement=self.posh_req)
        
        # Candidate should be marked as topically invalid
        self.assertEqual(len(evaluated), 1)
        self.assertFalse(evaluated[0]['is_topically_valid'])
        self.assertIn('missing_keywords', evaluated[0].get('rejection_reason', ''))
        self.assertEqual(evaluated[0]['nli_label'], 'neutral')
        self.assertEqual(evaluated[0]['entailment_prob'], 0.0)
