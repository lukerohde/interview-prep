import stripe
from decimal import Decimal
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods

from billing.models import Transaction

# Configure Stripe
stripe.api_key = settings.STRIPE_API_KEY


# Map webhook event types to transaction statuses
WEBHOOK_STATUS_MAPPING = {
    'payment_intent.succeeded': 'succeeded',
    'payment_intent.payment_failed': 'failed',
    'payment_intent.canceled': 'cancelled'
}


def get_transaction(intent_id):
    """Get transaction by payment intent ID"""
    try:
        return Transaction.objects.select_related('billing_profile').get(
            stripe_payment_intent_id=intent_id
        )
    except Transaction.DoesNotExist:
        return None


@login_required
def recharge_credits(request):
    """Handle credit recharging"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    billing_profile = request.user.billing_profile
    
    # Get amount from query params or use default
    amount = Decimal(request.GET.get('amount', '5.00'))
    
    # Create or get Stripe customer
    if not billing_profile.stripe_customer_id:
        customer = stripe.Customer.create(
            email=request.user.email
        )
        billing_profile.stripe_customer_id = customer.id
        billing_profile.save()
    
    # Create payment intent with card-only payments
    intent = stripe.PaymentIntent.create(
        amount=int(amount * 100),  # Convert to cents
        currency='usd',
        customer=billing_profile.stripe_customer_id,
        payment_method_types=['card'],  # Only allow card payments
        automatic_payment_methods=None  # Disable automatic payment methods
    )
    
    # Create transaction record using billing profile
    transaction = billing_profile.add_credit_intent(amount, intent.id)
    
    context = {
        'billing_profile': billing_profile,
        'recharge_amount': str(amount),
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
        'client_secret': intent.client_secret,
        'intent': intent,  # Pass full intent to template for ID access
    }
    
    return render(request, 'billing/recharge.html', context)


@login_required
@require_POST
def update_transaction_status(request):
    """Handle transaction status updates from the client"""
    intent_id = request.POST.get('intent_id')
    action = request.POST.get('action')
    
    if not intent_id or not action:
        return JsonResponse({'error': 'Missing intent_id or action'}, status=400)
        
    billing_profile = request.user.billing_profile
        
    if action == 'process':
        # Update to processing before submitting to Stripe
        if billing_profile.update_credit_intent(intent_id, 'processing'):
            return JsonResponse({'status': 'success', 'message': 'Updated to processing'})
        return JsonResponse({'error': 'Transaction not found'}, status=404)
            
    elif action == 'cancel':
        try:
            # Cancel the payment intent with Stripe
            stripe.PaymentIntent.cancel(intent_id)
            # Delete the transaction record
            if billing_profile.delete_credit_intent(intent_id):
                return JsonResponse({'status': 'success', 'message': 'Transaction cancelled and deleted'})
            return JsonResponse({'error': 'Transaction not found or already completed'}, status=404)
            
        except stripe.error.StripeError as e:
            return JsonResponse({'error': str(e)}, status=400)
            
    return JsonResponse({'error': 'Invalid action'}, status=400)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Handle Stripe webhook events"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError:
        return JsonResponse({'error': 'Invalid signature'}, status=400)

    # Only process payment intent events we care about
    new_status = WEBHOOK_STATUS_MAPPING.get(event.type)
    if not new_status:
        # Return 200 for events we don't handle
        return JsonResponse({'status': 'success', 'message': 'Event type not handled'})
        
    # Get intent
    intent = event.data.object
    transaction = get_transaction(intent.id)
    
    if not transaction:
        # Return 200 even if transaction not found - it might be a test webhook or duplicate
        return JsonResponse({
            'status': 'success',
            'message': f'Transaction not found for intent {intent.id}'
        })
        
    # For cancellations, delete the transaction
    if new_status == 'cancelled':
        transaction.billing_profile.delete_credit_intent(intent.id)
        return JsonResponse({'status': 'success', 'message': 'Transaction deleted'})
        
    # For other statuses, update the transaction
    transaction.billing_profile.update_credit_intent(intent.id, new_status)
    return JsonResponse({'status': 'success', 'message': f'Updated transaction to {new_status}'})
