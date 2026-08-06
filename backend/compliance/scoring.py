"""
backend/compliance/scoring.py

Milestone 4: Sub-Element Coverage & Explainable Severity Scoring Engine

Features:
- Sub-element coverage ratio computation:
  coverage = sum(satisfied_weight) / sum(all_weight)
  Mapped to verdicts:
  * >= 0.85 -> COMPLIANT
  * 0.40 - 0.84 -> GAP (with explicit sub-element breakdown)
  * < 0.40 -> MISSING
- Transparent 4-parameter severity formula:
  severity = 0.4 * mandatory_weight + 0.3 * (1 - coverage) + 0.2 * penalty_weight + 0.1 * nli_conf
  Scaled to 0 - 100.
- Confidence tier assignment (High, Medium, Low).
"""

import logging
from typing import List, Dict, Any, Tuple, Optional

from compliance.models import Requirement, SubElement, ClauseIndex
from compliance.retrieval import retrieve_for_sub_element
from compliance.nli_gate import evaluate_nli_candidates

logger = logging.getLogger(__name__)

PENALTY_TIER_WEIGHTS = {
    'high': 1.0,
    'medium': 0.6,
    'low': 0.3,
}


def compute_penalty_weight(penalty_tier: str) -> float:
    """Map penalty tier string ('high', 'medium', 'low') to float weight (0.0 to 1.0)."""
    if not penalty_tier:
        return 0.6
    tier_clean = str(penalty_tier).lower().strip()
    return PENALTY_TIER_WEIGHTS.get(tier_clean, 0.6)


def compute_sub_element_coverage(sub_element_results: List[Dict[str, Any]]) -> float:
    """
    Compute weighted sub-element coverage ratio:
    coverage = sum(satisfied sub-element weights) / sum(all sub-element weights)
    """
    if not sub_element_results:
        return 0.0

    total_weight = sum(float(item.get('weight', 1.0)) for item in sub_element_results)
    if total_weight <= 0:
        return 0.0

    satisfied_weight = sum(
        float(item.get('weight', 1.0))
        for item in sub_element_results
        if item.get('satisfied', False)
    )

    coverage = satisfied_weight / total_weight
    return float(np_clip(coverage, 0.0, 1.0))


def np_clip(val: float, min_v: float, max_v: float) -> float:
    """Clip val to [min_v, max_v]."""
    return max(min_v, min(val, max_v))


def determine_confidence_tier(nli_conf: float, model_agreement: float = 1.0) -> str:
    """
    Expose confidence tier ('High', 'Medium', 'Low') based on cross-model agreement
    and NLI confidence.
    """
    effective_conf = nli_conf * model_agreement

    if effective_conf >= 0.75:
        return 'High'
    elif effective_conf >= 0.45:
        return 'Medium'
    else:
        return 'Low'


def compute_severity_score(
    mandatory_weight: float,
    coverage: float,
    penalty_tier: str,
    nli_conf: float
) -> Dict[str, Any]:
    """
    Compute transparent 4-parameter severity formula:
    severity_raw = 0.4 * mandatory_weight + 0.3 * (1 - coverage) + 0.2 * penalty_weight + 0.1 * nli_conf
    severity_score = round(severity_raw * 100.0, 2)

    Returns dict with keys:
    {
        'severity_score': float (0.0 to 100.0),
        'severity_breakdown': {
            'mandatory_weight': float,
            'coverage_loss': float,
            'penalty_weight': float,
            'nli_conf': float
        }
    }
    """
    m_weight = float(mandatory_weight) if mandatory_weight is not None else 1.0
    cov = float(np_clip(coverage, 0.0, 1.0))
    cov_loss = float(1.0 - cov)
    p_weight = compute_penalty_weight(penalty_tier)
    conf = float(np_clip(nli_conf, 0.0, 1.0))

    severity_raw = (0.4 * m_weight) + (0.3 * cov_loss) + (0.2 * p_weight) + (0.1 * conf)
    severity_score = round(severity_raw * 100.0, 2)

    breakdown = {
        'mandatory_weight': round(m_weight, 4),
        'coverage_loss': round(cov_loss, 4),
        'penalty_weight': round(p_weight, 4),
        'nli_conf': round(conf, 4),
    }

    return {
        'severity_score': severity_score,
        'severity_breakdown': breakdown,
    }


