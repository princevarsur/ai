import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "themis.settings")
django.setup()

from django.core.management import call_command
call_command('seed_kb')

from policies.models import Policy
from django.contrib.auth import get_user_model
from compliance.engine import run_compliance_scan, invalidate_law_cache
from compliance.models import FlaggedIssue, ScanReport, Requirement, AuditFinding

User = get_user_model()
user, _ = User.objects.get_or_create(username="test_user")

pdf_dir = os.path.join(os.path.dirname(__file__), "media", "policies")
pdfs = [
    "HITS-IT-Policies.pdf",
    "CSE_Information_Technology_Policy.pdf",
    "IIA_HR_Policy.pdf",
    "MNC_Global_Employee_Policy.pdf"
]

for pdf in pdfs:
    path = os.path.join(pdf_dir, pdf)
    if os.path.exists(path):
        print(f"=== Scanning {pdf} ===")
        policy, _ = Policy.objects.get_or_create(
            title=pdf,
            defaults={"file": f"policies/{pdf}", "category": "general", "uploaded_by": user}
        )
        invalidate_law_cache()
        report = run_compliance_scan(policy.id, user)
        print(f"Report score: {report.overall_score}, risk: {report.risk_level}")
        issues = FlaggedIssue.objects.filter(report=report)
        for issue in issues:
            print(f"  Rule: {issue.legal_rule.law_name} {issue.legal_rule.section} -> Status: {issue.status}")
            print(f"        Clause: {issue.clause_text[:100]}...")
            if hasattr(issue, "element_results"):
                print(f"        Elements: {issue.element_results}")
    else:
        print(f"File not found: {path}")
