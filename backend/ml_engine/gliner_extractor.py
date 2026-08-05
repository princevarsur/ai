"""
ml_engine/gliner_extractor.py

Zero-Shot Structured Information Extraction using GLiNER (urchade/gliner_small-v2)
and downstream deterministic rule evaluator for unambiguous statutory adherence.
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_gliner_model = None

def get_gliner_model():
    """Lazy loader for GLiNER model to save memory and startup time."""
    global _gliner_model
    if _gliner_model is None:
        try:
            print("Loading GLiNER zero-shot model (urchade/gliner_small-v2)...")
            from gliner import GLiNER
            _gliner_model = GLiNER.from_pretrained("urchade/gliner_small-v2")
            print("GLiNER loaded successfully.")
        except Exception as exc:
            logger.error("Failed to load GLiNER model: %s", exc)
            _gliner_model = "FAILED"
    return _gliner_model if _gliner_model != "FAILED" else None


def extract_structured_entities(clause_text: str, threshold: float = 0.25) -> dict:
    """
    Convert unformatted policy prose into rigid structural data trees using GLiNER.
    
    Returns:
        {
            "referenced_statutes": list[str],
            "legal_subjects": list[str],
            "numeric_thresholds": list[str],
            "action_modalities": list[str],
            "raw_entities": list[dict],
        }
    """
    model = get_gliner_model()
    tree = {
        "referenced_statutes": [],
        "legal_subjects": [],
        "numeric_thresholds": [],
        "action_modalities": [],
        "raw_entities": [],
    }

    # Deterministic check for action modalities / affirmative compliance language
    affirmative_modalities = [
        "follows", "adheres", "adherence", "maintains", "constituted",
        "constitute", "comply", "complies", "compliance", "in accordance with",
        "as per", "governed by", "under applicable law", "pursuant to", "mandated by"
    ]
    clause_low = clause_text.lower()
    for mod in affirmative_modalities:
        if mod in clause_low and mod not in tree["action_modalities"]:
            tree["action_modalities"].append(mod)

    if model is None:
        return tree

    labels = ["law", "statute", "Act", "regulation", "committee", "board", "organization", "duration", "time period", "number", "percentage"]
    try:
        entities = model.predict_entities(clause_text, labels, threshold=threshold)
        tree["raw_entities"] = entities
        for ent in entities:
            lbl = ent.get("label", "")
            txt = ent.get("text", "")
            if lbl in ("law", "statute", "Act", "regulation") and txt not in tree["referenced_statutes"]:
                tree["referenced_statutes"].append(txt)
            elif lbl in ("committee", "board", "organization") and txt not in tree["legal_subjects"]:
                tree["legal_subjects"].append(txt)
            elif lbl in ("duration", "time period", "number", "percentage") and txt not in tree["numeric_thresholds"]:
                tree["numeric_thresholds"].append(txt)
    except Exception as exc:
        logger.error("Error running GLiNER inference: %s", exc)

    return tree


def _statute_matches_law(statute_text: str, law_name: str) -> bool:
    """Verify if extracted referenced statute aligns with target legal statute."""
    s_low = statute_text.lower()
    l_low = law_name.lower()
    
    if "posh" in l_low or "sexual harassment" in l_low:
        if any(w in s_low for w in ["posh", "sexual harassment", "harassment"]):
            return True
    if "maternity" in l_low:
        if any(w in s_low for w in ["maternity", "creche", "pregnancy", "benefit"]):
            return True
    if "dpdp" in l_low or "data protection" in l_low or "privacy" in l_low:
        if any(w in s_low for w in ["dpdp", "data protection", "privacy", "gdpr", "information technology"]):
            return True
    if "wages" in l_low or "payment of wages" in l_low:
        if any(w in s_low for w in ["wages", "salary", "bonus", "remuneration"]):
            return True
    if "labour" in l_low or "industrial relations" in l_low:
        if any(w in s_low for w in ["labour", "industrial", "standing orders", "dispute"]):
            return True
    if "contract" in l_low:
        if any(w in s_low for w in ["contract", "agreement", "restraint"]):
            return True

    # Token overlap check excluding legal boilerplates
    statute_tokens = set(re.findall(r"\w+", s_low))
    law_tokens = set(re.findall(r"\w+", l_low))
    ignore = {"act", "code", "law", "rules", "of", "the", "and", "in", "at", "for", "on", "2013", "2019", "2020", "2023", "1961", "1947", "1872", "1956", "section"}
    return len((statute_tokens - ignore) & (law_tokens - ignore)) > 0


def check_gliner_compliance_override(clause_text: str, rule, nlp=None) -> tuple[bool, str, dict]:
    """
    Deterministic rule engine evaluating GLiNER structured output.
    When [Referenced_Statute] matches target law and affirmative modality exists
    with no conflicting numeric threshold, evaluate as COMPLIANT with zero ambiguity.
    
    Returns:
        (is_compliant, catch_signal, structured_tree)
    """
    tree = extract_structured_entities(clause_text)
    
    # Must have affirmative action modality
    if not tree["action_modalities"]:
        return False, "", tree
        
    # Check if any extracted statute matches the rule's governing law
    matching_statute = None
    for stat in tree["referenced_statutes"]:
        if _statute_matches_law(stat, rule.law_name):
            matching_statute = stat
            break
            
    # Also check if clause explicitly names the rule law name directly in case GLiNER entity text was cut off
    if not matching_statute:
        if _statute_matches_law(clause_text, rule.law_name) and any(mod in clause_text.lower() for mod in ["follows the", "according to", "in accordance with", "as per the"]):
            matching_statute = rule.law_name
            
    if not matching_statute:
        return False, "", tree

    # Verify no conflicting numeric thresholds are present
    if rule.required_value is not None:
        from ml_engine.quantity_checker import check_quantity_conflict
        qty_res = check_quantity_conflict(
            clause_text, rule.required_value, rule.required_unit, rule.comparison_type, nlp
        )
        if qty_res["has_quantity"] and qty_res["is_conflict"]:
            # Numeric conflict overrides statutory reference!
            return False, "", tree

    signal = f"GLiNER zero-shot structural adherence ([Statute: {matching_statute}] + [Modality: {tree['action_modalities'][0]}])"
    return True, signal, tree
