"""
ml_engine/domain_classifier.py

Multi-tier Domain & Topical Alignment Engine + Contradiction vs Silence Firewall.
Prevents semantic matching hallucinations across incompatible domains and stops
silent or orthogonal procedures from being falsely flagged as legal contradictions.
"""
from __future__ import annotations

import re
import logging

logger = logging.getLogger(__name__)

# ── Document Domain Categorization ───────────────────────────────────────────
DOMAINS = {
    "IT_AND_SECURITY": {"cyber_security", "data_privacy"},
    "HUMAN_RESOURCES": {"labour", "employee_benefits", "workplace_safety", "contracts"},
    "CORPORATE_GOVERNANCE": {"corporate_governance"},
    "DATA_PRIVACY": {"data_privacy", "cyber_security"},
}

def classify_document_domain(title: str, full_text: str) -> set[str]:
    """
    Classify overall policy document domain by title and lexical density.
    Prevents dedicated technical manuals (e.g. IT/Cyber Security policies) from
    being evaluated against unrelated labor union or corporate board statutes.
    """
    title_low = title.lower()
    text_sample = full_text[:3000].lower() + " " + title_low
    
    # Check if this is explicitly a dedicated IT, Security, or Systems Policy
    it_keywords = ["information technology", "it policy", "cyber security", "information security", "acceptable use", "network security", "data security policy", "access control"]
    if any(k in title_low for k in it_keywords) or (title_low.endswith("it policy.pdf") or "cse information technology" in title_low):
        return {"IT_AND_SECURITY", "DATA_PRIVACY"}
        
    # Check if corporate governance / board charter
    if any(k in title_low for k in ["audit committee", "board charter", "corporate governance", "csr policy", "whistleblower"]):
        return {"CORPORATE_GOVERNANCE"}
        
    # Check if HR / Employee Handbook
    hr_keywords = ["employee handbook", "hr policy", "standing orders", "code of conduct", "human resources", "staff regulations", "service rules"]
    if any(k in title_low for k in hr_keywords):
        return {"HUMAN_RESOURCES", "DATA_PRIVACY", "IT_AND_SECURITY", "CORPORATE_GOVERNANCE"}

    # Fallback: General document, cover all domains
    return {"HUMAN_RESOURCES", "DATA_PRIVACY", "IT_AND_SECURITY", "CORPORATE_GOVERNANCE"}


def is_rule_in_document_scope(rule_category: str, doc_domains: set[str]) -> bool:
    """Verify if rule category is applicable to the classified document domains."""
    for domain in doc_domains:
        allowed_categories = DOMAINS.get(domain, set())
        if rule_category in allowed_categories:
            return True
    return False


# ── Clause-Level Topical Alignment Gate ──────────────────────────────────────

