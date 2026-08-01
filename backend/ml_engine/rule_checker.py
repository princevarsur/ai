"""
Rule-based compliance checking engine.

Checks policy documents against LegalRule.keywords_regex patterns.
No AI — pure regex matching. Flags missing required clauses.
"""

import os
import re
import sys

import django

# Django setup for standalone testing
if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "themis.settings")
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    django.setup()

from laws.models import LegalRule


def check_rules(full_text: str, clauses: list[dict]) -> list[dict]:
    """
    Run rule-based check against all active LegalRules.

    Args:
        full_text: The complete extracted text of the document.
        clauses: List of clause dicts from clause_extractor.

    Returns list of check results:
    [
        {
            "legal_rule_id": int,
            "law_name": str,
            "section": str,
            "category": str,
            "status": "PRESENT" | "MISSING",
            "matched_text": str | None,
            "matched_clause_index": int | None,
            "keywords_regex": str,
            "severity_weight": int,
        },
    ]
    """
    rules = LegalRule.objects.filter(is_active=True)
    results = []

    for rule in rules:
        result = _check_single_rule(rule, full_text, clauses)
        results.append(result)

    return results


def get_rule_check_summary(results: list[dict]) -> dict:
    """
    Summarize rule-check results.

    Returns:
    {
        "total_rules_checked": int,
        "present_count": int,
        "missing_count": int,
        "missing_by_category": {"labour": 2, "data_privacy": 3, ...},
        "critical_missing": [list of missing rules with severity >= 8],
    }
    """
    present = [r for r in results if r["status"] == "PRESENT"]
    missing = [r for r in results if r["status"] == "MISSING"]

    missing_by_category = {}
    for r in missing:
        cat = r["category"]
        missing_by_category[cat] = missing_by_category.get(cat, 0) + 1

    critical_missing = [
        {
            "law_name": r["law_name"],
            "section": r["section"],
            "category": r["category"],
            "severity_weight": r["severity_weight"],
            "keywords_regex": r["keywords_regex"],
        }
        for r in missing
        if r["severity_weight"] >= 8
    ]

    return {
        "total_rules_checked": len(results),
        "present_count": len(present),
        "missing_count": len(missing),
        "missing_by_category": missing_by_category,
        "critical_missing": critical_missing,
    }


# ── Internal ─────────────────────────────────────────────────────────────


def _check_single_rule(
    rule: LegalRule, full_text: str, clauses: list[dict]
) -> dict:
    """Check one LegalRule against the full text and individual clauses."""
    base = {
        "legal_rule_id": rule.id,
        "law_name": rule.law_name,
        "section": rule.section,
        "category": rule.category,
        "keywords_regex": rule.keywords_regex,
        "severity_weight": rule.severity_weight,
    }

    # Try matching against full document text
    match = _safe_regex_search(rule.keywords_regex, full_text)

    if match is None:
        base["status"] = "MISSING"
        base["matched_text"] = None
        base["matched_clause_index"] = None
        return base

    # Found in full text — now find which clause contains it
    base["status"] = "PRESENT"
    base["matched_text"] = match.group(0)
    base["matched_clause_index"] = _find_matching_clause(
        rule.keywords_regex, clauses
    )

    return base


def _safe_regex_search(pattern: str, text: str):
    """Run re.search with error handling for malformed patterns."""
    try:
        return re.search(pattern, text, re.IGNORECASE)
    except re.error:
        return None


def _find_matching_clause(pattern: str, clauses: list[dict]) -> int | None:
    """Find the first clause index that matches the pattern."""
    for clause in clauses:
        match = _safe_regex_search(pattern, clause.get("text", ""))
        if match is not None:
            return clause.get("index")
    return None


# ── CLI test ─────────────────────────────────────────────────────────────


if __name__ == "__main__":
    from ml_engine.clause_extractor import extract_clauses

    test_text = """
    1. ANTI-HARASSMENT POLICY

    1.1 The Company has constituted an Internal Complaints Committee (ICC)
    under the POSH Act. The ICC comprises a Presiding Officer who is a
    senior woman employee.

    1.2 The Company conducts annual awareness workshops on prevention of
    sexual harassment for all employees.

    2. DATA PRIVACY POLICY

    2.1 We collect personal data only with explicit consent from employees.
    All data is processed for specified purposes only.

    2.2 Employees have the right to access and correct their personal data.
    Grievance redressal is handled by the Data Protection Officer.

    3. LEAVE POLICY

    3.1 Female employees are entitled to 26 weeks of maternity leave for
    the first two children as per the Maternity Benefit Act.

    3.2 A creche facility is available for employees with children under 6.
    """

    clauses = extract_clauses(test_text)
    results = check_rules(test_text, clauses)
    summary = get_rule_check_summary(results)

    print("=" * 70)
    print("RULE-BASED COMPLIANCE CHECK")
    print("=" * 70)

    for r in results:
        icon = "PASS" if r["status"] == "PRESENT" else "FAIL"
        clause_info = (
            f" (clause {r['matched_clause_index']})"
            if r["matched_clause_index"]
            else ""
        )
        match_info = (
            f' matched="{r["matched_text"]}"'
            if r["matched_text"]
            else ""
        )
        print(
            f"  [{icon}] {r['law_name']} {r['section']} "
            f"(sev={r['severity_weight']}){clause_info}{match_info}"
        )

    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    print(f"Total checked:     {summary['total_rules_checked']}")
    print(f"Present:           {summary['present_count']}")
    print(f"Missing:           {summary['missing_count']}")
    print(f"Missing by cat:    {summary['missing_by_category']}")
    print(f"Critical missing:  {len(summary['critical_missing'])}")

    if summary["critical_missing"]:
        print(f"\nCRITICAL GAPS:")
        for cm in summary["critical_missing"]:
            print(f"  ! {cm['law_name']} {cm['section']} (sev={cm['severity_weight']})")
