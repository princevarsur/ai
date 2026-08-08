"""
Standalone validation script for topical keyword filtering.
Tests the fix for false positive POSH Act matches on paternity leave clauses.

Run: python backend/compliance/validate_topical_filter.py
"""

import sys
import os

# Add parent directory to path to import topical_filter
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from compliance.topical_filter import has_required_keywords, filter_topically_invalid_candidates


def test_paternity_leave_posh_rejection():
    """Test Case 1: Paternity leave should be rejected for POSH Act Section 9(1)."""
    clause_text = (
        "2.4 Paternity Leave Male employees are entitled to 5 days of paid paternity leave "
        "to be availed within 30 days of the birth of a child."
    )
    statute_citation = "POSH Act 2013 Section 9(1)"
    
    result = has_required_keywords(clause_text, statute_citation)
    
    assert result is False, (
        f"FAIL: Paternity leave clause should be REJECTED for POSH Act.\n"
        f"Expected: False, Got: {result}"
    )
    print("[PASS] Paternity leave correctly rejected for POSH Act Section 9(1)")


def test_harassment_clause_posh_acceptance():
    """Test Case 2: Actual harassment clause should be accepted for POSH Act Section 9(1)."""
    clause_text = (
        "Any aggrieved woman may file a written complaint of sexual harassment "
        "to the Internal Complaints Committee within 3 months of the incident."
    )
    statute_citation = "POSH Act 2013 Section 9(1)"
    
    result = has_required_keywords(clause_text, statute_citation)
    
    assert result is True, (
        f"FAIL: Harassment clause should be ACCEPTED for POSH Act.\n"
        f"Expected: True, Got: {result}"
    )
    print("[PASS] Harassment clause correctly accepted for POSH Act Section 9(1)")


def test_maternity_leave_posh_rejection():
    """Test Case 3: Maternity leave should be rejected for POSH Act Section 9(1)."""
    clause_text = (
        "Female employees are entitled to 26 weeks of paid maternity leave "
        "as per the Maternity Benefit Act 1961."
    )
    statute_citation = "POSH Act 2013 Section 9(1)"
    
    result = has_required_keywords(clause_text, statute_citation)
    
    assert result is False, (
        f"FAIL: Maternity leave clause should be REJECTED for POSH Act.\n"
        f"Expected: False, Got: {result}"
    )
    print("[PASS] Maternity leave correctly rejected for POSH Act Section 9(1)")


def test_photocopier_it_act_rejection():
    """Test Case 4: Photocopier clause should be rejected for IT Act Section 66E."""
    clause_text = (
        "Employees must not use photocopiers, scanners, or printers "
        "for personal work during office hours."
    )
    statute_citation = "IT Act 2000 Section 66E"
    
    result = has_required_keywords(clause_text, statute_citation)
    
    assert result is False, (
        f"FAIL: Photocopier clause should be REJECTED for IT Act 66E.\n"
        f"Expected: False, Got: {result}"
    )
    print("[PASS] Photocopier clause correctly rejected for IT Act Section 66E")


def test_cctv_it_act_acceptance():
    """Test Case 5: CCTV surveillance clause should be accepted for IT Act Section 66E."""
    clause_text = (
        "CCTV cameras are installed in common areas for security purposes. "
        "Employees' privacy is protected and cameras do not record private areas."
    )
    statute_citation = "IT Act 2000 Section 66E"
    
    result = has_required_keywords(clause_text, statute_citation)
    
    assert result is True, (
        f"FAIL: CCTV clause should be ACCEPTED for IT Act 66E.\n"
        f"Expected: True, Got: {result}"
    )
    print("[PASS] CCTV clause correctly accepted for IT Act Section 66E")


