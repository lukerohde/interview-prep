import json
import stripe
from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST

from billing.models import BillingProfile, Transaction

# Configure Stripe
stripe.api_key = settings.STRIPE_API_KEY


class RechargeCreditsView(LoginRequiredMixin, View):
    """
    Handle credit recharging
    """
    template_name = 'billing/recharge.html'
    
    def get(self, request):
        """Handle GET request - display the recharge form with amount"""
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
        
        return render(request, self.template_name, context)



@method_decorator(login_required, name='dispatch')
class UpdateTransactionStatusView(View):
    """Handle transaction status updates from the client"""
    
    def post(self, request):
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


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):
    """Handle Stripe webhooks for payment intents"""
    
    STATUS_MAPPING = {
        'payment_intent.succeeded': 'succeeded',
        'payment_intent.payment_failed': 'failed',
        'payment_intent.canceled': 'cancelled'
    }
    
    def get_transaction(self, intent_id):
        """Get transaction and billing profile for a payment intent"""
        try:
            return Transaction.objects.select_related('billing_profile').get(
                stripe_payment_intent_id=intent_id
            )
        except Transaction.DoesNotExist:
            return None
    
    def post(self, request):
        import ipdb; ipdb.set_trace()
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
        new_status = self.STATUS_MAPPING.get(event.type)
        if not new_status:
            # Return 200 for events we don't handle
            return JsonResponse({'status': 'success', 'message': 'Event type not handled'})
            
        # Get intent
        intent = event.data.object
        transaction = self.get_transaction(intent.id)
        
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
