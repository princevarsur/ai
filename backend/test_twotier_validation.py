"""
Validation scan: real_world_test_1.txt against the two-tier threshold engine.
Prints full status + law/section for every flagged issue.
"""
import os
import sys
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "themis.settings")
import django
django.setup()

from django.contrib.auth import get_user_model
from policies.models import Policy
from compliance.engine import run_compliance_scan, invalidate_law_cache
from compliance.models import ScanReport, FlaggedIssue

User = get_user_model()

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "data", "sample_policies")

def main():
    user, _ = User.objects.get_or_create(
        username="validation_user_v2",
        defaults={"email": "val2@themis.dev", "role": "compliance_officer"},
    )

    filename = "real_world_test_1.txt"
    src = os.path.join(SAMPLE_DIR, filename)

    # Copy into media/policies/ for extract_text()
    media_dir = os.path.join(os.path.dirname(__file__), "media", "policies")
    os.makedirs(media_dir, exist_ok=True)
    shutil.copy2(src, os.path.join(media_dir, filename))

    with open(src, "r", encoding="utf-8") as f:
        text = f.read()

    policy, created = Policy.objects.get_or_create(
        title="[VALIDATION-v2] Real World Test 1",
        uploaded_by=user,
        defaults={
            "file": f"policies/{filename}",
            "category": "general",
            "extracted_text": text,
            "file_type": "txt",
            "clause_count": 10,
        },
    )
    if not created:
        policy.extracted_text = text
        policy.file = f"policies/{filename}"
        policy.save(update_fields=["extracted_text", "file"])

    invalidate_law_cache()

    print("=" * 80)
    print("TWO-TIER VALIDATION SCAN (MIN_RELEVANCE=0.55, STRONG_MATCH=0.65)")
    print("=" * 80)

    report = run_compliance_scan(policy.id, user)
    issues = FlaggedIssue.objects.filter(report=report).order_by("-severity_score")

    status_counts = {}
    for issue in issues:
        s = issue.status.upper()
        status_counts[s] = status_counts.get(s, 0) + 1

    print("\n" + "=" * 80)
    print("SCAN SUMMARY")
    print("=" * 80)
    print(f"Overall Score:     {report.overall_score:.1f}%")
    print(f"Risk Level:        {report.risk_level.upper()}")
    print(f"Total Clauses:     {report.total_clauses}")
    print(f"Compliant Clauses: {report.compliant_clauses}")
    print(f"Flagged Issues:    {report.flagged_clauses}")
    print(f"Scan Duration:     {report.scan_duration_seconds:.2f}s")

    print("\nSTATUS BREAKDOWN:")
    for label in ["MISSING", "CONFLICT", "GAP"]:
        print(f"  {label:<12}: {status_counts.get(label, 0)}")
    print(f"  {'TOTAL':<12}: {sum(status_counts.values())}")

    print("\n" + "=" * 80)
    print("FULL ISSUE DETAIL (sorted by severity)")
    print("=" * 80)
    for i, issue in enumerate(issues, 1):
        clause_short = issue.clause_text[:100].replace("\n", " ")
        combined = 0.4 * issue.miniml_similarity + 0.6 * issue.inlegal_similarity
        nli = getattr(issue, "nli_label", "N/A")
        print(f"\n--- Issue {i} ---")
        print(f"  Status:   {issue.status.upper()}")
        print(f"  Severity: {issue.severity_score}")
        print(f"  Law:      {issue.legal_rule.law_name}")
        print(f"  Section:  {issue.legal_rule.section}")
        print(f"  MiniLM:   {issue.miniml_similarity:.4f}")
        print(f"  InLegal:  {issue.inlegal_similarity:.4f}")
        print(f"  Combined: {combined:.4f}")
        print(f"  NLI:      {nli}")
        print(f"  Clause:   \"{clause_short}\"")
        print(f"  Explain:  {issue.description[:150]}")

    # Check specific expected outcomes
    print("\n" + "=" * 80)
    print("EXPECTED OUTCOME CHECKS")
    print("=" * 80)

    checks = [
        ("Clause 3 vs Labour Code", "Leave Policy", "CONFLICT",
         "Should NOT be CONFLICT (generic deferral, nothing to contradict)"),
        ("Clause 9 vs POSH Act 13", "Attendance", "any match vs POSH",
         "Should NOT appear - completely unrelated topic"),
        ("Clause 10 vs Companies Act 135", "Salary Deduction", "any match vs Companies Act.*135",
         "Should NOT appear - unrelated topic"),
        ("Clause 10 vs Labour/Industrial", "Salary Deduction", "CONFLICT vs Labour",
         "SHOULD be CONFLICT - deliberately illegal clause"),
    ]

    for check_name, clause_keyword, expected, note in checks:
        matching = [
            iss for iss in issues
            if clause_keyword.lower() in iss.clause_text.lower()
        ]
        if matching:
            for m in matching:
                comb = 0.4 * m.miniml_similarity + 0.6 * m.inlegal_similarity
                marker = "PASS" if "Should NOT" not in note or m.status.upper() != "CONFLICT" else "FAIL"
                print(f"  [{marker}] {check_name}: {m.status.upper()} vs {m.legal_rule.law_name} {m.legal_rule.section} (combined={comb:.3f})")
        else:
            marker = "PASS" if "Should NOT appear" in note else "FAIL"
            print(f"  [{marker}] {check_name}: No match found. ({note})")

if __name__ == "__main__":
    main()