def test_filter_candidates_function():
    """Test Case 6: filter_topically_invalid_candidates removes irrelevant clauses."""
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
    
    assert len(filtered) == 1, (
        f"FAIL: Expected 1 candidate after filtering, got {len(filtered)}"
    )
    assert filtered[0]['clause_id'] == 'cl_002', (
        f"FAIL: Expected clause cl_002, got {filtered[0]['clause_id']}"
    )
    print("[PASS] filter_topically_invalid_candidates correctly filters 2/3 irrelevant clauses")


def test_unknown_statute_no_filtering():
    """Test Case 7: Unknown statutes without keyword filters should accept all clauses."""
    clause_text = "Random clause about employee benefits and leave policies."
    statute_citation = "Unknown Act 2025 Section 123"
    
    result = has_required_keywords(clause_text, statute_citation)
    
    assert result is True, (
        f"FAIL: Unknown statute should allow all clauses through.\n"
        f"Expected: True, Got: {result}"
    )
    print("[PASS] Unknown statute correctly accepts all clauses (no keyword filter)")


def test_leave_policy_rejected_for_working_hours():
    """Test Case 8: Leave accrual policy should be rejected for daily working hours limit."""
    clause_text = (
        "Entitlement: 22 Days per annum This leave is proportionally earned for the period "
        "worked by the employee during the previous calendar year and is accrued monthly "
        "post completion of the month. A minimum of 3 days continuous leave is to be taken "
        "for the purpose of availing Leave Travel Allowance (LTA)."
    )
    statute_citation = "OSHWC Code 2020 Section 25(1)(a)"
    
    result = has_required_keywords(clause_text, statute_citation)
    
    assert result is False, (
        f"FAIL: Leave accrual policy should be REJECTED for working hours limit.\n"
        f"Expected: False, Got: {result}"
    )
    print("[PASS] Leave accrual policy correctly rejected for OSHWC Section 25 (working hours)")


def test_working_hours_clause_accepted_for_oshwc():
    """Test Case 9: Actual working hours clause should be accepted for OSHWC Section 25."""
    clause_text = (
        "The standard working hours for employees shall be 8 hours per day and 48 hours per week. "
        "No employee shall be required to work more than 9 hours in a day including overtime. "
        "Shift timings will be determined by the department head."
    )
    statute_citation = "OSHWC Code 2020 Section 25(1)(a)"
    
    result = has_required_keywords(clause_text, statute_citation)
    
    assert result is True, (
        f"FAIL: Working hours clause should be ACCEPTED for OSHWC Section 25.\n"
        f"Expected: True, Got: {result}"
    )
    print("[PASS] Working hours clause correctly accepted for OSHWC Section 25")


def main():
    print("\n" + "="*70)
    print("THEMIS Topical Keyword Filter Validation")
    print("="*70 + "\n")
    
    print("Testing fix for false positive: Paternity leave flagged as POSH Act violation\n")
    
    tests = [
        test_paternity_leave_posh_rejection,
        test_harassment_clause_posh_acceptance,
        test_maternity_leave_posh_rejection,
        test_photocopier_it_act_rejection,
        test_cctv_it_act_acceptance,
        test_filter_candidates_function,
        test_unknown_statute_no_filtering,
        test_leave_policy_rejected_for_working_hours,
        test_working_hours_clause_accepted_for_oshwc,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] in {test_func.__name__}: {e}")
            failed += 1
    
    print("\n" + "="*70)
    print(f"Test Results: {passed} PASSED, {failed} FAILED")
    print("="*70)
    
    if failed == 0:
        print("\n[SUCCESS] All tests passed! Topical keyword filtering is working correctly.")
        print("\nThe fix prevents false positives like:")
        print("  - Paternity leave clauses flagged against POSH Act harassment rules")
        print("  - Photocopier clauses flagged against IT Act bodily privacy rules")
        print("  - General leave clauses flagged against maternity/harassment rules")
        print("  - Leave accrual policies flagged against working hours limits")
        return 0
    else:
        print(f"\n[FAILURE] {failed} test(s) failed. Review the implementation.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
