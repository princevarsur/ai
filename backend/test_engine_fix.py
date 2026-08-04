"""
Test script: run compliance scan on bad_policy.txt and good_policy.txt,
print total flag count and status breakdown for each.
"""
import os
import sys
import shutil
import django

# ── Django bootstrap ─────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "themis.settings")
django.setup()

from django.contrib.auth import get_user_model
from policies.models import Policy
from compliance.engine import run_compliance_scan, invalidate_law_cache
from compliance.models import ScanReport, FlaggedIssue

User = get_user_model()

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "data", "sample_policies")


def get_or_create_test_user():
    user, _ = User.objects.get_or_create(
        username="engine_test_user",
        defaults={"email": "test@themis.dev", "role": "compliance_officer"},
    )
    return user


def upload_and_scan(filename: str, user):
    """Upload a test policy file, run scan, print results."""
    filepath = os.path.join(SAMPLE_DIR, filename)
    if not os.path.exists(filepath):
        print(f"  ERROR: {filepath} not found")
        return

    # Copy file into media/policies/ so extract_text() finds it
    media_dir = os.path.join(os.path.dirname(__file__), "media", "policies")
    os.makedirs(media_dir, exist_ok=True)
    dest_path = os.path.join(media_dir, filename)
    shutil.copy2(filepath, dest_path)

    # Read the file text
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    # Create or reuse policy
    title = filename.replace(".txt", "").replace("_", " ").title()
    policy, created = Policy.objects.get_or_create(
        title=f"[TEST] {title}",
        uploaded_by=user,
        defaults={
            "file": f"policies/{filename}",
            "category": "general",
            "extracted_text": text,
            "file_type": "txt",
            "clause_count": 0,
        },
    )

    # If reusing, update the text and ensure file field points correctly
    if not created:
        policy.extracted_text = text
        policy.file = f"policies/{filename}"
        policy.save(update_fields=["extracted_text", "file"])

    # Force fresh law cache
    invalidate_law_cache()

    print(f"\n{'=' * 70}")
    print(f"  SCANNING: {filename}")
    print(f"{'=' * 70}")

    report = run_compliance_scan(policy.id, user)

    # Fetch persisted issues
    issues = FlaggedIssue.objects.filter(report=report)

    # Status breakdown
    status_counts = {}
    for issue in issues:
        s = issue.status.upper()
        status_counts[s] = status_counts.get(s, 0) + 1

    print(f"\n  RESULTS FOR: {filename}")
    print(f"  {'─' * 50}")
    print(f"  Overall Score:     {report.overall_score:.1f}%")
    print(f"  Risk Level:        {report.risk_level.upper()}")
    print(f"  Total Clauses:     {report.total_clauses}")
    print(f"  Compliant Clauses: {report.compliant_clauses}")
    print(f"  Flagged Issues:    {report.flagged_clauses}")
    print(f"  Scan Duration:     {report.scan_duration_seconds:.2f}s")
    print(f"\n  STATUS BREAKDOWN:")
    for status_label in ["MISSING", "CONFLICT", "GAP"]:
        count = status_counts.get(status_label, 0)
        print(f"    {status_label:<12} {count}")
    print(f"    {'TOTAL':<12} {sum(status_counts.values())}")

    # Print first few flagged issues for inspection
    print(f"\n  SAMPLE FLAGS (first 5):")
    for i, issue in enumerate(issues[:5]):
        clause_preview = issue.clause_text[:80].replace("\n", " ")
        print(
            f"    [{issue.status.upper():<8}] sev={issue.severity_score:>3} "
            f"| {issue.legal_rule.law_name} {issue.legal_rule.section}"
        )
        print(f"             clause: \"{clause_preview}...\"")

    return report


def main():
    user = get_or_create_test_user()

    print("\n" + "=" * 70)
    print("  THEMIS ENGINE TEST — Fixed Decision Logic")
    print("  Relevance floor=0.3, one-flag-per-requirement, 4-way NLI tree")
    print("=" * 70)

    bad_report = upload_and_scan("bad_policy.txt", user)
    good_report = upload_and_scan("good_policy.txt", user)

    # Summary comparison
    if bad_report and good_report:
        print(f"\n{'=' * 70}")
        print("  COMPARISON SUMMARY")
        print(f"{'=' * 70}")
        print(f"  {'Metric':<25} {'bad_policy':>15} {'good_policy':>15}")
        print(f"  {'─' * 55}")
        print(f"  {'Overall Score':<25} {bad_report.overall_score:>14.1f}% {good_report.overall_score:>14.1f}%")
        print(f"  {'Risk Level':<25} {bad_report.risk_level:>15} {good_report.risk_level:>15}")
        print(f"  {'Total Flags':<25} {bad_report.flagged_clauses:>15} {good_report.flagged_clauses:>15}")
        print(f"  {'Compliant':<25} {bad_report.compliant_clauses:>15} {good_report.compliant_clauses:>15}")

        bad_issues = FlaggedIssue.objects.filter(report=bad_report)
        good_issues = FlaggedIssue.objects.filter(report=good_report)

        for label in ["MISSING", "CONFLICT", "GAP"]:
            bc = bad_issues.filter(status=label.lower()).count()
            gc = good_issues.filter(status=label.lower()).count()
            print(f"  {label + ' count':<25} {bc:>15} {gc:>15}")


if __name__ == "__main__":
    main()
