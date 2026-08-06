"""
Verification Test Suite for Requirement Knowledge Base Seeding & Fixtures.

Tests database seeding, command idempotency, 4-way taxonomy coverage (existence,
threshold, composite, conflict), legal domain filtering, sub-element key evaluation,
and KB query helper functions.
"""

import os
import sys

# Ensure backend directory is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'themis.settings')

import django
django.setup()

from django.test import TestCase
from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from compliance.models import Requirement, SubElement
from compliance.kb import (
    get_requirements_by_domain,
    get_requirement_by_citation,
    get_requirements_by_taxonomy,
    get_all_requirements,
    validate_kb_integrity,
    search_requirements,
)


class TestKBSeedingCommand(TestCase):
    """Tests for the seed_kb management command execution, idempotency, and --clear option."""

    def test_seed_kb_command_execution(self):
        """Verify that seed_kb executes cleanly and populates Requirements & SubElements."""
        call_command('seed_kb')
        req_count = Requirement.objects.count()
        sub_count = SubElement.objects.count()

        self.assertGreater(req_count, 0, "Requirement table should not be empty after seeding")
        self.assertGreater(sub_count, 0, "SubElement table should not be empty after seeding")
        self.assertGreaterEqual(req_count, 9, "Should seed at least 9 canonical benchmark requirements")

    def test_seed_kb_idempotency(self):
        """Verify that executing seed_kb multiple times does not produce duplicate records."""
        call_command('seed_kb')
        initial_req_count = Requirement.objects.count()
        initial_sub_count = SubElement.objects.count()

        # Run seeding a second time
        call_command('seed_kb')

        self.assertEqual(
            Requirement.objects.count(),
            initial_req_count,
            f"Requirement count changed from {initial_req_count} to {Requirement.objects.count()} on re-seed!"
        )
        self.assertEqual(
            SubElement.objects.count(),
            initial_sub_count,
            f"SubElement count changed from {initial_sub_count} to {SubElement.objects.count()} on re-seed!"
        )

    def test_seed_kb_clear_flag(self):
        """Verify that seed_kb --clear wipes existing records before re-seeding."""
        call_command('seed_kb')
        initial_req_count = Requirement.objects.count()

        call_command('seed_kb', clear=True)

        self.assertEqual(
            Requirement.objects.count(),
            initial_req_count,
            "Requirement count mismatch after seed_kb --clear"
        )


