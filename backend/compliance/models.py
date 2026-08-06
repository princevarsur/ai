from django.db import models
from django.conf import settings


class ScanReport(models.Model):
    """Result of a compliance scan on a policy document."""

    RISK_LEVEL_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    policy = models.ForeignKey(
        'policies.Policy',
        on_delete=models.CASCADE,
        related_name='scan_reports',
    )
    overall_score = models.FloatField(default=0, help_text='Compliance score: 0 to 100.')
    risk_level = models.CharField(max_length=10, choices=RISK_LEVEL_CHOICES)
    total_clauses = models.IntegerField(default=0)
    compliant_clauses = models.IntegerField(default=0)
    flagged_clauses = models.IntegerField(default=0)
    scanned_at = models.DateTimeField(auto_now_add=True)
    scan_duration_seconds = models.FloatField(default=0)
    miniml_avg_score = models.FloatField(default=0, help_text='Average MiniLM similarity.')
    inlegal_avg_score = models.FloatField(default=0, help_text='Average InLegal-SBERT similarity.')
    scanned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='scan_reports',
    )

    class Meta:
        ordering = ['-scanned_at']

    def __str__(self):
        return f"Scan: {self.policy.title} — {self.risk_level} ({self.overall_score:.1f}%)"


class FlaggedIssue(models.Model):
    """A single compliance issue found during a scan."""

    STATUS_CHOICES = [
        ('missing', 'MISSING'),
        ('conflict', 'CONFLICT'),
        ('gap', 'GAP'),
    ]

    report = models.ForeignKey(
        ScanReport,
        on_delete=models.CASCADE,
        related_name='flagged_issues',
    )
    legal_rule = models.ForeignKey(
        'laws.LegalRule',
        on_delete=models.CASCADE,
        related_name='flagged_issues',
    )
    clause_text = models.TextField(help_text='Exact clause from policy that triggered this flag.')
    clause_index = models.IntegerField(help_text='Position of clause in document (1-based).')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    severity_score = models.IntegerField(help_text='Severity: 0 to 100.')
    miniml_similarity = models.FloatField(default=0)
    inlegal_similarity = models.FloatField(default=0)
    description = models.TextField(help_text='Human-readable explanation of the issue.')
    is_resolved = models.BooleanField(default=False)
    # New signals from enhanced detection pipeline
    nli_label = models.CharField(
        max_length=20, blank=True,
        help_text='"contradiction" | "entailment" | "neutral" | "" (not run).',
    )
    quantity_conflict = models.BooleanField(
        default=False,
        help_text='True when a deterministic numeric conflict was detected.',
    )
    element_results = models.JSONField(
        default=list,
        help_text='List of sub-element evaluation results: [{"id", "text", "found", "contradicted", "method"}].',
    )
    coverage_fraction = models.FloatField(
        default=0.0,
        help_text='Weighted percentage of required sub-elements satisfied (0.0 to 1.0).',
    )
    # Reviewer feedback for continuous improvement
    FEEDBACK_CHOICES = [
        ('correct', 'Correct'),
        ('incorrect', 'Incorrect'),
        ('unsure', 'Unsure'),
    ]
    user_feedback = models.CharField(
        max_length=10, choices=FEEDBACK_CHOICES, blank=True,
        help_text='Reviewer assessment of whether this flag was accurate.',
    )
    feedback_note = models.TextField(
        blank=True,
        help_text='Optional free-text reason from the reviewer.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-severity_score']

    def __str__(self):
        return f"[{self.status.upper()}] {self.legal_rule.law_name} — Severity {self.severity_score}"


class Requirement(models.Model):
    TAXONOMY_CHOICES = [
        ('existence', 'Existence'),
        ('threshold', 'Threshold'),
        ('composite', 'Composite'),
        ('conflict', 'Conflict'),
    ]

    PENALTY_TIER_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    THRESHOLD_OP_CHOICES = [
        ('min', 'Minimum'),
        ('max', 'Maximum'),
        ('exact', 'Exact'),
    ]

    statute_citation = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Canonical citation, e.g. 'IT Act 2000 Section 43A', 'POSH Act 2013 Section 4(2)'"
    )
    title = models.CharField(
        max_length=255,
        help_text="Short title of the requirement"
    )
    description = models.TextField(
        help_text="Detailed text or statutory explanation of the rule"
    )
    taxonomy_type = models.CharField(
        max_length=20,
        choices=TAXONOMY_CHOICES,
        db_index=True,
        help_text="4-way taxonomy classification"
    )
    penalty_tier = models.CharField(
        max_length=10,
        choices=PENALTY_TIER_CHOICES,
        default='medium',
        help_text="Penalty severity tier: low, medium, or high"
    )
    mandatory_weight = models.FloatField(
        default=1.0,
        help_text="Mandatory weight used in severity formula (0.0 to 1.0+)"
    )
    threshold_value = models.FloatField(
        null=True,
        blank=True,
        help_text="Numeric threshold value for threshold/conflict rules"
    )
    threshold_unit = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Unit for threshold, e.g. 'days', 'months', 'percent', 'INR'"
    )
    threshold_op = models.CharField(
        max_length=10,
        choices=THRESHOLD_OP_CHOICES,
        blank=True,
        null=True,
        help_text="Comparison operator: min, max, exact"
    )
    domain = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Legal domain tag, e.g. 'labour', 'data_privacy', 'workplace_safety'"
    )

    class Meta:
        ordering = ['domain', 'statute_citation']
        indexes = [
            models.Index(fields=['domain', 'taxonomy_type']),
            models.Index(fields=['statute_citation']),
        ]

    def __str__(self):
        return f"[{self.domain.upper()}] {self.statute_citation} — {self.title}"


