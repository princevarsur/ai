"""
backend/compliance/nli_gate.py

Milestone 4: NLI Classification Gate & Strict Evidence Guard

Features:
- NLI Cross-Encoder classification using cross-encoder/nli-MiniLM2-L6-H768 via ModelRegistry.
- Classifies candidate clause pairs as COMPLIANT, CONFLICT, GAP, or MISSING.
- Enforces strict non-hallucination evidence guard: returns evidence: [] for any MISSING finding.
- Topical filtering: Rejects photocopier/scanner/printing clauses from IT Act Section 66E
  bodily privacy findings.
"""

import re
import logging
import numpy as np
from typing import List, Dict, Any, Optional

from compliance.models import Requirement, SubElement
from compliance.model_registry import ModelRegistry

logger = logging.getLogger(__name__)

# Keywords for topical rejection under IT Act 66E (Bodily Privacy / Surveillance)
BODILY_PRIVACY_EXCLUDED_TERMS = {
    'photocopier', 'photocopy', 'scanner', 'scanning', 'printer', 'printing',
    'duplicating machine', 'multi-function printer', 'mfp', 'xerox', 'copier',
    'paper copy', 'hardcopy', 'document scanning'
}


def is_topically_valid_clause(requirement: Requirement, clause_text: str) -> bool:
    """
    Apply domain/topical filtering rules to reject false positive citations.
    Specifically rejects photocopier/scanner/printing equipment clauses from
    IT Act Section 66E bodily privacy findings.
    """
    if not requirement or not clause_text:
        return True

    citation = requirement.statute_citation or ''
    title = requirement.title or ''
    desc = requirement.description or ''

    is_sec_66e = (
        '66e' in citation.lower() or
        'bodily privacy' in title.lower() or
        'bodily privacy' in desc.lower() or
        'surveillance' in title.lower()
    )

    if is_sec_66e:
        clause_lower = clause_text.lower()
        # Check if clause mentions excluded printing/scanning/photocopier equipment
        for term in BODILY_PRIVACY_EXCLUDED_TERMS:
            if term in clause_lower:
                logger.info(
                    "Topical filter rejected clause mentioning '%s' for IT Act Sec 66E bodily privacy.",
                    term
                )
                return False

    return True


def softmax(x: np.ndarray) -> np.ndarray:
    """Compute softmax probabilities for a 1D or 2D array of logits."""
    e_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
    return e_x / np.sum(e_x, axis=-1, keepdims=True)


def predict_nli_pair(clause_text: str, hypothesis_text: str) -> Dict[str, Any]:
    """
    Predict NLI label probabilities for a (clause_text, hypothesis_text) pair
    using CrossEncoder from ModelRegistry.

    Returns dict with keys:
    {
        'label': 'entailment' | 'contradiction' | 'neutral',
        'entailment_prob': float,
        'contradiction_prob': float,
        'neutral_prob': float,
        'confidence': float
    }
    """
    cross_encoder = ModelRegistry.get_nli_cross_encoder()

    try:
        # CrossEncoder.predict returns raw logits array
        logits = cross_encoder.predict([(clause_text, hypothesis_text)])
        if isinstance(logits, list):
            logits = np.array(logits)

        logits = logits.flatten()
        probs = softmax(logits)

        # Label index mapping: 0=contradiction, 1=entailment, 2=neutral
        # Verify if model config has custom id2label mapping
        id2label = getattr(getattr(cross_encoder, 'model', None), 'config', None)
        id2label = getattr(id2label, 'id2label', {0: 'contradiction', 1: 'entailment', 2: 'neutral'})

        # Map probs to label names
        label_probs = {}
        for idx, prob in enumerate(probs):
            lbl_name = str(id2label.get(idx, idx)).lower()
            if 'contradict' in lbl_name:
                label_probs['contradiction'] = float(prob)
            elif 'entail' in lbl_name:
                label_probs['entailment'] = float(prob)
            else:
                label_probs['neutral'] = float(prob)

        # Ensure all three keys are populated
        contradiction_prob = label_probs.get('contradiction', float(probs[0]))
        entailment_prob = label_probs.get('entailment', float(probs[1]))
        neutral_prob = label_probs.get('neutral', float(probs[2]) if len(probs) > 2 else 0.0)

        # Determine dominant label
        max_idx = int(np.argmax(probs))
        dom_label_raw = str(id2label.get(max_idx, max_idx)).lower()
        if 'entail' in dom_label_raw:
            dominant_label = 'entailment'
            conf = entailment_prob
        elif 'contradict' in dom_label_raw:
            dominant_label = 'contradiction'
            conf = contradiction_prob
        else:
            dominant_label = 'neutral'
            conf = neutral_prob

        return {
            'label': dominant_label,
            'entailment_prob': entailment_prob,
            'contradiction_prob': contradiction_prob,
            'neutral_prob': neutral_prob,
            'confidence': conf
        }
    except Exception as exc:
        logger.warning("NLI CrossEncoder prediction failed: %s", exc)
        return {
            'label': 'neutral',
            'entailment_prob': 0.0,
            'contradiction_prob': 0.0,
            'neutral_prob': 1.0,
            'confidence': 0.0
        }


