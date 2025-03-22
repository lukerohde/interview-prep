import pytest
import stripe
from django.urls import reverse
from django.test import Client
from decimal import Decimal
from unittest.mock import patch, MagicMock
from .factories import UserFactory
from billing.models import BillingProfile, Transaction

pytestmark = pytest.mark.django_db

@pytest.fixture
def client():
    return Client()

@pytest.fixture
def user():
    return UserFactory()

@pytest.fixture
def authenticated_client(client, user):
    client.force_login(user)
    return client

@pytest.fixture
def mock_stripe():
    with patch('billing.views.credit_views.stripe') as mock_stripe:
        # Setup mock payment intent
        mock_intent = MagicMock()
        mock_intent.id = 'pi_123'
        mock_intent.client_secret = 'secret_123'
        mock_stripe.PaymentIntent.create.return_value = mock_intent
        
        # Setup mock customer
        mock_customer = MagicMock()
        mock_customer.id = 'cus_123'
        mock_stripe.Customer.create.return_value = mock_customer
        
        yield mock_stripe

def test_recharge_credits_view(authenticated_client, user, mock_stripe):
    """Test the recharge credits view with default amount."""
    response = authenticated_client.get(reverse('billing:recharge_credits'))
    
    assert response.status_code == 200
    assert 'billing/recharge.html' in [t.name for t in response.templates]

def test_recharge_credits_view_with_amount_from_dashboard(authenticated_client, user, mock_stripe):
    """Test that the amount selected on the dashboard appears correctly on the recharge page."""
    # First visit dashboard and submit the recharge form
    dashboard_response = authenticated_client.get(reverse('billing:billing_dashboard'))
    assert dashboard_response.status_code == 200
    
    # Get the form from dashboard and submit with custom amount
    recharge_amount = '75.00'
    recharge_response = authenticated_client.get(
        reverse('billing:recharge_credits'),
        {'amount': recharge_amount}
    )
    
    # Verify response
    assert recharge_response.status_code == 200
    assert 'billing/recharge.html' in [t.name for t in recharge_response.templates]
    
    # Check amount appears in context
    assert recharge_response.context['recharge_amount'] == recharge_amount
    assert recharge_response.context['client_secret'] == 'secret_123'
    assert recharge_response.context['stripe_publishable_key']

    # Check amount appears in template
    content = recharge_response.content.decode()
    assert f'${recharge_amount}' in content
    
    # Verify Stripe setup with correct amount in cents
    mock_stripe.PaymentIntent.create.assert_called_once_with(
        amount=7500,  # $75.00 in cents
        currency='usd',
        customer='cus_123',
        payment_method_types=['card'],
        automatic_payment_methods=None
    )
    
    # Check Stripe customer was created
    mock_stripe.Customer.create.assert_called_once_with(
        email=user.email
    )


def test_recharge_credits_view_custom_amount(authenticated_client, user, mock_stripe):
    """Test the recharge credits view with custom amount."""
    response = authenticated_client.get(
        reverse('billing:recharge_credits') + '?amount=10.00'
    )
    
    assert response.status_code == 200
    
    # Check payment intent was created with correct amount
    mock_stripe.PaymentIntent.create.assert_called_once_with(
        amount=1000,  # $10.00 in cents
        currency='usd',
        customer='cus_123',
        payment_method_types=['card'],
        automatic_payment_methods=None
    )
    
    assert response.context['recharge_amount'] == '10.00'

