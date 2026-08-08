"""
backend/compliance/gliner_engine.py

Milestone 4: GLiNER Quantitative Entity Extraction & Rule-Based Comparison Engine

Features:
- Loads GLiNER model via ModelRegistry singleton.
- Zero-shot entity extraction for:
  'time period', 'monetary amount', 'percentage', 'deadline', 'statute reference', 'role/designation'.
- Deterministic rule-based numeric comparisons for threshold and conflict rules:
  * POSH complaint window: hard cut-off < 3 months -> CONFLICT; aspirational
    qualifiers ("preferably", "ideally", "at the earliest", etc.) suppress the flag
  * Wage payment timing (7th day statutory maximum)
  * Wage deduction ceiling (50% statutory maximum)
  * Earned leave carry-forward caps (Maharashtra 45 days, Karnataka 30 days)
"""

import re
import logging
from typing import List, Dict, Any, Optional, Union

from compliance.models import Requirement
from compliance.model_registry import ModelRegistry

logger = logging.getLogger(__name__)

DEFAULT_GLINER_LABELS = [
    "time period",
    "monetary amount",
    "percentage",
    "deadline",
    "statute reference",
    "role/designation",
]


def extract_entities(
    text: Union[str, List[str]],
    labels: Optional[List[str]] = None,
    threshold: float = 0.3
) -> List[Dict[str, Any]]:
    """
    Extract zero-shot named entities from text using GLiNER via ModelRegistry.

    Parameters:
    - text: str or List[str] text to process
    - labels: List[str] entity tags to extract (defaults to DEFAULT_GLINER_LABELS)
    - threshold: float confidence threshold for predictions (default 0.3)

    Returns:
    - List[Dict[str, Any]]: Extracted entities with keys {'text', 'label', 'score', 'start', 'end'}
    """
    if labels is None:
        labels = DEFAULT_GLINER_LABELS

    if not text:
        return []

    try:
        gliner_model = ModelRegistry.get_gliner()
        if isinstance(text, str):
            if not text.strip():
                return []
            raw_entities = gliner_model.predict_entities(text, labels, threshold=threshold)
            return [
                {
                    "text": e["text"],
                    "label": e["label"],
                    "score": float(e.get("score", 1.0)),
                    "start": int(e.get("start", 0)),
                    "end": int(e.get("end", 0)),
                }
                for e in raw_entities
            ]
        elif isinstance(text, list):
            results = []
            for t in text:
                if t and t.strip():
                    ents = gliner_model.predict_entities(t, labels, threshold=threshold)
                    results.extend([
                        {
                            "text": e["text"],
                            "label": e["label"],
                            "score": float(e.get("score", 1.0)),
                            "start": int(e.get("start", 0)),
                            "end": int(e.get("end", 0)),
                        }
                        for e in ents
                    ])
            return results
    except Exception as exc:
        logger.warning("GLiNER entity extraction failed: %s", exc)
        return []

    return []


# --- Numeric & Time Parsers ---

TIME_PERIOD_REGEX = re.compile(
    r'(?i)\b(\d+)\s*(?:-\s*)?(days?|working\s+days?|months?|years?|weeks?|hours?)\b'
)

ORDINAL_DAY_REGEX = re.compile(
    r'(?i)\b(\d+)(?:st|nd|rd|th)?\s+(?:day|date)\b'
)

PERCENTAGE_REGEX = re.compile(
    r'(?i)\b(\d+(?:\.\d+)?)\s*(?:%|percent\b|per\s+cent\b)'
)


def parse_time_period(text: str) -> Optional[Dict[str, Any]]:
    """
    Parse a numeric time period and unit from string text.
    Returns dict: {'value': float, 'unit': str} or None.
    """
    if not text:
        return None

    # Match standard e.g. "10 days", "3 months", "2 working days", "24 hours"
    match = TIME_PERIOD_REGEX.search(text)
    if match:
        val = float(match.group(1))
        raw_unit = match.group(2).lower()
        if 'day' in raw_unit:
            unit = 'day'
        elif 'month' in raw_unit:
            unit = 'month'
        elif 'year' in raw_unit:
            unit = 'year'
        elif 'week' in raw_unit:
            unit = 'week'
        elif 'hour' in raw_unit:
            unit = 'hour'
        else:
            unit = raw_unit
        return {"value": val, "unit": unit}

    # Match ordinal day e.g. "7th day"
    match_ord = ORDINAL_DAY_REGEX.search(text)
    if match_ord:
        val = float(match_ord.group(1))
        return {"value": val, "unit": "day"}

    return None


