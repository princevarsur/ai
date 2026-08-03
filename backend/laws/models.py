from django.db import models


class LegalRule(models.Model):
    """A single legal requirement from one section of one Indian law."""

    CATEGORY_CHOICES = [
        ('labour', 'Labour Law'),
        ('data_privacy', 'Data Privacy'),
        ('workplace_safety', 'Workplace Safety'),
        ('employee_benefits', 'Employee Benefits'),
        ('corporate_governance', 'Corporate Governance'),
        ('cyber_security', 'Cyber Security'),
    ]

    law_name = models.CharField(max_length=300)
    section = models.CharField(max_length=100)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    requirement_text = models.TextField(
        help_text='What the law requires in plain English.'
    )
    keywords_regex = models.TextField(
        help_text='Regex pattern for rule-based compliance check.'
    )
    COMPARISON_TYPE_CHOICES = [
        ('min', 'At Least'),
        ('max', 'At Most'),
        ('exact', 'Exactly'),
    ]

    severity_weight = models.IntegerField(
        help_text='Violation severity: 1 (minor) to 10 (critical).'
    )
    template_fix = models.TextField(
        help_text='Pre-written compliant clause text for copy-paste.'
    )
    # Numeric quantity enforcement (e.g. 26 weeks maternity, 12% PF)
    required_value = models.FloatField(
        null=True, blank=True,
        help_text='Numeric threshold (e.g. 26 for "26 weeks"). Null if not numeric.',
    )
    required_unit = models.CharField(
        max_length=20, blank=True,
        help_text='Unit for required_value (e.g. "weeks", "days", "percent"). Blank if N/A.',
    )
    comparison_type = models.CharField(
        max_length=10, choices=COMPARISON_TYPE_CHOICES, default='min',
        help_text='How to compare: at least / at most / exactly.',
    )
    embedding_cached = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'law_name', 'section']

    def __str__(self):
        return f"{self.law_name} — {self.section}"