class TestTaxonomyTypeCoverage(TestCase):
    """Tests covering all 4 taxonomy types: existence, threshold, composite, and conflict."""

    def setUp(self):
        call_command('seed_kb')

    def test_existence_taxonomy_requirements(self):
        """Verify existence taxonomy requirements (e.g. IT Act Sec 66E, DPDP Act Sec 8(6))."""
        existence_reqs = Requirement.objects.filter(taxonomy_type='existence')
        self.assertTrue(existence_reqs.exists(), "No existence taxonomy requirements found!")

        for req in existence_reqs:
            self.assertIsNone(req.threshold_value, f"Existence rule '{req.statute_citation}' should have null threshold_value")
            self.assertIn(req.penalty_tier, ['low', 'medium', 'high'])
            self.assertNotEqual(req.domain, "")

        # Check canonical existence benchmark
        sec66e = Requirement.objects.filter(statute_citation__icontains="66E").first()
        self.assertIsNotNone(sec66e, "IT Act Section 66E benchmark missing!")
        self.assertEqual(sec66e.taxonomy_type, 'existence')
        self.assertEqual(sec66e.penalty_tier, 'high')

    def test_threshold_taxonomy_requirements(self):
        """Verify threshold taxonomy requirements (e.g. Code on Wages Sec 17(1)(d), Leave caps)."""
        threshold_reqs = Requirement.objects.filter(taxonomy_type='threshold')
        self.assertTrue(threshold_reqs.exists(), "No threshold taxonomy requirements found!")

        for req in threshold_reqs:
            self.assertIsNotNone(req.threshold_value, f"Threshold rule '{req.statute_citation}' missing threshold_value")
            self.assertIsNotNone(req.threshold_unit)
            self.assertGreater(len(req.threshold_unit), 0)
            self.assertIn(req.threshold_op, ['min', 'max', 'exact'])

        # Check canonical wage payment threshold benchmark (7 days)
        wages_req = Requirement.objects.filter(statute_citation__icontains="17(1)(d)").first()
        self.assertIsNotNone(wages_req, "Code on Wages 17(1)(d) missing!")
        self.assertEqual(wages_req.taxonomy_type, 'threshold')
        self.assertEqual(wages_req.threshold_value, 7.0)
        self.assertEqual(wages_req.threshold_op, 'max')
        self.assertEqual(wages_req.threshold_unit, 'day')

        # Check F&F settlement (2 working days)
        fnf_req = Requirement.objects.filter(statute_citation__icontains="17(2)").first()
        self.assertIsNotNone(fnf_req, "Code on Wages 17(2) missing!")
        self.assertEqual(fnf_req.threshold_value, 2.0)
        self.assertEqual(fnf_req.threshold_op, 'max')

        # Check Leave caps (MH 45 days, KA 30 days)
        mh_req = Requirement.objects.filter(statute_citation__icontains="Maharashtra").first()
        self.assertIsNotNone(mh_req, "MH Shops Act missing!")
        self.assertEqual(mh_req.threshold_value, 45.0)

        ka_req = Requirement.objects.filter(statute_citation__icontains="Karnataka").first()
        self.assertIsNotNone(ka_req, "KA Shops Act missing!")
        self.assertEqual(ka_req.threshold_value, 30.0)

    def test_composite_taxonomy_requirements(self):
        """Verify composite taxonomy requirements and sub-element decomposition (e.g. IT Act Sec 43A, POSH Sec 4(2))."""
        composite_reqs = Requirement.objects.filter(taxonomy_type='composite')
        self.assertTrue(composite_reqs.exists(), "No composite taxonomy requirements found!")

        for req in composite_reqs:
            subs = req.sub_elements.all()
            self.assertGreaterEqual(subs.count(), 1, f"Composite rule '{req.statute_citation}' must have sub-elements!")
            total_weight = sum(s.weight for s in subs)
            self.assertAlmostEqual(total_weight, 1.0, places=3, msg=f"Sub-element weights for '{req.statute_citation}' sum to {total_weight}, expected 1.0")

        # Check IT Act Sec 43A sub-elements
        sec43a = Requirement.objects.filter(statute_citation__icontains="43A").first()
        self.assertIsNotNone(sec43a, "IT Act Section 43A benchmark missing!")
        sec43a_keys = set(sec43a.sub_elements.values_list('element_key', flat=True))
        expected_43a_keys = {'security_policy_doc', 'control_measures', 'prescribed_standard', 'periodic_independent_vapt'}
        self.assertTrue(expected_43a_keys.issubset(sec43a_keys), f"Missing IT Act 43A sub-element keys. Got: {sec43a_keys}")

        # Check POSH Act Sec 4(2) sub-elements
        posh42 = Requirement.objects.filter(statute_citation__icontains="4(2)").first()
        self.assertIsNotNone(posh42, "POSH Act Sec 4(2) benchmark missing!")
        posh_keys = set(posh42.sub_elements.values_list('element_key', flat=True))
        expected_posh_keys = {'presiding_officer_woman', 'employee_members_min2', 'external_member', 'gender_parity_50pct'}
        self.assertTrue(expected_posh_keys.issubset(posh_keys), f"Missing POSH Act 4(2) keys. Got: {posh_keys}")

    def test_conflict_taxonomy_requirements(self):
        """Verify conflict taxonomy requirements (e.g. POSH Complaint Window, Deduction Ceiling)."""
        conflict_reqs = Requirement.objects.filter(taxonomy_type='conflict')
        self.assertTrue(conflict_reqs.exists(), "No conflict taxonomy requirements found!")

        # Check POSH Sec 9(1) complaint window benchmark (3 months min)
        posh_window = Requirement.objects.filter(statute_citation__icontains="9(1)").first()
        self.assertIsNotNone(posh_window, "POSH Section 9(1) missing!")
        self.assertEqual(posh_window.taxonomy_type, 'conflict')
        self.assertEqual(posh_window.threshold_value, 3.0)
        self.assertIn(posh_window.threshold_unit, ['month', 'months'])
        self.assertEqual(posh_window.threshold_op, 'min')

        # Check Wage Deduction Cap (50% max)
        deduction_cap = Requirement.objects.filter(statute_citation__icontains="18(3)").first()
        self.assertIsNotNone(deduction_cap, "Code on Wages 18(3) missing!")
        self.assertEqual(deduction_cap.threshold_value, 50.0)
        self.assertEqual(deduction_cap.threshold_op, 'max')
        self.assertEqual(deduction_cap.threshold_unit, 'percent')


