"""
Quick scoring test for sample policies.
Run via: python _score_samples.py
"""
import os, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "themis.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import django; django.setup()

from pathlib import Path
from ml_engine.text_extractor import extract_text
from ml_engine.clause_extractor import extract_clauses, get_clause_stats
from ml_engine.rule_checker import check_rules, get_rule_check_summary
from ml_engine.semantic_matcher import precompute_law_embeddings, batch_match_clauses
from ml_engine.risk_scorer import calculate_issue_severity, calculate_overall_score
from ml_engine.rule_checker import _safe_regex_search
from laws.models import LegalRule
from compliance.engine import _get_law_cache, _build_best_semantic_map, _determine_status

POLICIES = [
    ("bad_policy.txt",     "TechNova (Bad)"),
    ("average_policy.txt", "Innovate Solutions (Average)"),
    ("good_policy.txt",    "Zenith Corp (Good)"),
]

POLICY_DIR = Path(__file__).parent / "data" / "sample_policies"

print("Loading law cache (models)...")
law_cache = _get_law_cache()
all_rules = list(LegalRule.objects.filter(is_active=True))
print(f"Loaded {len(all_rules)} rules.\n")

for filename, label in POLICIES:
    fpath = POLICY_DIR / filename
    result = extract_text(str(fpath))
    full_text = result["text"]
    clauses = extract_clauses(full_text)
    stats = get_clause_stats(clauses)

    rule_results = check_rules(full_text, clauses)
    rule_map = {r["legal_rule_id"]: r for r in rule_results}

    semantic_results = batch_match_clauses(clauses, law_cache, similarity_threshold=0.3)
    best_semantic = _build_best_semantic_map(semantic_results)

    flagged = []
    compliant = 0
    for rule in all_rules:
        kw_found = rule_map.get(rule.id, {}).get("status") == "PRESENT"
        best = best_semantic.get(rule.id)
        sim = best["combined_score"] if best else 0.0
        status = _determine_status(kw_found, sim)
        if status is None:
            compliant += 1
        else:
            severity = calculate_issue_severity(status, sim, rule.severity_weight, kw_found)
            flagged.append({"severity_score": severity, "category": rule.category})

    score_data = calculate_overall_score(len(all_rules), flagged, stats["total_clauses"])

    print(f"{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  Clauses:       {stats['total_clauses']}")
    print(f"  Compliant:     {compliant}/{len(all_rules)} rules")
    print(f"  Flagged:       {len(flagged)} issues")
    print(f"  Overall Score: {score_data['overall_score']}%")
    print(f"  Risk Level:    {score_data['risk_level'].upper()}")
    print(f"  Category Scores:")
    for cat, cscore in score_data["category_scores"].items():
        flags = score_data["category_flag_counts"][cat]
        bar = "#" * int(cscore / 10) + "-" * (10 - int(cscore / 10))
        print(f"    {cat:<25} [{bar}] {cscore:>6.1f}%  ({flags} flags)")
    print()
