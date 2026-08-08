"""
backend/compliance/topical_filter.py

Topical keyword filtering to prevent false positive retrieval matches.

Prevents cases like:
- Paternity leave clauses (30 days) flagged against POSH complaint window (3 months)
- IT equipment clauses flagged against bodily privacy surveillance
- General HR clauses flagged against specific statutory domains

Strategy:
- For high-risk false-positive requirement IDs, enforce mandatory keyword presence
- If clause lacks ANY required keyword, skip NLI evaluation entirely
- Applied AFTER retrieval but BEFORE NLI gate for performance
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# Mandatory keyword whitelist per statutory requirement
# Key: statute_citation pattern | Value: list of required keywords (any one must be present)
REQUIRED_KEYWORDS_MAP = {
    # POSH Act Section 9(1) — Complaint Filing Window (3 months)
    'POSH Act 2013 Section 9': [
        'harassment', 'sexual harassment', 'complaint', 'aggrieved',
        'internal complaints committee', 'icc', 'local complaints committee',
        'posh', 'grievance', 'aggrieved woman', 'unwelcome', 'sexual favour'
    ],
    
    # POSH Act Section 4(2) — Internal Complaints Committee Constitution
    'POSH Act 2013 Section 4': [
        'internal complaints committee', 'icc', 'presiding officer',
        'posh committee', 'harassment committee', 'sexual harassment committee',
        'women employee', 'external member', 'local complaints committee'
    ],
    
    # IT Act Section 66E — Bodily Privacy / Surveillance
    # Bug 3 Fix: 'privacy' alone is far too broad — it matches acceptable-use
    # clauses ("network access… privacy") and general data-privacy statements.
    # Section 66E is specifically about capturing/transmitting images of private
    # body parts.  Require at least one surveillance/recording/capture term so
    # that generic privacy-of-communications clauses are excluded.
    'IT Act 2000 Section 66E': [
        'surveillance', 'bodily privacy', 'camera', 'video recording',
        'recording', 'cctv', 'image capture', 'capture image', 'voyeurism',
        'private area', 'private parts', 'intimate image', 'body parts',
        'transmit image', 'publish image', 'photograph', 'filming',
        'monitor employee', 'covert recording', 'hidden camera',
    ],
    
    # IT Act Section 43A — Reasonable Security Practices
    'IT Act 2000 Section 43A': [
        'sensitive personal data', 'security practices', 'data protection',
        'negligence', 'wrongful loss', 'data breach', 'compensation',
        'reasonable security', 'body corporate', 'information'
    ],
    
    # DPDP Act Section 6 — Consent Notice
    'DPDP Act 2023 Section 6': [
        'consent', 'data principal', 'notice', 'personal data',
        'data fiduciary', 'purpose', 'withdrawal of consent', 'consent notice',
        'data processing', 'information', 'collection'
    ],
    
    # DPDP Act Section 7 — Aadhaar Restrictions
    'DPDP Act 2023 Section 7': [
        'aadhaar', 'unique identity', 'alternative id', 'identity document',
        'voluntary', 'government-issued id', 'proof of identity', 'authentication'
    ],
    
    # DPDP Act Section 8(6) — Data Breach Notification
    'DPDP Act 2023 Section 8': [
        'data breach', 'breach notification', 'data protection board',
        'cert-in', 'notify', 'personal data breach', 'security incident',
        'data fiduciary', 'board', 'information'
    ],
    
    # Payment of Wages Act Section 7 — Wage Payment Timing (7th day)
    'Payment of Wages Act 1936 Section 7': [
        'wage', 'salary', 'payment', 'pay day', 'wages period',
        'working day', 'remuneration', 'compensation', 'disbursement'
    ],
    
    # Maternity Benefit Act Section 12 — 26 weeks maternity leave
    'Maternity Benefit Act 1961 Section 12': [
        'maternity', 'maternity leave', 'pregnancy', 'childbirth', 'confinement',
        'delivery', 'woman employee', 'expected delivery', 'prenatal', 'postnatal',
        'woman worker', 'expectant mother'
    ],
    
    # Companies Act Section 177 — Audit Committee & Vigil Mechanism
    'Companies Act 2013 Section 177': [
        'audit committee', 'vigil mechanism', 'whistle blower', 'whistleblower',
        'directors', 'board', 'independent director', 'corporate governance',
        'financial statement', 'internal control', 'related party transaction'
    ],
    
    # OSHWC Code 2020 Section 25(1)(a) / Factories Act Section 51 — Daily Working Hours (8 hours max)
    'OSHWC Code 2020 Section 25': [
        'working hours', 'work hours', 'daily hours', 'hours per day', 'hours of work',
        'shift', 'shift duration', 'work day', 'workday', 'overtime', 'extended hours',
        'maximum hours', 'hour limit', 'rostered hours', 'duty hours', 'clock in',
        'time sheet', 'attendance hours', 'shift timings'
    ],
    
    'Factories Act 1948 Section 51': [
        'working hours', 'work hours', 'daily hours', 'hours per day', 'hours of work',
        'shift', 'shift duration', 'work day', 'workday', 'overtime', 'extended hours',
        'maximum hours', 'hour limit', 'rostered hours', 'duty hours', 'adult worker',
        'time sheet', 'attendance hours', 'shift timings', 'spread over'
    ],
    
    # OSHWC Code 2020 Section 26 / Factories Act Section 52 — Weekly Working Hours (48 hours max)
    'OSHWC Code 2020 Section 26': [
        'weekly hours', 'hours per week', 'work week', 'working hours', 'workweek',
        'weekly limit', '48 hours', 'average hours', 'overtime', 'weekly schedule'
    ],
    
    'Factories Act 1948 Section 52': [
        'weekly hours', 'hours per week', 'work week', 'working hours', 'workweek',
        'weekly limit', '48 hours', 'average hours', 'overtime', 'adult worker'
    ],
    
    # OSHWC Code 2020 Section 27 / Factories Act Section 54 — Weekly Rest Day
    'OSHWC Code 2020 Section 27': [
        'weekly off', 'rest day', 'weekly holiday', 'weekly rest', 'day off',
        'compensatory off', 'weekly leave', 'sunday', 'weekly closure'
    ],
    
    'Factories Act 1948 Section 54': [
        'weekly off', 'rest day', 'weekly holiday', 'weekly rest', 'day off',
        'compensatory off', 'weekly leave', 'sunday', 'adult worker'
    ],

    # Contract Act 1872 Section 27 — Agreement in Restraint of Trade (void-if-present)
    # Bug 4 Fix: This rule should ONLY be evaluated when the clause actually contains
    # non-compete / restraint-of-trade language.  Generic compliance obligations,
    # leave entitlements, and professional conduct rules share zero subject matter
    # with Section 27 and must be excluded before any NLI evaluation.
    'Contract Act 1872 Section 27': [
        'non-compete', 'non compete', 'restraint of trade', 'restraint from trade',
        'post-termination', 'post termination', 'after leaving', 'after separation',
        'competitor', 'competing business', 'competing organisation', 'competing organization',
        'join competitor', 'work for competitor', 'prohibited from working',
        'not engage in', 'not carry on', 'not involved in', 'refrain from engaging',
        'restrictive covenant', 'exclusivity clause', 'garden leave',
    ],
}


def has_required_keywords(clause_text: str, statute_citation: str) -> bool:
    """
    Check if clause contains at least one required keyword for the given statute.
    
    Returns:
        True if clause is topically relevant (or if no keyword filter exists).
        False if clause is topically irrelevant and should be skipped.
    """
    if not clause_text or not statute_citation:
        return True
    
    # Match statute_citation against patterns in REQUIRED_KEYWORDS_MAP
    required_keywords = None
    for pattern, keywords in REQUIRED_KEYWORDS_MAP.items():
        if pattern.lower() in statute_citation.lower():
            required_keywords = keywords
            break
    
    # If no keyword filter exists for this statute, allow through
    if not required_keywords:
        return True
    
    clause_lower = clause_text.lower()
    
    # Check if ANY required keyword is present
    for keyword in required_keywords:
        if keyword.lower() in clause_lower:
            return True
    
    # No required keyword found — reject clause as topically irrelevant
    logger.debug(
        "Topical filter rejected clause for %s: missing keywords %s",
        statute_citation, required_keywords[:3]
    )
    return False


def filter_topically_invalid_candidates(
    candidates: List[dict],
    statute_citation: str
) -> List[dict]:
    """
    Filter retrieved candidates by topical keyword presence.
    
    Removes candidates that lack required keywords for the given statute,
    preventing false positive NLI evaluations.
    
    Parameters:
        candidates: List of retrieval candidate dicts with 'raw_text' key
        statute_citation: Canonical statute citation string
    
    Returns:
        Filtered list of topically valid candidates.
    """
    if not candidates or not statute_citation:
        return candidates
    
    filtered = []
    rejected_count = 0
    
    for cand in candidates:
        clause_text = cand.get('raw_text', '')
        if has_required_keywords(clause_text, statute_citation):
            filtered.append(cand)
        else:
            rejected_count += 1
    
    if rejected_count > 0:
        logger.info(
            "Topical filter rejected %d/%d candidates for %s (missing required keywords)",
            rejected_count, len(candidates), statute_citation
        )
    
    return filtered