class TestDomainFiltering(TestCase):
    """Tests for domain-scoped retrieval and domain filtering helper logic."""

    def setUp(self):
        call_command('seed_kb')

    def test_domain_filtering_valid_domains(self):
        """Verify that requirements can be filtered strictly by domain."""
        valid_domains = ["workplace_safety", "data_privacy", "labour", "cyber_security", "corporate_governance", "employee_benefits"]
        for domain_name in valid_domains:
            domain_reqs = get_requirements_by_domain(domain_name, include_adjacent=False)
            self.assertTrue(domain_reqs.exists(), f"No requirements found for domain '{domain_name}'")
            for req in domain_reqs:
                self.assertEqual(req.domain, domain_name)

    def test_domain_isolation(self):
        """Verify that domain filtering isolates unrelated legal requirements."""
        posh_reqs = set(Requirement.objects.filter(domain='workplace_safety').values_list('id', flat=True))
        privacy_reqs = set(Requirement.objects.filter(domain='data_privacy').values_list('id', flat=True))

        intersection = posh_reqs.intersection(privacy_reqs)
        self.assertEqual(len(intersection), 0, f"Domain overlap detected between workplace_safety and data_privacy: {intersection}")

    def test_invalid_domain_filter(self):
        """Verify that filtering by a non-existent domain returns an empty queryset."""
        res = get_requirements_by_domain('invalid_domain_xyz', include_adjacent=False)
        self.assertFalse(res.exists())