def evaluate_nli_candidates(
    candidates: List[Dict[str, Any]],
    hypothesis_text: str,
    requirement: Optional[Requirement] = None
) -> List[Dict[str, Any]]:
    """
    Evaluate NLI Cross-Encoder probabilities and apply topical filtering
    for a list of retrieved candidate clauses.

    Adds NLI scores and topical validity metadata to each candidate dict.
    """
    if not candidates:
        return []

    evaluated = []
    for cand in candidates:
        c_text = cand.get('raw_text', '')

        # Check topical validity
        valid_topic = is_topically_valid_clause(requirement, c_text)

        if not valid_topic:
            cand_copy = dict(cand)
            cand_copy.update({
                'is_topically_valid': False,
                'nli_label': 'neutral',
                'entailment_prob': 0.0,
                'contradiction_prob': 0.0,
                'neutral_prob': 1.0,
                'nli_confidence': 0.0,
                'nli_score': 0.0
            })
            evaluated.append(cand_copy)
            continue

        nli_res = predict_nli_pair(c_text, hypothesis_text)

        cand_copy = dict(cand)
        cand_copy.update({
            'is_topically_valid': True,
            'nli_label': nli_res['label'],
            'entailment_prob': nli_res['entailment_prob'],
            'contradiction_prob': nli_res['contradiction_prob'],
            'neutral_prob': nli_res['neutral_prob'],
            'nli_confidence': nli_res['confidence'],
            'nli_score': nli_res['entailment_prob'],
        })
        evaluated.append(cand_copy)

    return evaluated


