import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "themis.settings")
django.setup()

from compliance.models import ScanReport, FlaggedIssue, Requirement, AuditFinding
from policies.models import Policy

for policy in Policy.objects.all():
    print(f"\n==================== Policy: {policy.title} ====================")
    reports = ScanReport.objects.filter(policy=policy).order_by("-scanned_at")
    if not reports.exists():
        print("  No scan reports found.")
        continue
    report = reports.first()
    print(f"Report ID: {report.id} | Score: {report.overall_score:.1f} | Risk: {report.risk_level} | Clauses: {report.total_clauses} (Compliant: {report.compliant_clauses}, Flagged: {report.flagged_clauses})")
    issues = FlaggedIssue.objects.filter(report=report).order_by("-severity_score")
    for issue in issues:
        rule_name = f"{issue.legal_rule.law_name} {issue.legal_rule.section}"
        print(f"  [{issue.status.upper()}] Severity: {issue.severity_score} | Rule: {rule_name}")
        print(f"      Clause: {issue.clause_text[:120]}...")
        if issue.element_results:
            print(f"      Elements: {issue.element_results}")
