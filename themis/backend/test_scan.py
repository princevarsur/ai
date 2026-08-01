import os
import sys
import django

sys.path.append('c:/Users/vruti/Desktop/THMS/themis/backend')
os.environ['DJANGO_SETTINGS_MODULE'] = 'themis.settings'
django.setup()

from compliance.engine import run_compliance_scan
from django.contrib.auth import get_user_model
from policies.models import Policy

User = get_user_model()
user = User.objects.first()

from compliance.engine import run_compliance_scan, _get_law_cache, batch_match_clauses, _determine_status, _build_best_semantic_map
from ml_engine.clause_extractor import extract_clauses
from ml_engine.text_extractor import extract_text
from ml_engine.rule_checker import check_rules

for p in Policy.objects.all().order_by('id'):
    print(f"\n--- Testing Policy: {p.title} ---")
    report = run_compliance_scan(p.id, user)
    print(f"Score: {report.overall_score}")
    print(f"Flagged Issues Count: {report.flagged_issues.count()}")
    for issue in report.flagged_issues.all():
        print(f" - {issue.status}: {issue.legal_rule.law_name}")

