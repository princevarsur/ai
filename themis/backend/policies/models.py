from django.db import models
from django.conf import settings


class Policy(models.Model):
    """An uploaded company policy document."""

    CATEGORY_CHOICES = [
        ('labour', 'Labour Law'),
        ('data_privacy', 'Data Privacy'),
        ('workplace_safety', 'Workplace Safety'),
        ('employee_benefits', 'Employee Benefits'),
        ('corporate_governance', 'Corporate Governance'),
        ('cyber_security', 'Cyber Security'),
        ('general', 'General'),
    ]

    title = models.CharField(max_length=300)
    file = models.FileField(upload_to='policies/')
    file_type = models.CharField(max_length=10, help_text='Auto-detected: pdf, docx, txt.')
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    extracted_text = models.TextField(blank=True)
    clause_count = models.IntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='policies',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'policies'

    def __str__(self):
        return self.title
