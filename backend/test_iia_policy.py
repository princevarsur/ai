"""
Test script to run THEMIS compliance scan directly against IIA_HR_Policy.pdf
and print the results to evaluate accuracy against benchmark legal review.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "themis.settings")
import django
django.setup()

from django.contrib.auth import get_user_model
from policies.models import Policy
from compliance.engine import run_compliance_scan, invalidate_law_cache
from compliance.models import FlaggedIssue

User = get_user_model()

def main():
    user, _ = User.objects.get_or_create(
        username="iia_reviewer",
        defaults={"email": "reviewer@themis.dev", "role": "compliance_officer"},
    )

    filename = "IIA_HR_Policy.pdf"
    file_path = f"policies/{filename}"
    abs_path = os.path.join(os.path.dirname(__file__), "media", file_path)

    if not os.path.exists(abs_path):
        print(f"Error: Could not find {abs_path}")
        return

    # Extract text using ml_engine extractor
    from ml_engine.text_extractor import extract_text
    print(f"Extracting text from {filename}...")
    text = extract_text(abs_path)
    print(f"Extracted {len(text)} characters of text.")

    policy, _ = Policy.objects.get_or_create(
        title="IIA Human Resource Policy (Rev 1.1)",
        uploaded_by=user,
        defaults={
            "file": file_path,
            "category": "general",
            "extracted_text": text,
            "file_type": "pdf",
            "clause_count": 0,
        },
    )
    policy.extracted_text = text
    policy.save()

    invalidate_law_cache()

    print("\n" + "=" * 80)
    print("RUNNING THEMIS COMPLIANCE SCAN ON IIA HR POLICY")
    print("=" * 80)

    start_time = time.time()
    report = run_compliance_scan(policy.id, user)
    duration = time.time() - start_time

    issues = FlaggedIssue.objects.filter(report=report).order_by("-severity_score")

    print("\n" + "=" * 80)
    print(f"EXECUTIVE SUMMARY — OVERALL SCORE: {report.overall_score:.1f}% ({report.risk_level.upper()})")
    print("=" * 80)
    print(f"Total Clauses Analyzed : {report.total_clauses}")
    print(f"Compliant Clauses      : {report.compliant_clauses}")
    print(f"Flagged Legal Issues   : {report.flagged_clauses}")
    print(f"Execution Time         : {duration:.2f} seconds")

    print("\n" + "=" * 80)
    print("DETECTED ISSUES & VIOLATIONS (Sorted by Severity)")
    print("=" * 80)

    for idx, issue in enumerate(issues, 1):
        clause_short = issue.clause_text[:120].replace("\n", " ") + "..."
        print(f"\n[{idx}] STATUS: {issue.status.upper()} | SEVERITY: {issue.severity_score}/100")
        print(f"    Statutory Rule : {issue.legal_rule.law_name} — {issue.legal_rule.section}")
        print(f"    Policy Clause  : \"{clause_short}\"")
        print(f"    Match Signal   : MiniLM {issue.miniml_similarity:.2f} | InLegal {issue.inlegal_similarity:.2f} | NLI {getattr(issue, 'nli_label', 'N/A')}")
        print(f"    Explanation    : {issue.description[:200]}...")

if __name__ == "__main__":
    main()