def evaluate_composite_sub_elements(
    requirement: Requirement,
    clauses: List[ClauseIndex]
) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Evaluate each SubElement under a composite Requirement against candidate clauses.
    Returns (coverage_ratio, list of sub-element status dicts).
    """
    sub_elements = list(requirement.sub_elements.all())
    if not sub_elements:
        return 0.0, []

    status_list = []
    for sub in sub_elements:
        # Retrieve candidate clauses for this sub-element
        cands = retrieve_for_sub_element(sub, clauses, top_k=8, include_lexical=True)

        satisfied = False
        best_clause_id = None
        best_score = 0.0

        if cands:
            # Run NLI evaluation on sub-element query candidates
            hypothesis = f"The policy enforces {sub.element_text}"
            eval_cands = evaluate_nli_candidates(cands, hypothesis, requirement=requirement)

            valid_cands = [c for c in eval_cands if c.get('is_topically_valid', True)]
            if valid_cands:
                top_cand = max(valid_cands, key=lambda c: c.get('entailment_prob', 0.0))
                best_score = float(top_cand.get('entailment_prob', 0.0))

                # Consider sub-element satisfied if entailment score >= 0.65 or retrieval score >= 0.65
                if best_score >= 0.65 or top_cand.get('max_score', 0.0) >= 0.65:
                    satisfied = True
                    best_clause_id = top_cand.get('clause_id')

        status_list.append({
            'element_key': sub.element_key,
            'element_text': sub.element_text,
            'weight': sub.weight,
            'satisfied': satisfied,
            'evidence_clause_id': best_clause_id,
            'confidence_score': round(best_score, 4),
        })

    coverage = compute_sub_element_coverage(status_list)
    return coverage, status_list


def score_finding(
    requirement: Requirement,
    verdict: str,
    coverage: float,
    nli_conf: float,
    evidence: List[Dict[str, Any]],
    sub_element_status: List[Dict[str, Any]],
    model_agreement: float = 1.0
) -> Dict[str, Any]:
    """
    Assemble the complete explainable audit finding scoring payload.

    Parameters:
    - requirement: Requirement ORM object
    - verdict: str ('COMPLIANT' | 'GAP' | 'CONFLICT' | 'MISSING')
    - coverage: float (0.0 to 1.0)
    - nli_conf: float (0.0 to 1.0)
    - evidence: List[Dict[str, Any]] evidence clause dicts
    - sub_element_status: List[Dict[str, Any]] sub-element status breakdown
    - model_agreement: float agreement score between models (default 1.0)

    Returns:
    - Dict[str, Any] with keys matching THEMIS API output contract:
      {
          'requirement_id': str,
          'verdict': str,
          'confidence_tier': str,
          'severity': float,
          'coverage': float,
          'severity_breakdown': dict,
          'sub_element_status': list,
          'evidence': list,
      }
    """
    # Enforce strict evidence guard if MISSING
    if verdict == 'MISSING':
        evidence_payload = []
    else:
        evidence_payload = evidence

    sev_dict = compute_severity_score(
        mandatory_weight=requirement.mandatory_weight,
        coverage=coverage,
        penalty_tier=requirement.penalty_tier,
        nli_conf=nli_conf
    )

    conf_tier = determine_confidence_tier(nli_conf, model_agreement=model_agreement)

    return {
        'requirement_id': requirement.statute_citation,
        'verdict': verdict,
        'confidence_tier': conf_tier,
        'severity': sev_dict['severity_score'],
        'coverage': round(float(coverage), 4),
        'nli_confidence': round(float(nli_conf), 4),
        'severity_breakdown': sev_dict['severity_breakdown'],
        'sub_element_status': sub_element_status,
        'evidence': evidence_payload,
    }
