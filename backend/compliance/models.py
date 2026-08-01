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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-severity_score']

    def __str__(self):
        return f"[{self.status.upper()}] {self.legal_rule.law_name} — Severity {self.severity_score}"
