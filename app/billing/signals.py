from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from decimal import Decimal
from .models import BillingProfile, BillingSettings


@receiver(post_save, sender=User)
def create_billing_profile(sender, instance, created, **kwargs):
    """
    Create a billing profile when a new user is created and add default signup credits
    """
    if created:
        billing_profile = BillingProfile.objects.create(user=instance)
        
        # Get credits from BillingSettings model (admin configurable)
        billing_settings = BillingSettings.load()
        default_credits = billing_settings.signup_credits
        
        # Add credits if the amount is greater than zero
        if default_credits > Decimal('0'):
            billing_profile.add_credits(
                default_credits, 
                transaction_type='promotion'
            )


@receiver(post_save, sender=User)
def save_billing_profile(sender, instance, **kwargs):
    """
    Save the billing profile when the user is saved
    """
    if hasattr(instance, 'billing_profile'):
        instance.billing_profile.save()
