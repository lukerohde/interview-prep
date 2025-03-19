from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import BillingProfile


@receiver(post_save, sender=User)
def create_billing_profile(sender, instance, created, **kwargs):
    """
    Create a billing profile when a new user is created
    """
    if created:
        BillingProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_billing_profile(sender, instance, **kwargs):
    """
    Save the billing profile when the user is saved
    """
    if hasattr(instance, 'billing_profile'):
        instance.billing_profile.save()
