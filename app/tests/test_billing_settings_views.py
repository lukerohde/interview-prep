import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.urls import reverse
from django.contrib.auth.models import User
from .factories import UserFactory
from billing.models import BillingProfile

pytestmark = pytest.mark.django_db

@pytest.fixture
def user():
    return UserFactory()

@pytest.fixture
def authenticated_client(client, user):
    client.force_login(user)
    return client

def test_billing_settings_login_required(client):
    """Test that billing settings requires login."""
    url = reverse('billing:billing_settings')
    response = client.get(url)
    assert response.status_code == 302  # Redirects to login
    assert '/login/' in response.url

@patch('stripe.Customer.create')
@patch('stripe.SetupIntent.create')
def test_billing_settings_no_payment_method(mock_setup_intent, mock_customer, authenticated_client, user):
    """Test billing settings when user has no payment method."""
    # Set up mocks
    mock_customer.return_value = MagicMock(id='cus_test_123')
    mock_setup_intent.return_value = MagicMock(
        id='seti_test_123',
        client_secret='secret_test_123'
    )
    
    # Get billing settings page
    url = reverse('billing:billing_settings')
    response = authenticated_client.get(url)
    
    # Check response
    assert response.status_code == 200
    assert 'form' in response.context
    assert 'billing_profile' in response.context
    assert 'stripe_publishable_key' in response.context
    assert 'setup_intent' in response.context
    
    # Verify SetupIntent was created
    mock_setup_intent.assert_called_once_with(
        customer='cus_test_123',
        payment_method_types=['card'],
        usage='off_session'
    )
    
    # Verify customer was created
    mock_customer.assert_called_once_with(
        email=user.email
    )
    
    # Verify customer ID was saved
    billing_profile = BillingProfile.objects.get(user=user)
    assert billing_profile.stripe_customer_id == 'cus_test_123'

@patch('stripe.SetupIntent.create')
def test_billing_settings_existing_payment_method(mock_setup_intent, authenticated_client, user):
    """Test billing settings when user has payment method."""
    # Set up billing profile with payment method
    billing_profile = BillingProfile.objects.get(user=user)
    billing_profile.stripe_payment_method_id = 'pm_test_123'
    billing_profile.stripe_customer_id = 'cus_test_123'
    billing_profile.save()
    
    # Get billing settings page
    url = reverse('billing:billing_settings')
    response = authenticated_client.get(url)
    
    # Check response
    assert response.status_code == 200
    assert 'form' in response.context
    assert 'billing_profile' in response.context
    assert 'stripe_publishable_key' in response.context
    assert not response.context['setup_intent'] is None # we setup a new intent even if we have an existing intent
    
    # Verify new SetupIntent was created
    mock_setup_intent.assert_called_once()
