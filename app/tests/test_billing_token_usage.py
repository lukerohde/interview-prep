import pytest
from django.urls import reverse
from django.test import Client
from decimal import Decimal
import json

from .factories import UserFactory
from billing.models import BillingProfile, BillingSettings

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
def billing_profile(user):
    """Create a billing profile with initial credits"""
    profile = user.billing_profile
    profile.add_credits(Decimal('100.00'))
    return profile

def test_add_token_usage_success(authenticated_client, billing_profile):
    """Test successful token usage tracking with CSRF-exempt endpoint"""
    url = reverse('billing:add_token_usage')
    
    # Prepare token usage data
    usage_data = {
        'model_name': 'gpt-4o-mini-realtime-preview',
        'input_tokens': 1000,
        'input_tokens_cached': 500,
        'output_tokens': 800
    }
    
    # Get initial balance
    initial_balance = billing_profile.balance
    
    # Make the request
    response = authenticated_client.post(
        url,
        data=json.dumps(usage_data),
        content_type='application/json'
    )
    
    # Check response
    assert response.status_code == 200
    response_data = response.json()
    assert response_data['status'] == 'success'
    assert 'cost' in response_data
    assert 'balance' in response_data
    
    # Verify database update
    billing_profile.refresh_from_db()
    cost = Decimal(str(response_data['cost']))
    assert billing_profile.total_usage == cost
    assert billing_profile.balance == initial_balance - cost

def test_add_token_usage_unauthenticated(client):
    """Test token usage tracking requires authentication even though it's CSRF-exempt"""
    url = reverse('billing:add_token_usage')
    
    # Prepare token usage data
    usage_data = {
        'model_name': 'gpt-4o-mini-realtime-preview',
        'input_tokens': 1000,
        'input_tokens_cached': 500,
        'output_tokens': 800
    }
    
    # Make the request without authentication
    response = client.post(
        url,
        data=json.dumps(usage_data),
        content_type='application/json'
    )
    
    # Check unauthorized response
    assert response.status_code == 302  # Redirects to login
    assert '/login/' in response['Location']

def test_add_token_usage_invalid_data(authenticated_client, billing_profile):
    """Test token usage tracking with invalid data"""
    url = reverse('billing:add_token_usage')
    
    # Test cases with invalid data
    test_cases = [
        # Missing model name
        {
            'input_tokens': 1000,
            'input_tokens_cached': 500,
            'output_tokens': 800
        },
        # Invalid token counts
        {
            'model_name': 'gpt-4o-mini-realtime-preview',
            'input_tokens': 'invalid',
            'input_tokens_cached': 500,
            'output_tokens': 800
        },
        # Negative token counts
        {
            'model_name': 'gpt-4o-mini-realtime-preview',
            'input_tokens': -1000,
            'input_tokens_cached': 500,
            'output_tokens': 800
        }
    ]
    
    initial_usage = billing_profile.total_usage
    
    for test_data in test_cases:
        response = authenticated_client.post(
            url,
            data=json.dumps(test_data),
            content_type='application/json'
        )
        
        # Check error response
        if response.status_code == 200:
            import ipdb; ipdb.set_trace()
        assert response.status_code == 400
        response_data = response.json()
        assert response_data['status'] == 'error'
        
        # Verify no changes to billing profile
        billing_profile.refresh_from_db()
        assert billing_profile.total_usage == initial_usage
