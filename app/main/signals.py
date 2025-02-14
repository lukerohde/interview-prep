from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from .models import Application

@receiver(post_save, sender=User)
def create_user_application(sender, instance, created, **kwargs):
    if created:
        Application.objects.create(
            name=f"Welcome {instance.username}! Create your first job application",
            status='draft',
            resume='Paste your resume here...',
            job_description='Paste the job description here...',
            owner=instance
        )
        
@receiver(user_logged_in, sender=User)
def something_useful_on_login(sender, request, user, **kwargs):
    pass