class TestKeyBasedEvaluationAndSubElements(TestCase):
    """Tests for sub-element lookup by key, helper functions, and coverage ratio calculation."""

    def setUp(self):
        call_command('seed_kb')

    def test_query_sub_elements_by_key(self):
        """Verify querying sub-elements by element_key under a parent requirement."""
        req = get_requirement_by_citation("IT Act 2000 Section 43A")
        self.assertIsNotNone(req)

        sub = req.sub_elements.get(element_key='periodic_independent_vapt')
        self.assertEqual(sub.element_key, 'periodic_independent_vapt')
        self.assertEqual(sub.weight, 0.25)
        self.assertGreater(len(sub.element_text), 0)

    def test_composite_coverage_ratio_evaluation(self):
        """Verify coverage ratio arithmetic for composite requirements."""
        req = get_requirement_by_citation("IT Act 2000 Section 43A")
        all_subs = list(req.sub_elements.all())
        total_weight = sum(s.weight for s in all_subs)

        # Case 1: All elements satisfied (100% coverage)
        satisfied_keys_full = {s.element_key for s in all_subs}
        satisfied_weight_full = sum(s.weight for s in all_subs if s.element_key in satisfied_keys_full)
        coverage_full = satisfied_weight_full / total_weight
        self.assertEqual(coverage_full, 1.0)

        # Case 2: Partial satisfaction (2 of 4 keys satisfied)
        satisfied_keys_partial = {'security_policy_doc', 'control_measures'}
        satisfied_weight_partial = sum(s.weight for s in all_subs if s.element_key in satisfied_keys_partial)
        coverage_partial = satisfied_weight_partial / total_weight
        self.assertEqual(coverage_partial, 0.50)

        # Case 3: Zero elements satisfied
        coverage_zero = 0.0 / total_weight
        self.assertEqual(coverage_zero, 0.0)

    def test_threshold_comparison_evaluations(self):
        """Verify numeric evaluation logic for threshold requirements."""
        # Max threshold test (e.g. Code on Wages 7 days)
        wages_req = get_requirement_by_citation("Code on Wages 2019 Section 17(1)(d)")
        self.assertIsNotNone(wages_req)
        self.assertEqual(wages_req.threshold_op, 'max')
        max_limit = wages_req.threshold_value  # 7.0

        val_compliant = 5.0
        val_conflict = 10.0

        self.assertLessEqual(val_compliant, max_limit, "Value 5 days should satisfy max threshold of 7 days")
        self.assertGreater(val_conflict, max_limit, "Value 10 days should violate max threshold of 7 days")

        # Min threshold test (e.g. POSH 3 months complaint window)
        posh_req = get_requirement_by_citation("POSH Act 2013 Section 9(1)")
        self.assertIsNotNone(posh_req)
        self.assertEqual(posh_req.threshold_op, 'min')
        min_limit = posh_req.threshold_value  # 3.0

        val_compliant_posh = 3.0
        val_conflict_posh = 1.0  # 1 month policy window triggers conflict

        self.assertGreaterEqual(val_compliant_posh, min_limit, "Value 3 months should satisfy min threshold of 3 months")
        self.assertLess(val_conflict_posh, min_limit, "Value 1 month should violate min threshold of 3 months")


class TestDatabaseIntegrityAndKBHelpers(TestCase):
    """Tests enforcing schema constraints, unique indices, and KB helper function integrity."""

    def setUp(self):
        call_command('seed_kb')

    def test_sub_element_unique_constraint(self):
        """Verify that duplicate (requirement, element_key) pairs raise IntegrityError."""
        sub = SubElement.objects.first()
        self.assertIsNotNone(sub, "At least one SubElement should exist in seeded database")
        req = sub.requirement

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SubElement.objects.create(
                    requirement=req,
                    element_key=sub.element_key,
                    element_text="Duplicate key attempt",
                    weight=0.1
                )

    def test_requirement_choice_validations(self):
        """Verify full_clean raises ValidationError on invalid choices."""
        invalid_req = Requirement(
            statute_citation="Invalid Act Sec 1",
            title="Test",
            description="Test",
            taxonomy_type="invalid_type",
            penalty_tier="super_high",
            domain="labour"
        )
        with self.assertRaises(ValidationError) as exc_info:
            invalid_req.full_clean()

        errors = exc_info.exception.message_dict
        self.assertIn('taxonomy_type', errors)
        self.assertIn('penalty_tier', errors)

    def test_validate_kb_integrity_helper(self):
        """Verify validate_kb_integrity returns status 'ok' for seeded database."""
        result = validate_kb_integrity()
        self.assertEqual(result['status'], 'ok')
        self.assertGreaterEqual(result['total_requirements'], 9)
        self.assertEqual(len(result['errors']), 0)

    def test_search_requirements_helper(self):
        """Verify search_requirements matches keyword across title, description, and citation."""
        results_vapt = search_requirements("VAPT")
        self.assertTrue(results_vapt.exists())
        self.assertEqual(results_vapt.first().statute_citation, "IT Act 2000 Section 43A")

        results_posh = search_requirements("POSH", domain="workplace_safety")
        self.assertTrue(results_posh.exists())
        for req in results_posh:
            self.assertEqual(req.domain, "workplace_safety")


if __name__ == '__main__':
    import unittest
    unittest.main()