def test_update_transaction_status_processing(authenticated_client, user):
    """Test updating transaction status to processing."""
    # Create a pending transaction
    billing_profile = BillingProfile.objects.get(user=user)
    transaction = billing_profile.add_credit_intent(
        Decimal('50.00'), 
        'pi_123'
    )
    
    response = authenticated_client.post(
        reverse('billing:update_transaction_status'),
        {'intent_id': 'pi_123', 'action': 'process'}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'success'
    
    # Verify transaction status was updated
    transaction.refresh_from_db()
    assert transaction.status == 'processing'

def test_update_transaction_status_cancel(authenticated_client, user, mock_stripe):
    """Test cancelling a transaction."""
    # Create a pending transaction
    billing_profile = BillingProfile.objects.get(user=user)
    transaction = billing_profile.add_credit_intent(
        Decimal('50.00'), 
        'pi_123'
    )
    
    response = authenticated_client.post(
        reverse('billing:update_transaction_status'),
        {'intent_id': 'pi_123', 'action': 'cancel'}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'success'
    
    # Verify Stripe was called
    mock_stripe.PaymentIntent.cancel.assert_called_once_with('pi_123')
    
    # Verify transaction was deleted
    assert not Transaction.objects.filter(
        stripe_payment_intent_id='pi_123'
    ).exists()

@pytest.fixture
def mock_stripe_webhook():
    with patch('billing.views.credit_views.stripe.Webhook') as mock_webhook:
        # Setup mock event
        mock_event = MagicMock()
        mock_webhook.construct_event.return_value = mock_event
        yield mock_webhook, mock_event

@pytest.mark.parametrize('event_type,expected_status', [
    ('payment_intent.succeeded', 'succeeded'),
    ('payment_intent.payment_failed', 'failed'),
    ('payment_intent.canceled', 'cancelled'),
])
def test_stripe_webhook(client, user, mock_stripe_webhook, event_type, expected_status):
    """Test Stripe webhook handling for different event types."""
    mock_webhook, mock_event = mock_stripe_webhook
    
    # Create a transaction to update
    billing_profile = BillingProfile.objects.get(user=user)
    transaction = billing_profile.add_credit_intent(
        Decimal('50.00'), 
        'pi_123'
    )
    initial_credits = billing_profile.total_credits
    
    # Setup mock event
    mock_event.type = event_type
    mock_event.data.object.id = 'pi_123'
    mock_event.data.object.amount = 5000
    
    # Send webhook request
    response = client.post(
        reverse('billing:stripe_webhook'),
        data='{}',  # Raw payload doesn't matter as we mock construct_event
        content_type='application/json',
        HTTP_STRIPE_SIGNATURE='mock_signature'
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'success'
    
    # Verify webhook was constructed
    mock_webhook.construct_event.assert_called_once()
    
    # Refresh transaction and billing profile
    if expected_status != 'cancelled':  # Transaction is deleted for cancelled status
        transaction.refresh_from_db()
        assert transaction.status == expected_status
    else:
        assert not Transaction.objects.filter(stripe_payment_intent_id='pi_123').exists()
    
    billing_profile.refresh_from_db()
    
    # Verify credits were added only for succeeded events
    if expected_status == 'succeeded':
        assert billing_profile.total_credits == initial_credits + Decimal('50.00')
    else:
        assert billing_profile.total_credits == initial_credits

def test_stripe_webhook_invalid_signature(client):
    """Test Stripe webhook with invalid signature."""
    with patch('billing.views.credit_views.stripe.Webhook') as mock_webhook:
        mock_webhook.construct_event.side_effect = stripe.error.SignatureVerificationError('', '')
        
        response = client.post(
            reverse('billing:stripe_webhook'),
            data='{}',
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='invalid_signature'
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data['error'] == 'Invalid signature'

def test_stripe_webhook_invalid_payload(client):
    """Test Stripe webhook with invalid payload."""
    with patch('billing.views.credit_views.stripe.Webhook') as mock_webhook:
        mock_webhook.construct_event.side_effect = ValueError('Invalid payload')
        
        response = client.post(
            reverse('billing:stripe_webhook'),
            data='invalid_json',
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='mock_signature'
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data['error'] == 'Invalid payload'

def test_stripe_webhook_unhandled_event(client, user, mock_stripe_webhook):
    """Test Stripe webhook with unhandled event type."""
    mock_webhook, mock_event = mock_stripe_webhook
    mock_event.type = 'unhandled.event'
    
    response = client.post(
        reverse('billing:stripe_webhook'),
        data='{}',
        content_type='application/json',
        HTTP_STRIPE_SIGNATURE='mock_signature'
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'success'
    assert 'not handled' in data['message'].lower()
