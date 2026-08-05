"""
ml_engine/quantity_checker.py

Deterministic numeric quantity extraction and conflict detection.
Catches cases like "12 weeks maternity leave" when the law requires ≥ 26 weeks.

Two-pass extraction:
  1. PRIMARY: spaCy NER — CARDINAL / QUANTITY / PERCENT / MONEY entities,
     then check surrounding tokens for a unit word.
  2. FALLBACK: regex + word2number for spelled-out numbers.
"""

from __future__ import annotations

import re
import logging

logger = logging.getLogger(__name__)

# ─── Unit normalization ────────────────────────────────────────────────────

# Map raw token text → canonical unit
_UNIT_MAP: dict[str, str] = {
    # Time
    "week": "weeks", "weeks": "weeks",
    "day": "days", "days": "days",
    "month": "months", "months": "months",
    "year": "years", "years": "years",
    # Percentage
    "%": "percent", "percent": "percent", "percentage": "percent",
    # Money
    "inr": "inr", "rupee": "inr", "rupees": "inr", "rs": "inr", "lakh": "inr",
    "crore": "inr",
    # Generic
    "employee": "employees", "employees": "employees",
    "member": "members", "members": "members",
}

_UNIT_PATTERN = re.compile(
    r"\b(weeks?|days?|months?|years?|%|percent(?:age)?|inr|rupees?|rs\.?|lakh|crore|employees?|members?)\b",
    re.IGNORECASE,
)

_NUMERIC_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*"
    r"(weeks?|days?|months?|years?|%|percent(?:age)?|inr|rupees?|rs\.?|lakh|crore|employees?|members?)",
    re.IGNORECASE,
)

# word2number mapping for small integers commonly seen in policy text
_WORD_NUM: dict[str, float] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "twenty-one": 21, "twenty-two": 22,
    "twenty-three": 23, "twenty-four": 24, "twenty-five": 25,
    "twenty-six": 26, "twenty-seven": 27, "twenty-eight": 28,
    "twenty-nine": 29, "thirty": 30, "sixty": 60, "ninety": 90,
}

_WORD_NUM_PATTERN = re.compile(
    r"\b(twenty.?six|twenty.?five|twenty.?four|twenty.?three|twenty.?two|"
    r"twenty.?one|twenty|nineteen|eighteen|seventeen|sixteen|fifteen|"
    r"fourteen|thirteen|twelve|eleven|ten|nine|eight|seven|six|five|"
    r"four|three|two|one|thirty|sixty|ninety|zero)\b"
    r"\s*(?:\(\d+\)\s*)?"  # optional parenthetical "(26)"
    r"(weeks?|days?|months?|years?|%|percent(?:age)?|inr|rupees?|employees?|members?)",
    re.IGNORECASE,
)


def _normalize_unit(raw: str) -> str:
    """Map a raw unit token to its canonical form."""
    return _UNIT_MAP.get(raw.lower().rstrip("."), raw.lower())


# ─── Primary extraction: spaCy NER ────────────────────────────────────────


def _extract_via_ner(text: str, nlp) -> dict | None:
    """
    Use spaCy statistical NER to find CARDINAL / QUANTITY / PERCENT / MONEY
    entities, then search the surrounding window for a unit word.
    """
    doc = nlp(text)
    target_labels = {"CARDINAL", "QUANTITY", "PERCENT", "MONEY"}

    for ent in doc.ents:
        if ent.label_ not in target_labels:
            continue

        # Try to parse numeric value from entity text
        raw_ent = ent.text.strip()
        value = None

        # Handle "%" embedded in entity text (PERCENT label)
        percent_m = re.match(r"(\d+(?:\.\d+)?)\s*%", raw_ent)
        if percent_m:
            return {
                "value": float(percent_m.group(1)),
                "unit": "percent",
                "extraction_method": "ner",
            }

        # Pure digit
        digit_m = re.match(r"^(\d+(?:\.\d+)?)$", raw_ent)
        if digit_m:
            value = float(digit_m.group(1))

        # Word number embedded in entity
        if value is None:
            # Check for parenthetical digit near entity in surrounding window text
            # e.g. "twenty six (26) weeks" — spaCy tokenizes (26) outside entity
            win_tokens = doc[max(0, ent.start - 2):min(len(doc), ent.end + 4)]
            win_text = " ".join(t.text for t in win_tokens)
            paren_m = re.search(r"\((\d+(?:\.\d+)?)\)", win_text)
            if paren_m:
                value = float(paren_m.group(1))

        if value is None:
            for word, num in _WORD_NUM.items():
                if re.fullmatch(word, raw_ent.lower().strip()):
                    value = num
                    break
            # Also try matching against the full entity text for multi-word numbers
            if value is None:
                ent_lower = raw_ent.lower()
                for word, num in sorted(_WORD_NUM.items(), key=lambda x: -len(x[0])):
                    if word in ent_lower:
                        value = num
                        break

        if value is None:
            continue

        # Search window of ±6 tokens around entity for unit word
        start_i = max(0, ent.start - 6)
        end_i = min(len(doc), ent.end + 6)
        window_tokens = [doc[i] for i in range(start_i, end_i)]
        window_text = " ".join(t.text for t in window_tokens).lower()

        unit_m = _UNIT_PATTERN.search(window_text)
        if unit_m:
            unit = _normalize_unit(unit_m.group(0))
            return {
                "value": value,
                "unit": unit,
                "extraction_method": "ner",
            }

    return None


