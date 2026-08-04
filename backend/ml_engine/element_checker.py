"""
ml_engine/element_checker.py

Element-level checklist evaluation against policy clauses using hybrid NLI and quantity checking.
"""

from __future__ import annotations
from ml_engine.quantity_checker import extract_quantity, check_quantity_conflict
from ml_engine.contradiction_checker import check_entailment


def check_elements(clause_text: str, required_elements: list[dict], nlp=None, comparison_type: str = "min") -> dict:
    """
    Evaluate each structural requirement element against a candidate policy clause.
    
    For each element:
    - If the element's text implies a numeric requirement, run quantity_checker against it
    - Otherwise run contradiction_checker.check_entailment(clause_text, element['text'], clause_as_premise=True)
      - entailment -> found=True
      - contradiction -> found=False, contradicted=True
      - neutral -> found=False
      
    Returns:
        {
            "elements": [{"id", "text", "found": bool, "contradicted": bool, "method": str}, ...],
            "coverage_fraction": float,   # weighted found / total weight
            "any_contradiction": bool
        }
    """
    elements_out = []
    total_weight = 0.0
    found_weight = 0.0
    any_contradiction = False

    for elem in required_elements:
        elem_id = elem.get("id", "")
        elem_text = elem["text"]
        w = float(elem.get("weight", 1.0))
        total_weight += w

        found = False
        contradicted = False
        method = ""

        # Check if element implies a numeric requirement
        qty_req = extract_quantity(elem_text, nlp)
        if qty_req is not None:
            method = "quantity"
            res = check_quantity_conflict(
                clause_text,
                qty_req["value"],
                qty_req["unit"],
                comparison_type,
                nlp,
            )
            if res["has_quantity"]:
                if res["is_conflict"]:
                    contradicted = True
                else:
                    found = True
            else:
                found = False
        else:
            method = "nli"
            nli_res = check_entailment(clause_text, elem_text, clause_as_premise=True)
            lbl = nli_res.get("label", "neutral")
            if lbl == "entailment":
                found = True
            elif lbl == "contradiction":
                contradicted = True

        if found:
            found_weight += w
        if contradicted:
            any_contradiction = True

        elements_out.append({
            "id": elem_id,
            "text": elem_text,
            "found": found,
            "contradicted": contradicted,
            "method": method,
        })

    coverage_fraction = round(found_weight / total_weight, 4) if total_weight > 0 else 0.0

    return {
        "elements": elements_out,
        "coverage_fraction": coverage_fraction,
        "any_contradiction": any_contradiction,
    }


if __name__ == "__main__":
    import spacy
    print("Loading spaCy model for test...")
    nlp = spacy.load("en_core_web_sm")

    test_clause = (
        "The company follows the Sexual Harassment of Women at Workplace (Prevention, Prohibition and "
        "Redressal) Act, 2013, and maintains an Internal Committee to address complaints."
    )
    posh_elements = [
        {"id": "icc_exists", "text": "Company has constituted an Internal Complaints Committee", "weight": 1.0},
        {"id": "presiding_officer", "text": "ICC has a Presiding Officer who is a senior woman employee", "weight": 1.0},
        {"id": "employee_members", "text": "ICC has at least two employee members committed to the cause of women", "weight": 1.0},
        {"id": "external_member", "text": "ICC has one external member from an NGO or association", "weight": 1.0}
    ]

    print(f"\nEvaluating test clause against POSH §4 elements:\n'{test_clause}'\n")
    res = check_elements(test_clause, posh_elements, nlp=nlp)
    for el in res["elements"]:
        print(f"[{el['id']}] Found: {el['found']} | Contradicted: {el['contradicted']} | Method: {el['method']}")
    print(f"\nCoverage Fraction: {res['coverage_fraction']} | Any Contradiction: {res['any_contradiction']}")
