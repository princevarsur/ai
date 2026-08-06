import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "themis.settings")
django.setup()

from policies.models import Policy
from compliance.engine import run_compliance_scan, invalidate_law_cache
from compliance.models import FlaggedIssue, ScanReport
from django.contrib.auth import get_user_model

User = get_user_model()
user, _ = User.objects.get_or_create(username='tester', defaults={'email': 't@t.com', 'role': 'compliance_officer'})

out_path = os.path.join(os.path.dirname(__file__), 'diag_output.txt')
with open(out_path, 'w') as out:
    pdf_dir = os.path.join(os.path.dirname(__file__), 'media', 'policies')
    for fname in ['HITS-IT-Policies.pdf', 'IIA_HR_Policy.pdf', 'CSE_Information_Technology_Policy.pdf']:
        path = os.path.join(pdf_dir, fname)
        if os.path.exists(path):
            out.write(f"\n==================== {fname} ====================\n")
            p, _ = Policy.objects.get_or_create(
                title=fname,
                defaults={'file': f'policies/{fname}', 'uploaded_by': user, 'category': 'general'}
            )
            p.file = f'policies/{fname}'
            p.save()
            invalidate_law_cache()
            report = run_compliance_scan(p.id, user)
            issues = FlaggedIssue.objects.filter(report=report)
            for fi in issues:
                out.write(f"ID: {fi.id} | law_name: {fi.legal_rule.law_name!r} | section: {fi.legal_rule.section!r} | status: {fi.status!r}\n")
        else:
            out.write(f"File not found: {path}\n")

print("Wrote output to diag_output.txt")