# ─── Fallback extraction: regex ───────────────────────────────────────────


def _extract_via_regex(text: str) -> dict | None:
    """Regex fallback for digit+unit and word-number+unit patterns."""
    # Digit + unit
    m = _NUMERIC_PATTERN.search(text)
    if m:
        return {
            "value": float(m.group(1)),
            "unit": _normalize_unit(m.group(2)),
            "extraction_method": "regex",
        }

    # Spelled-out number + unit (e.g. "twenty six weeks")
    m = _WORD_NUM_PATTERN.search(text)
    if m:
        raw_word = m.group(1).lower().replace(" ", "-").replace("‑", "-")
        # Normalize variants like "twenty six" → "twenty-six"
        raw_word = re.sub(r"\s+", "-", raw_word)
        value = _WORD_NUM.get(raw_word)
        if value is not None:
            return {
                "value": float(value),
                "unit": _normalize_unit(m.group(2)),
                "extraction_method": "regex",
            }

    return None


# ─── Public API ───────────────────────────────────────────────────────────


def extract_quantity(text: str, nlp=None) -> dict | None:
    """
    Extract a number + unit from clause text using NER first, regex fallback.

    Returns:
        {"value": float, "unit": str, "extraction_method": "ner"|"regex"}
        or None if nothing found.
    """
    if nlp is not None:
        result = _extract_via_ner(text, nlp)
        if result is not None:
            return result
    return _extract_via_regex(text)


def check_quantity_conflict(
    clause_text: str,
    required_value: float,
    required_unit: str,
    comparison_type: str,
    nlp,
) -> dict:
    """
    Deterministically detect a numeric conflict between a clause and a
    legal requirement.

    Args:
        clause_text: The policy clause to check.
        required_value: The threshold number from LegalRule.required_value.
        required_unit: The canonical unit (e.g. "weeks", "days", "percent").
        comparison_type: "min" | "max" | "exact".
        nlp: A loaded spaCy model.

    Returns:
        {
            "has_quantity": bool,
            "extracted_value": float | None,
            "extracted_unit": str | None,
            "is_conflict": bool,
            "confidence": "high" | "low",
        }
    """
    result = extract_quantity(clause_text, nlp)

    if result is None:
        return {
            "has_quantity": False,
            "extracted_value": None,
            "extracted_unit": None,
            "is_conflict": False,
            "confidence": "low",
        }

    extracted_val = result["value"]
    extracted_unit = result["unit"]

    # Unit mismatch — can't compare reliably; convert months→weeks if needed
    if extracted_unit != required_unit:
        # Handle common month/week conversion for maternity leave
        if extracted_unit == "months" and required_unit == "weeks":
            extracted_val = round(extracted_val * 4.33, 1)
            extracted_unit = "weeks"
        else:
            # Unit mismatch we can't resolve — no conflict claim
            return {
                "has_quantity": True,
                "extracted_value": result["value"],
                "extracted_unit": result["unit"],
                "is_conflict": False,
                "confidence": "low",
            }

    # Comparison
    if comparison_type == "min":
        is_conflict = extracted_val < required_value
    elif comparison_type == "max":
        is_conflict = extracted_val > required_value
    elif comparison_type == "exact":
        is_conflict = abs(extracted_val - required_value) > 0.01
    else:
        is_conflict = False

    return {
        "has_quantity": True,
        "extracted_value": extracted_val,
        "extracted_unit": extracted_unit,
        "is_conflict": is_conflict,
        "confidence": "high",
    }


# ─── Self-test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import spacy

    print("Loading spaCy model...")
    nlp = spacy.load("en_core_web_sm")

    tests = [
        (
            "Female employees get 12 weeks maternity leave",
            {"value": 12.0, "unit": "weeks"},
        ),
        (
            "Leave of twenty six (26) weeks is granted",
            {"value": 26.0, "unit": "weeks"},
        ),
        (
            "Maternity leave of 3 months is provided",
            {"value": 3.0, "unit": "months"},
        ),
        (
            "PF contribution at 12% of basic wages",
            {"value": 12.0, "unit": "percent"},
        ),
    ]

    print("\n--- extract_quantity tests ---")
    for text, expected in tests:
        result = extract_quantity(text, nlp)
        status = "OK" if result and result["value"] == expected["value"] else "FAIL"
        print(f"  [{status}] {text!r}")
        print(f"         Expected: {expected}")
        print(f"         Got:      {result}")

    print("\n--- check_quantity_conflict tests ---")
    conflict_tests = [
        ("12 weeks maternity leave", 26, "weeks", "min", True),
        ("26 weeks maternity leave", 26, "weeks", "min", False),
        ("30 weeks paid leave", 26, "weeks", "min", False),
        ("3 months maternity leave", 26, "weeks", "min", True),   # 3*4.33=~13 < 26
        ("PF at 10% of basic", 12, "percent", "min", True),
        ("PF contribution at 12% of basic wages", 12, "percent", "min", False),
        ("Notice period of 15 days", 30, "days", "min", True),
    ]

    for clause, req_val, req_unit, cmp_type, expected_conflict in conflict_tests:
        result = check_quantity_conflict(clause, req_val, req_unit, cmp_type, nlp)
        ok = result["is_conflict"] == expected_conflict
        status = "OK" if ok else "FAIL"
        print(
            f"  [{status}] {clause!r} "
            f"-> conflict={result['is_conflict']} (expected={expected_conflict})"
        )