def check_clause_topical_alignment(clause_text: str, rule) -> bool:
    """
    Deterministic concept gating to prevent semantic embedding hallucinations.
    Ensures exact statutory subject matter alignment before any NLI or gap analysis.
    """
    c_low = clause_text.lower()
    r_law = rule.law_name.lower()
    r_req = rule.requirement_text.lower()
    r_sec = rule.section.lower()

    # 1. Companies Act / Section 177 (Audit Committee & Board Governance)
    if "companies act" in r_law or "177" in r_sec or "audit committee" in r_req or "independent director" in r_req:
        board_terms = ["board", "director", "directors", "independent director", "shareholder", "audit committee", "csr", "corporate governance", "statutory committee", "board of directors"]
        if not any(w in c_low for w in board_terms):
            # If clause mentions system/software audit without board governance terms, reject
            return False

    # 2. Industrial Relations Code / Trade Union & Collective Bargaining
    if "industrial relations" in r_law or "trade union" in r_req or "collective bargaining" in r_req or "section 4" in r_sec and "trade" in r_req:
        union_terms = ["union", "trade union", "collective", "association", "strike", "lockout", "labour organization", "bargaining"]
        if not any(w in c_low for w in union_terms):
            return False
        # Reject Identity and Access Management (IAM) exit deactivation clauses
        if any(w in c_low for w in ["access privileges", "end of life", "deactivate", "credentials", "login", "user account", "system access"]):
            return False

    # 3. DPDP Section 6 (Consent for Biometrics & Sensitive Employee Data)
    if ("dpdp" in r_law or "data protection" in r_law) and ("section 6" in r_sec or "biometric" in r_req or "consent" in r_req):
        bio_terms = ["biometrics", "biometric", "fingerprint", "facial recognition", "iris", "retina", "attendance scanning", "sensitive personal data", "consent declaration", "explicit consent", "itemized consent", "consent of data principal"]
        if not any(w in c_low for w in bio_terms):
            return False

    # 4. DPDP Section 8(4) (Post-Employment Data Erasure)
    if ("dpdp" in r_law or "data protection" in r_law) and ("8(4)" in r_sec or "erasure" in r_req or "post-employment" in r_req):
        retention_terms = ["erasure", "erase", "delete", "deletion", "retention period", "destroy", "post-employment", "separation of an employee", "upon separation", "ex-employee data", "retention schedule", "purging"]
        if not any(w in c_low for w in retention_terms):
            return False

    # 5. DPDP Section 10 (Personal Data Breach Notification)
    if ("dpdp" in r_law or "data protection" in r_law) and ("section 10" in r_sec or "breach" in r_req):
        breach_terms = ["breach", "leak", "unauthorized access", "incident", "compromise", "notification", "report", "cert-in", "data protection board", "dpb"]
        if not any(w in c_low for w in breach_terms):
            return False

    # 6. Code on Wages / Salary / Deductions
    if "wages" in r_law or "salary" in r_req or "deduction" in r_req or "forfeiture" in r_req:
        wage_terms = ["salary", "wage", "wages", "remuneration", "pay", "deduct", "deduction", "forfeit", "forfeiture", "notice period pay", "recovery", "stipend"]
        if not any(w in c_low for w in wage_terms):
            return False
            
    # 7. POSH Act / Sexual Harassment
    if "posh" in r_law or "sexual harassment" in r_req:
        if not any(w in c_low for w in ["posh", "harassment", "sexual", "woman", "women", "icc", "internal committee", "gender", "aggrieved", "respondent"]):
            return False

    # 8. Maternity Benefit Act
    if "maternity" in r_law or "creche" in r_req:
        if not any(w in c_low for w in ["maternity", "pregnancy", "creche", "nursing", "mother", "maternal", "child", "woman", "women"]):
            return False

    # 9. Indian Contract Act / Non-Compete
    if "contract act" in r_law or "non-compete" in r_req or "restraint of trade" in r_req:
        if not any(w in c_low for w in ["compete", "competitor", "restraint", "prohibit", "restriction", "post-termination", "working after", "joining"]):
            return False

    return True


# ── Contradiction vs Silence Firewall ────────────────────────────────────────

EXPLICIT_NEGATION_LEXICON = {
    "does not", "do not", "shall not", "is not required", "exempt",
    "without any obligation", "no responsibility", "forever", "indefinitely",
    "perpetuity", "at its sole discretion without inquiry", "without inquiry",
    "without any inquiry", "without notice or hearing", "without assigning any reason",
    "forfeit", "forfeited", "permanently retain", "deemed to have quit", "deemed resignation",
    "never delete", "no obligation to notify", "not required to notify",
    "deduct full", "deduct entire", "withhold all", "permanently withhold"
}

def verify_real_contradiction(clause_text: str, is_qty_conflict: bool = False, is_high_risk: bool = False) -> bool:
    """
    Contradiction vs Silence Firewall.
    A missing or silent provision is not a contradiction. An NLI 'contradiction' label
    on orthogonal or silent procedural descriptions is downgraded unless there is an
    explicit negation, unlawful exclusion, high-risk antipattern, or numeric incompatibility.
    """
    if is_qty_conflict or is_high_risk:
        return True
        
    c_low = clause_text.lower()
    return any(term in c_low for term in EXPLICIT_NEGATION_LEXICON)
