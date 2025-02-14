from django.db import models
from django.contrib.auth.models import User
from .utils import do_something_handy
from uuid import uuid4

class Application(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('in_progress', 'In Progress'),
        ('rejected', 'Rejected'),
        ('accepted', 'Accepted'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255, help_text='Name of the position or company')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    resume = models.TextField(help_text='Your resume or CV content')
    job_description = models.TextField(help_text='Full job description')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.status}"

    class Meta:
        ordering = ['-updated_at']

