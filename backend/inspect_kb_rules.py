import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "themis.settings")
django.setup()

from django.core.management import call_command
call_command('seed_kb')

from laws.models import LegalRule
from compliance.models import Requirement

print("\n--- LegalRule Objects ---")
for r in LegalRule.objects.all():
    print(f"ID: {r.id} | Law: '{r.law_name}' | Sec: '{r.section}' | Category: '{r.category}'")

print("\n--- Requirement Objects ---")
for req in Requirement.objects.all():
    print(f"ID: {req.id} | Statute: '{req.statute_citation}' | Title: '{req.title}' | Taxonomy: '{req.taxonomy_type}'")
