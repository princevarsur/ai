import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "themis.settings")
django.setup()

from django.core.management import call_command
call_command('seed_laws')
call_command('seed_kb')

from policies.models import Policy
from compliance.engine import run_compliance_scan, invalidate_law_cache
from compliance.models import FlaggedIssue, Requirement, AuditFinding
from django.contrib.auth import get_user_model

User = get_user_model()
user, _ = User.objects.get_or_create(username='tester', defaults={'email': 't@t.com', 'role': 'compliance_officer'})

pdf_dir = os.path.join(os.path.dirname(__file__), 'media', 'policies')
fname = 'CSE_Information_Technology_Policy.pdf'
path = os.path.join(pdf_dir, fname)

p, _ = Policy.objects.get_or_create(title=fname, defaults={'file': f'policies/{fname}', 'uploaded_by': user, 'category': 'general'})
p.file = f'policies/{fname}'
p.uploaded_by = user
p.save()

invalidate_law_cache()
report = run_compliance_scan(p.id, user)

print(f"\nReport overall_score={report.overall_score}, risk={report.risk_level}, clauses={report.total_clauses}")
issues = FlaggedIssue.objects.filter(report=report)
for fi in issues:
    print(f"\nIssue ID: {fi.id}")
    print(f"  Law: {fi.legal_rule.law_name} | Sec: {fi.legal_rule.section}")
    print(f"  Status: {fi.status}")
    print(f"  Severity: {fi.severity_score}")
    print(f"  Clause: {fi.clause_text[:150]}...")
