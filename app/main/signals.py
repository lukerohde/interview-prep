from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from .models import Deck

@receiver(post_save, sender=User)
def create_user_deck(sender, instance, created, **kwargs):
    pass
    # if created:
    #     Deck.objects.create(
    #         name=f"Welcome {instance.username}! Create your first deck",
    #         deck_type=Deck.DeckType.JOB_APPLICATION,
    #         status='draft',
    #         owner=instance
    #         tutor= 
    #     )
        
@receiver(user_logged_in, sender=User)
def something_useful_on_login(sender, request, user, **kwargs):
    pass