def parse_percentage(text: str) -> Optional[float]:
    """
    Parse a percentage value from text string.
    Returns float or None.
    """
    if not text:
        return None

    match = PERCENTAGE_REGEX.search(text)
    if match:
        return float(match.group(1))

    if re.search(r'(?i)\bhalf\b', text) or re.search(r'(?i)\b50\s*percent\b', text):
        return 50.0

    return None


def normalize_to_days(value: float, unit: str) -> float:
    """
    Convert time duration value and unit into standard days.
    """
    unit_clean = unit.lower().strip() if unit else 'day'
    if 'month' in unit_clean:
        return value * 30.0
    elif 'year' in unit_clean:
        return value * 365.0
    elif 'week' in unit_clean:
        return value * 7.0
    elif 'hour' in unit_clean:
        return value / 24.0
    return value


def evaluate_numeric_comparison(
    requirement: Requirement,
    clause_text: str,
    extracted_entities: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Perform deterministic rule-based numeric comparison between statutory requirement threshold
    and policy clause text/extracted GLiNER entities.

    Parameters:
    - requirement: Requirement object with statutory thresholds
    - clause_text: str raw text of policy clause being evaluated
    - extracted_entities: Optional list of GLiNER entities from clause_text

    Returns:
    - Dict[str, Any] with keys:
      {
          'has_numeric_rule': bool,
          'is_conflict': bool,
          'is_compliant': bool,
          'statutory_val': float,
          'statutory_unit': str,
          'extracted_val': float,
          'extracted_unit': str,
          'reason': str
      }
    """
    result = {
        'has_numeric_rule': False,
        'is_conflict': False,
        'is_compliant': False,
        'statutory_val': requirement.threshold_value,
        'statutory_unit': requirement.threshold_unit or '',
        'extracted_val': None,
        'extracted_unit': None,
        'reason': ''
    }

    stat_val = requirement.threshold_value
    stat_op = requirement.threshold_op
    stat_unit = requirement.threshold_unit or ''
    citation = requirement.statute_citation

    # Check if requirement has numeric parameters or is conflict/threshold taxonomy
    is_numeric_req = (
        stat_val is not None or
        requirement.taxonomy_type in ('threshold', 'conflict')
    )

    if not is_numeric_req:
        return result

    result['has_numeric_rule'] = True

    # 1. Specialized benchmark rule handling for known statutory rules

    # POSH Section 9(1) / POSH Complaint Window
    if "9(1)" in citation or "complaint" in requirement.title.lower() or "posh" in citation.lower():
        # Statutory window is strictly 3 months (~90 days) minimum
        time_parsed = parse_time_period(clause_text)
        if time_parsed:
            pol_val = time_parsed['value']
            pol_unit = time_parsed['unit']
            result['extracted_val'] = pol_val
            result['extracted_unit'] = pol_unit

            pol_days = normalize_to_days(pol_val, pol_unit)
            stat_days = normalize_to_days(stat_val or 3.0, stat_unit or 'month')

            # Aspirational / softening language makes a short timeframe a preference, not a
            # binding restriction.  "Preferably within 10 days" does NOT override the 3-month
            # statutory window and is therefore NOT a CONFLICT.
            _ASPIRATIONAL_QUALIFIERS = [
                "preferably", "ideally", "at the earliest", "as early as possible",
                "as soon as possible", "recommended", "encouraged", "suggested",
                "where possible", "if possible", "should aim", "endeavour",
                "endeavor", "best effort", "best endeavour",
            ]
            clause_lower = clause_text.lower()
            is_aspirational = any(q in clause_lower for q in _ASPIRATIONAL_QUALIFIERS)

            # Shorter window (e.g. 10 days or 30 days) triggers CONFLICT only when it
            # is stated as a hard mandatory cut-off, not as aspirational guidance.
            if pol_days < stat_days:
                if is_aspirational:
                    result['is_conflict'] = False
                    result['reason'] = (
                        f"Policy mentions {int(pol_val)} {pol_unit}(s) aspirationally (softening qualifier "
                        f"detected). This does not restrict the statutory 3-month window — not a conflict."
                    )
                else:
                    result['is_conflict'] = True
                    result['reason'] = (
                        f"Policy complaint window of {int(pol_val)} {pol_unit}(s) ({int(pol_days)} days) "
                        f"is shorter than statutory minimum of 3 months ({int(stat_days)} days) under POSH Act Sec 9(1)."
                    )
            else:
                result['is_compliant'] = True
                result['reason'] = f"Policy complaint window of {int(pol_val)} {pol_unit}(s) satisfies statutory minimum."
            return result

    # Wage Payment Deadline (Code on Wages Sec 17(1)(d))
    if "17(1)(d)" in citation or ("wage" in requirement.title.lower() and "disbursement" in requirement.title.lower()):
        time_parsed = parse_time_period(clause_text)
        if time_parsed:
            pol_val = time_parsed['value']
            pol_unit = time_parsed['unit']
            result['extracted_val'] = pol_val
            result['extracted_unit'] = pol_unit

            # Max allowed is 7th day
            stat_limit = stat_val or 7.0
            if pol_val > stat_limit:
                result['is_conflict'] = True
                result['reason'] = (
                    f"Policy payment day ({int(pol_val)}th day) exceeds statutory maximum 7th day limit under Code on Wages §17."
                )
            else:
                result['is_compliant'] = True
                result['reason'] = f"Policy payment day ({int(pol_val)}th day) complies with statutory 7th day limit."
            return result

    # Wage Deduction Ceiling (Code on Wages Sec 18(3))
    if "18(3)" in citation or "deduction" in requirement.title.lower():
        pct = parse_percentage(clause_text)
        if pct is not None:
            result['extracted_val'] = pct
            result['extracted_unit'] = 'percent'

            stat_limit = stat_val or 50.0
            if pct > stat_limit:
                result['is_conflict'] = True
                result['reason'] = f"Policy deduction cap of {pct}% exceeds statutory maximum {stat_limit}% limit under Code on Wages §18(3)."
            else:
                result['is_compliant'] = True
                result['reason'] = f"Policy deduction cap of {pct}% satisfies statutory {stat_limit}% cap."
            return result

    # Earned Leave Accumulation Caps (Maharashtra 45 days, Karnataka 30 days)
    if "maharashtra" in citation.lower() or "karnataka" in citation.lower() or "leave" in requirement.title.lower():
        time_parsed = parse_time_period(clause_text)
        if time_parsed:
            pol_val = time_parsed['value']
            pol_unit = time_parsed['unit']
            result['extracted_val'] = pol_val
            result['extracted_unit'] = pol_unit

            stat_limit = stat_val or (45.0 if "maharashtra" in citation.lower() else 30.0)
            if pol_val > stat_limit:
                result['is_conflict'] = True
                result['reason'] = f"Policy leave accumulation limit ({int(pol_val)} days) exceeds statutory cap of {int(stat_limit)} days."
            else:
                result['is_compliant'] = True
                result['reason'] = f"Policy leave accumulation limit ({int(pol_val)} days) complies with statutory cap of {int(stat_limit)} days."
            return result

    # 2. General fallback numeric comparison using stat_op (min, max, exact)
    time_parsed = parse_time_period(clause_text)
    pct_parsed = parse_percentage(clause_text)

    if time_parsed and any(u in stat_unit.lower() for u in ['day', 'month', 'year', 'week', 'hour']):
        pol_val = normalize_to_days(time_parsed['value'], time_parsed['unit'])
        stat_days = normalize_to_days(stat_val, stat_unit)

        result['extracted_val'] = time_parsed['value']
        result['extracted_unit'] = time_parsed['unit']

        if stat_op == 'min':
            if pol_val < stat_days:
                result['is_conflict'] = True
                result['reason'] = f"Value {pol_val} days is below minimum required threshold {stat_days} days."
            else:
                result['is_compliant'] = True
        elif stat_op == 'max':
            if pol_val > stat_days:
                result['is_conflict'] = True
                result['reason'] = f"Value {pol_val} days exceeds maximum allowed threshold {stat_days} days."
            else:
                result['is_compliant'] = True
    elif pct_parsed is not None and 'percent' in stat_unit.lower():
        result['extracted_val'] = pct_parsed
        result['extracted_unit'] = 'percent'

        if stat_op == 'max' and pct_parsed > stat_val:
            result['is_conflict'] = True
            result['reason'] = f"Percentage {pct_parsed}% exceeds statutory max {stat_val}%."
        elif stat_op == 'min' and pct_parsed < stat_val:
            result['is_conflict'] = True
            result['reason'] = f"Percentage {pct_parsed}% is below statutory min {stat_val}%."
        else:
            result['is_compliant'] = True

    return result
