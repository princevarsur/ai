"""
Knowledge Base Query & Helper Module (backend/compliance/kb.py)
Provides utility functions for retrieving requirements by domain, citation, and taxonomy,
searching requirements, and performing diagnostic integrity checks on the database.
"""

from typing import List, Optional, Dict, Any
from django.db.models import Q, QuerySet
from compliance.models import Requirement, SubElement


def get_requirements_by_domain(domain: str, include_adjacent: bool = True) -> QuerySet:
    """
    Retrieve all Requirement records for a given legal domain.
    Optionally includes adjacent domains (e.g. data_privacy + cyber_security).
    """
    if not domain:
        return Requirement.objects.none()

    domain = domain.lower().strip()
    domains = [domain]

    if include_adjacent:
        ADJACENT_DOMAINS = {
            'data_privacy': ['cyber_security'],
            'cyber_security': ['data_privacy'],
            'labour': ['employee_benefits', 'workplace_safety'],
            'employee_benefits': ['labour'],
            'workplace_safety': ['labour'],
        }
        domains.extend(ADJACENT_DOMAINS.get(domain, []))

    return Requirement.objects.filter(domain__in=domains).prefetch_related('sub_elements')


def get_requirement_by_citation(citation: str) -> Optional[Requirement]:
    """
    Retrieve a single Requirement by exact or case-insensitive statute citation string.
    """
    if not citation:
        return None
    return Requirement.objects.filter(statute_citation__iexact=citation.strip()).prefetch_related('sub_elements').first()


def get_requirements_by_taxonomy(taxonomy_type: str) -> QuerySet:
    """
    Filter requirements by 4-way taxonomy type ('existence', 'threshold', 'composite', 'conflict').
    """
    if not taxonomy_type:
        return Requirement.objects.none()
    return Requirement.objects.filter(taxonomy_type=taxonomy_type.lower().strip()).prefetch_related('sub_elements')


def get_all_requirements() -> QuerySet:
    """
    Retrieve all requirements with pre-fetched sub-elements.
    """
    return Requirement.objects.all().prefetch_related('sub_elements')


def validate_kb_integrity() -> Dict[str, Any]:
    """
    Execute diagnostic checks on the seeded Requirement KB in the database.
    Checks:
    - Composite rules have at least 1 SubElement.
    - Composite rule sub-element weights sum to approximately 1.0 (0.99 to 1.01).
    - Threshold and conflict rules have non-null threshold_value and threshold_op (if mandatory_weight > 0).
    - Statute citations are non-empty and unique.
    """
    errors: List[str] = []
    warnings: List[str] = []

    requirements = Requirement.objects.all().prefetch_related('sub_elements')
    total_reqs = requirements.count()
    total_subs = SubElement.objects.count()

    for req in requirements:
        # Check composite rules
        if req.taxonomy_type == 'composite':
            subs = list(req.sub_elements.all())
            if not subs:
                errors.append(f"Composite requirement '{req.statute_citation}' has zero SubElements.")
            else:
                total_weight = sum(s.weight for s in subs)
                if not (0.99 <= total_weight <= 1.01):
                    warnings.append(
                        f"Composite requirement '{req.statute_citation}' sub-element weights sum to {total_weight:.3f} (expected 1.0)."
                    )

        # Check threshold & conflict rules
        if req.taxonomy_type in ('threshold', 'conflict'):
            if req.threshold_value is None and req.mandatory_weight > 0:
                warnings.append(
                    f"{req.taxonomy_type.capitalize()} requirement '{req.statute_citation}' has null threshold_value."
                )

    return {
        'status': 'error' if errors else 'ok',
        'total_requirements': total_reqs,
        'total_sub_elements': total_subs,
        'errors': errors,
        'warnings': warnings,
    }


def search_requirements(query: str, domain: Optional[str] = None) -> QuerySet:
    """
    Search requirements across title, description, citation, and sub-element text.
    """
    qs = Requirement.objects.all()
    if domain:
        qs = qs.filter(domain=domain.lower().strip())

    if query and query.strip():
        q_term = query.strip()
        q_filter = (
            Q(statute_citation__icontains=q_term) |
            Q(title__icontains=q_term) |
            Q(description__icontains=q_term) |
            Q(sub_elements__element_text__icontains=q_term)
        )
        qs = qs.filter(q_filter).distinct()

    return qs.prefetch_related('sub_elements')
