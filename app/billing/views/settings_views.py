import stripe
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse

from billing.models import BillingProfile
from billing.forms import BillingSettingsForm

# Configure Stripe
stripe.api_key = settings.STRIPE_API_KEY


@login_required
def billing_settings(request):
    """Handle billing settings display and updates"""
    billing_profile = request.user.billing_profile
    form = BillingSettingsForm(instance=billing_profile)
        
    # Create SetupIntent if user doesn't have a payment method
    setup_intent = None
    if not billing_profile.has_payment_method:
        # Create or get Stripe customer
        if not billing_profile.stripe_customer_id:
            customer = stripe.Customer.create(
                email=request.user.email
            )
            billing_profile.stripe_customer_id = customer.id
            billing_profile.save()
            
        # Create SetupIntent for saving card
        setup_intent = stripe.SetupIntent.create(
            customer=billing_profile.stripe_customer_id,
            payment_method_types=['card'],
            usage='off_session'  # Required for future payments
        )
    
    context = {
        'form': form,
        'billing_profile': billing_profile,
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
        'setup_intent': setup_intent
    }
    
    return render(request, 'billing/settings.html', context)
