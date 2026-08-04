"""
Empirical Calibration Script for THEMIS Semantic Matcher.
Computes real baseline similarities for DEFINITELY-UNRELATED vs DEFINITELY-RELATED pairs
to set an empirical relevance floor instead of guessing.
"""

import os
import sys
import numpy as np

# Django setup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "themis.settings")
import django
django.setup()

from laws.models import LegalRule
from ml_engine.semantic_matcher import FAST_WEIGHT, LEGAL_WEIGHT, precompute_law_embeddings, match_clause_against_laws

def find_rule(keyword=None, category=None):
    qs = LegalRule.objects.filter(is_active=True)
    if category:
        qs = qs.filter(category=category)
    if keyword:
        for r in qs:
            if keyword.lower() in (r.law_name + " " + r.section + " " + r.requirement_text).lower():
                return r
    return qs.first()

def main():
    print("=" * 75)
    print("THEMIS SEMANTIC CALIBRATION DIAGNOSTIC")
    print("=" * 75)

    # Fetch real rules from DB
    csr_rule = find_rule(keyword="135", category="corporate_governance") or find_rule(category="corporate_governance")
    dpdp_rule = find_rule(keyword="consent", category="data_privacy") or find_rule(category="data_privacy")
    mat_rule = find_rule(keyword="maternity", category="labour") or find_rule(keyword="weeks")
    posh_rule = find_rule(keyword="harassment", category="workplace_safety") or find_rule(keyword="complaint")
    pf_rule = find_rule(keyword="provident", category="employee_benefits") or find_rule(keyword="fund")
    work_rule = find_rule(keyword="hours", category="labour") or find_rule(keyword="overtime")

    rules_map = {
        "CSR": csr_rule,
        "DATA_PRIVACY": dpdp_rule,
        "MATERNITY": mat_rule,
        "POSH": posh_rule,
        "PF": pf_rule,
        "HOURS": work_rule,
    }

    print("\nSelected Reference Rules from DB:")
    for key, r in rules_map.items():
        if r:
            print(f"  [{key:<12}] {r.law_name} {r.section} -> {r.requirement_text[:70]}...")
        else:
            print(f"  [{key:<12}] WARNING: No matching rule found in DB!")

    # Prepare cache for just these reference rules to evaluate cleanly
    active_rules = [r for r in rules_map.values() if r is not None]
    law_data = [{"id": r.id, "text": r.requirement_text} for r in active_rules]
    law_cache = precompute_law_embeddings(law_data)
    rule_lookup = {r.id: r for r in active_rules}

    # 1. DEFINITELY-UNRELATED PAIRS
    unrelated_pairs = [
        ("Salary Deduction for Resignation: Employees failing to serve the full 30-day notice period will forfeit salary equal to the unserved notice duration.", csr_rule),
        ("Prevention of Sexual Harassment: The company maintains an Internal Complaints Committee (ICC) to investigate grievances under POSH guidelines.", dpdp_rule),
        ("Leave Policy: Every regular employee is entitled to 18 days of paid privilege leave and 12 days of sick leave per financial year.", csr_rule),
        ("Internet & Cyber Security Policy: All outgoing desktop traffic is monitored through centralized firewall gateways to prevent confidential data exfiltration.", mat_rule),
        ("Gratuity Entitlement: Employees completing continuous service of not less than five years shall be granted superannuation gratuity upon separation.", dpdp_rule),
        ("Corporate Governance & Audit Committee: The Board shall comprise at least one-third independent directors to oversee internal accounting auditing standards.", work_rule),
    ]

    print("\n" + "=" * 75)
    print("DISTRIBUTION 1: DEFINITELY-UNRELATED PAIRS (Should FAIL Relevance Floor)")
    print("=" * 75)
    print(f"{'Clause Topic':<26} | {'Target Statute':<22} | {'MiniLM':>7} | {'InLegal':>8} | {'Combined':>8}")
    print("-" * 75)

    unrelated_scores = []
    unrelated_minilm = []
    unrelated_inlegal = []

    for clause, rule in unrelated_pairs:
        if not rule:
            continue
        matches = match_clause_against_laws(clause, law_cache)
        # Find score for the specific rule in this pair
        target_score = next((m for m in matches if m["legal_rule_id"] == rule.id), {"miniml_similarity": 0.0, "inlegal_similarity": 0.0, "combined_score": 0.0})
        
        c_label = clause.split(":")[0][:25]
        r_label = (f"{rule.law_name} {rule.section}")[:22]
        m_sim = target_score["miniml_similarity"]
        i_sim = target_score["inlegal_similarity"]
        comb = target_score["combined_score"]

        unrelated_scores.append(comb)
        unrelated_minilm.append(m_sim)
        unrelated_inlegal.append(i_sim)

        print(f"{c_label:<26} | {r_label:<22} | {m_sim:>7.4f} | {i_sim:>8.4f} | {comb:>8.4f}")

    # 2. DEFINITELY-RELATED PAIRS
    related_pairs = [
        ("Maternity Leave Entitlement: Female employees are entitled to 26 weeks of paid maternity leave for up to two surviving children.", mat_rule),
        ("Corporate Social Responsibility: In compliance with mandates, the enterprise devotes 2% of average net profits to designated community CSR initiatives.", csr_rule),
        ("Data Consent: Personal employee data is processed exclusively upon receiving verified affirmative consent, with full right to withdraw at any time.", dpdp_rule),
        ("Workplace Harassment Grievances: To uphold dignified environments, an Internal Complaints Committee with an external NGO observer is actively functioning.", posh_rule),
        ("Provident Fund Deduction: The company contributes 12% of basic wages to statutory employee provident fund deposits each billing cycle.", pf_rule),
        ("Working Hours & Overtime: Standard shifts are capped at 9 hours daily or 48 hours weekly, beyond which overtime is disbursed at 200% wage rate.", work_rule),
    ]

    print("\n" + "=" * 75)
    print("DISTRIBUTION 2: DEFINITELY-RELATED PAIRS (Should CLEAR Relevance Floor)")
    print("=" * 75)
    print(f"{'Clause Topic':<26} | {'Target Statute':<22} | {'MiniLM':>7} | {'InLegal':>8} | {'Combined':>8}")
    print("-" * 75)

    related_scores = []
    related_minilm = []
    related_inlegal = []

    for clause, rule in related_pairs:
        if not rule:
            continue
        matches = match_clause_against_laws(clause, law_cache)
        target_score = next((m for m in matches if m["legal_rule_id"] == rule.id), {"miniml_similarity": 0.0, "inlegal_similarity": 0.0, "combined_score": 0.0})
        
        c_label = clause.split(":")[0][:25]
        r_label = (f"{rule.law_name} {rule.section}")[:22]
        m_sim = target_score["miniml_similarity"]
        i_sim = target_score["inlegal_similarity"]
        comb = target_score["combined_score"]

        related_scores.append(comb)
        related_minilm.append(m_sim)
        related_inlegal.append(i_sim)

        print(f"{c_label:<26} | {r_label:<22} | {m_sim:>7.4f} | {i_sim:>8.4f} | {comb:>8.4f}")

    print("\n" + "=" * 75)
    print("STATISTICAL SUMMARY & RECOMMENDATION")
    print("=" * 75)
    print(f"UNRELATED COMBINED -> Min: {min(unrelated_scores):.4f} | Max: {max(unrelated_scores):.4f} | Mean: {np.mean(unrelated_scores):.4f}")
    print(f"RELATED COMBINED   -> Min: {min(related_scores):.4f} | Max: {max(related_scores):.4f} | Mean: {np.mean(related_scores):.4f}")
    print("-" * 75)
    print(f"UNRELATED MiniLM   -> Min: {min(unrelated_minilm):.4f} | Max: {max(unrelated_minilm):.4f} | Mean: {np.mean(unrelated_minilm):.4f}")
    print(f"RELATED MiniLM     -> Min: {min(related_minilm):.4f} | Max: {max(related_minilm):.4f} | Mean: {np.mean(related_minilm):.4f}")
    print("-" * 75)
    print(f"UNRELATED InLegal  -> Min: {min(unrelated_inlegal):.4f} | Max: {max(unrelated_inlegal):.4f} | Mean: {np.mean(unrelated_inlegal):.4f}")
    print(f"RELATED InLegal    -> Min: {min(related_inlegal):.4f} | Max: {max(related_inlegal):.4f} | Mean: {np.mean(related_inlegal):.4f}")
    print("=" * 75)

if __name__ == "__main__":
    main()
