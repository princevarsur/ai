from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Custom user model for THEMIS."""

    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('compliance_officer', 'Compliance Officer'),
        ('viewer', 'Viewer'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    company_name = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.username