class SubElement(models.Model):
    requirement = models.ForeignKey(
        Requirement,
        on_delete=models.CASCADE,
        related_name='sub_elements'
    )
    element_key = models.CharField(
        max_length=100,
        help_text="Unique key identifier, e.g. 'presiding_officer_woman'"
    )
    element_text = models.TextField(
        help_text="Plain English text of the required sub-element"
    )
    weight = models.FloatField(
        default=1.0,
        help_text="Sub-element weight for coverage scoring"
    )
    gliner_label = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="GLiNER entity tag if applicable, e.g. 'role/designation'"
    )

    class Meta:
        ordering = ['requirement', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['requirement', 'element_key'],
                name='unique_requirement_element_key'
            )
        ]
        indexes = [
            models.Index(fields=['requirement', 'element_key']),
        ]

    def __str__(self):
        return f"{self.requirement.statute_citation} -> {self.element_key}"


class ClauseIndex(models.Model):
    document_name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="File name or document identifier"
    )
    policy = models.ForeignKey(
        'policies.Policy',
        on_delete=models.CASCADE,
        related_name='clause_indexes',
        null=True,
        blank=True,
        help_text="FK link to uploaded Policy object"
    )
    clause_id = models.CharField(
        max_length=100,
        help_text="Unique clause identifier within document, e.g. 'CSE_CL_012'"
    )
    section_title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Extracted section heading"
    )
    page_no = models.IntegerField(
        default=1,
        help_text="1-based PDF page number"
    )
    raw_text = models.TextField(
        help_text="Raw text of the clause"
    )
    char_offsets = models.JSONField(
        default=dict,
        help_text="Character offset dict: {'start': int, 'end': int}"
    )
    start_char = models.IntegerField(
        default=0,
        help_text="Start character index in document"
    )
    end_char = models.IntegerField(
        default=0,
        help_text="End character index in document"
    )
    embedding_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        db_index=True,
        help_text="SHA-256 hash of text/document version for vector caching"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['policy', 'page_no', 'id']
        indexes = [
            models.Index(fields=['policy', 'clause_id']),
            models.Index(fields=['embedding_hash']),
            models.Index(fields=['document_name', 'clause_id']),
        ]

    def __str__(self):
        return f"{self.document_name} [{self.clause_id}] p.{self.page_no}"


class AuditFinding(models.Model):
    VERDICT_CHOICES = [
        ('COMPLIANT', 'Compliant'),
        ('GAP', 'Gap'),
        ('CONFLICT', 'Conflict'),
        ('MISSING', 'Missing'),
    ]

    CONFIDENCE_TIER_CHOICES = [
        ('High', 'High'),
        ('Medium', 'Medium'),
        ('Low', 'Low'),
    ]

    policy = models.ForeignKey(
        'policies.Policy',
        on_delete=models.CASCADE,
        related_name='audit_findings',
        null=True,
        blank=True
    )
    requirement = models.ForeignKey(
        Requirement,
        on_delete=models.CASCADE,
        related_name='audit_findings'
    )
    verdict = models.CharField(
        max_length=20,
        choices=VERDICT_CHOICES,
        db_index=True,
        help_text="Audit verdict: COMPLIANT, GAP, CONFLICT, MISSING"
    )
    confidence_tier = models.CharField(
        max_length=10,
        choices=CONFIDENCE_TIER_CHOICES,
        default='High',
        help_text="Cross-model agreement confidence tier: High, Medium, Low"
    )
    severity_score = models.FloatField(
        help_text="Normalized severity score on a 0-100 scale"
    )
    coverage = models.FloatField(
        default=0.0,
        help_text="Weighted sub-element coverage ratio (0.0 to 1.0)"
    )
    nli_confidence = models.FloatField(
        default=0.0,
        help_text="Cross-Encoder NLI entailment confidence (0.0 to 1.0)"
    )
    evidence_clauses = models.JSONField(
        default=list,
        help_text="List of candidate evidence dicts. Strictly [] for MISSING."
    )
    sub_element_status = models.JSONField(
        default=list,
        help_text="List of sub-element status dicts."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-severity_score']
        indexes = [
            models.Index(fields=['policy', 'verdict']),
            models.Index(fields=['policy', 'severity_score']),
            models.Index(fields=['requirement', 'verdict']),
        ]

    def __str__(self):
        return f"[{self.verdict}] {self.requirement.statute_citation} (Severity: {self.severity_score:.1f})"

