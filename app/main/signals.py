from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from .models import Thing

@receiver(post_save, sender=User)
def create_user_thing(sender, instance, created, **kwargs):
    if created:
        thing = Thing.objects.create(
            name=f"{instance.username}'s Thing",
            owner=instance
        )
        
@receiver(user_logged_in, sender=User)
def something_useful_on_login(sender, request, user, **kwargs):
    pass