def classify_requirement_gate(
    requirement: Requirement,
    candidates: List[Dict[str, Any]],
    numeric_eval_result: Optional[Dict[str, Any]] = None,
    entailment_threshold: float = 0.75,
    relevance_floor: float = 0.35
) -> Dict[str, Any]:
    """
    Classify a requirement finding into COMPLIANT, CONFLICT, GAP, or MISSING
    and enforce strict non-hallucination evidence guard (evidence: [] for MISSING).

    Parameters:
    - requirement: Requirement object
    - candidates: List[Dict[str, Any]] candidate clauses evaluated by NLI
    - numeric_eval_result: Optional numeric rule evaluation dict from gliner_engine
    - entailment_threshold: float threshold for COMPLIANT classification (default 0.75)
    - relevance_floor: float threshold below which finding is classified MISSING (default 0.35)

    Returns:
    - Dict[str, Any] with keys:
      {
          'verdict': 'COMPLIANT' | 'CONFLICT' | 'GAP' | 'MISSING',
          'nli_confidence': float,
          'evidence': List[Dict[str, Any]],  # strictly [] if MISSING
          'evaluated_candidates': List[Dict[str, Any]],
      }
    """
    # 1. Check numeric conflict rule first
    if numeric_eval_result and numeric_eval_result.get('is_conflict'):
        # Automatic CONFLICT
        # Collect evidence clauses if available
        valid_cands = [c for c in candidates if c.get('is_topically_valid', True)]
        conflict_cands = [c for c in valid_cands if c.get('numeric_conflict')]
        if not conflict_cands:
            conflict_cands = valid_cands[:1]
            
        evidence_list = [
            {
                "clause_id": c["clause_id"],
                "section_title": c["section_title"],
                "page_no": c["page_no"],
                "raw_text": c["raw_text"],
                "nli_label": c.get("nli_label", "contradiction"),
                "nli_score": c.get("nli_score", 0.0),
            }
            for c in conflict_cands
        ]
        return {
            'verdict': 'CONFLICT',
            'nli_confidence': 0.90,
            'evidence': evidence_list,
            'evaluated_candidates': candidates,
        }

    # Filter candidates by topical validity AND enforce a strict semantic floor 
    # (requires MiniLM >= 0.12 to prevent InLegal-SBERT clustering artifacts 
    # where all labor laws get grouped together causing NLI hallucination)
    valid_candidates = [
        c for c in candidates 
        if c.get('is_topically_valid', True) 
        and (c.get('max_score', 0.0) >= relevance_floor)
        and (c.get('minilm_score', 0.0) >= 0.30)
    ]

    # If no topically valid candidates exist -> strictly MISSING with evidence: []
    if not valid_candidates:
        return {
            'verdict': 'MISSING',
            'nli_confidence': 0.0,
            'evidence': [],
            'evaluated_candidates': candidates,
        }

    # Calculate max NLI scores across valid candidates
    max_entailment = max(c.get('entailment_prob', 0.0) for c in valid_candidates)
    max_contradiction = max(c.get('contradiction_prob', 0.0) for c in valid_candidates)
    max_max_score = max(c.get('max_score', 0.0) for c in valid_candidates)

    best_candidate = max(valid_candidates, key=lambda c: c.get('entailment_prob', 0.0))
    best_entailment = best_candidate.get('entailment_prob', 0.0)

    # 2. Check relevance floor across entire index
    if max_entailment < relevance_floor and max_max_score < relevance_floor:
        # STRICT NON-HALLUCINATION GUARD: evidence must be []
        return {
            'verdict': 'MISSING',
            'nli_confidence': float(max_entailment),
            'evidence': [],
            'evaluated_candidates': candidates,
        }

    # 3. Classify verdict based on entailment and contradiction thresholds
    if max_contradiction >= 0.65 and requirement.taxonomy_type != 'threshold':
        verdict = 'CONFLICT'
        nli_conf = float(max_contradiction)
    elif max_entailment >= entailment_threshold:
        verdict = 'COMPLIANT'
        nli_conf = float(max_entailment)
    elif max_entailment >= 0.40:
        verdict = 'GAP'
        nli_conf = float(max_entailment)
    else:
        verdict = 'MISSING'
        nli_conf = float(max_entailment)

    # 4. Strict Evidence Guard: If verdict is MISSING, evidence MUST be []
    if verdict == 'MISSING':
        evidence_list = []
    else:
        # Include top valid candidates as evidence
        if verdict == 'CONFLICT':
            sort_key = lambda c: (c.get('contradiction_prob', 0.0), c.get('max_score', 0.0))
        else:
            sort_key = lambda c: (c.get('entailment_prob', 0.0), c.get('max_score', 0.0))
            
        top_evidence_cands = sorted(valid_candidates, key=sort_key, reverse=True)[:1]

        evidence_list = [
            {
                "clause_id": c["clause_id"],
                "section_title": c["section_title"],
                "page_no": c["page_no"],
                "raw_text": c["raw_text"],
                "nli_label": c.get("nli_label", "neutral"),
                "nli_score": c.get("nli_score", 0.0),
            }
            for c in top_evidence_cands
        ]

    return {
        'verdict': verdict,
        'nli_confidence': nli_conf,
        'evidence': evidence_list,
        'evaluated_candidates': candidates,
    }
