"""
Risk scoring module for THEMIS compliance engine.

Combines rule-based results + AI similarity scores into:
  - Per-issue severity scores (0-100)
  - Overall document compliance score (0-100)
  - Per-category breakdowns
"""


def calculate_issue_severity(
    rule_status: str,
    max_similarity: float,
    severity_weight: int,
    keyword_found: bool,
) -> int:
    """
    Calculate severity score (0-100) for a single flagged issue.

    Args:
        rule_status: "MISSING", "CONFLICT", or "GAP"
        max_similarity: highest combined similarity score (0-1)
        severity_weight: 1-10 from LegalRule
        keyword_found: whether rule_checker found keywords

    Returns:
        Severity score 0-100. Higher = more severe.
    """
    if rule_status == "CONFLICT":
        # Clause exists but contradicts the law requirement
        base = 90
    elif rule_status == "GAP":
        # Clause partially addresses the law but incomplete
        base = 65
    elif rule_status == "MISSING":
        # No keyword found AND no meaningful semantic match
        base = 35
    else:
        base = 20

    # Scale by severity_weight (1-10) and inverse similarity
    score = base * (severity_weight / 10.0) + (1.0 - max_similarity) * 15.0

    return min(100, max(0, int(score)))


def calculate_overall_score(
    total_rules: int,
    flagged_issues: list[dict],
    total_clauses: int,
) -> dict:
    """
    Calculate overall compliance score and category breakdowns.

    Args:
        total_rules: number of active LegalRules checked
        flagged_issues: list of {"severity_score": int, "category": str}
        total_clauses: number of clauses in document

    Returns:
        {
            "overall_score": float,
            "risk_level": str,
            "category_scores": {"labour": float, ...},
            "category_flag_counts": {"labour": int, ...},
        }
    """
    if total_rules == 0:
        return {
            "overall_score": 100.0,
            "risk_level": "low",
            "category_scores": {},
            "category_flag_counts": {},
        }

    # Overall score: weighted deduction by severity and status
    total_deduction = 0.0
    for issue in flagged_issues:
        st = issue.get("status", "missing").lower()
        if st == "conflict":
            total_deduction += 15.0 * (issue["severity_score"] / 100.0)
        elif st == "gap":
            total_deduction += 8.0 * (issue["severity_score"] / 100.0)
        else:
            total_deduction += 0.5 * (issue["severity_score"] / 100.0)

    overall_score = max(0.0, min(100.0, 100.0 - total_deduction))

    # Risk level
    risk_level = _score_to_risk_level(overall_score)

    # Per-category breakdown
    category_scores, category_flag_counts = _compute_category_scores(
        total_rules, flagged_issues
    )

    return {
        "overall_score": round(overall_score, 2),
        "risk_level": risk_level,
        "category_scores": category_scores,
        "category_flag_counts": category_flag_counts,
    }


# ── Internal ─────────────────────────────────────────────────────────────


def _score_to_risk_level(score: float) -> str:
    """Map score to risk level."""
    if score >= 80:
        return "low"
    elif score >= 60:
        return "medium"
    elif score >= 40:
        return "high"
    else:
        return "critical"


def _compute_category_scores(
    total_rules: int,
    flagged_issues: list[dict],
) -> tuple[dict, dict]:
    """Compute per-category compliance scores and flag counts."""
    # Group flagged issues by category
    category_issues = {}
    for issue in flagged_issues:
        cat = issue["category"]
        if cat not in category_issues:
            category_issues[cat] = []
        category_issues[cat].append(issue)

    # All known categories
    all_categories = [
        "labour", "data_privacy", "workplace_safety",
        "employee_benefits", "corporate_governance", "cyber_security",
    ]

    category_scores = {}
    category_flag_counts = {}

    for cat in all_categories:
        issues = category_issues.get(cat, [])
        category_flag_counts[cat] = len(issues)

        if not issues:
            category_scores[cat] = 100.0
        else:
            # Category score: 100 minus average severity of its issues
            avg_severity = sum(i["severity_score"] for i in issues) / len(issues)
            category_scores[cat] = round(max(0.0, 100.0 - avg_severity), 2)

    return category_scores, category_flag_counts


# ── CLI test ─────────────────────────────────────────────────────────────


if __name__ == "__main__":
    # Test severity calculation
    print("=" * 60)
    print("SEVERITY CALCULATION TESTS")
    print("=" * 60)

    tests = [
        ("MISSING", 0.1, 10, False, "Critical missing rule"),
        ("MISSING", 0.3, 7, False, "Medium missing rule"),
        ("CONFLICT", 0.7, 9, True, "High-severity conflict"),
        ("CONFLICT", 0.5, 5, True, "Medium conflict"),
        ("GAP", 0.6, 8, True, "Partial compliance gap"),
        ("GAP", 0.8, 3, True, "Minor gap"),
    ]

    for status, sim, weight, kw, desc in tests:
        score = calculate_issue_severity(status, sim, weight, kw)
        print(f"  {desc:<30} status={status:<8} sim={sim} weight={weight:>2} => severity={score}")

    # Test overall score
    print(f"\n{'=' * 60}")
    print("OVERALL SCORE TEST")
    print("=" * 60)

    flagged = [
        {"severity_score": 90, "category": "data_privacy"},
        {"severity_score": 85, "category": "data_privacy"},
        {"severity_score": 70, "category": "workplace_safety"},
        {"severity_score": 60, "category": "labour"},
        {"severity_score": 40, "category": "employee_benefits"},
    ]

    result = calculate_overall_score(
        total_rules=22, flagged_issues=flagged, total_clauses=10
    )

    print(f"  Overall score: {result['overall_score']}")
    print(f"  Risk level:    {result['risk_level']}")
    print(f"  Category scores:")
    for cat, score in result["category_scores"].items():
        flags = result["category_flag_counts"][cat]
        print(f"    {cat:<25} score={score:>6.2f}  flags={flags}")
