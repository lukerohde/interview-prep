import pytest
from decimal import Decimal
from django.urls import reverse
from django.test import Client
from django.contrib.auth.models import User
from billing.models import BillingProfile, Transaction


@pytest.fixture
def admin_client(admin_user):
    """Create a client logged in as admin."""
    client = Client()
    client.force_login(admin_user)
    return client


@pytest.fixture
def test_users():
    """Create test users with billing profiles."""
    users = []
    for i in range(3):
        user = User.objects.create_user(
            username=f'testuser{i}',
            email=f'test{i}@example.com',
            password='password123'
        )
        users.append(user)
    return users


def test_credit_adjustment_view_get(admin_client, test_users):
    """Test the credit adjustment form view."""
    # Get the changelist URL
    url = reverse('admin:billing_billingprofile_changelist')
    
    # Select two users for adjustment
    data = {
        'action': 'make_credit_adjustment',
        '_selected_action': [
            str(test_users[0].billing_profile.pk),
            str(test_users[1].billing_profile.pk)
        ]
    }
    
    # Submit the action
    response = admin_client.post(url, data)
    assert response.status_code == 200
    
    # Check that the form shows both users
    content = response.content.decode()
    assert test_users[0].username in content
    assert test_users[1].username in content
    assert test_users[2].username not in content


def test_credit_adjustment_view_post(admin_client, test_users):
    """Test applying credit adjustments."""
    # Get initial credit balances
    profile1 = test_users[0].billing_profile
    profile2 = test_users[1].billing_profile
    initial_balance1 = profile1.balance
    initial_balance2 = profile2.balance
    
    # Get the changelist URL
    url = reverse('admin:billing_billingprofile_changelist')
    
    # Submit adjustment
    data = {
        'action': 'make_credit_adjustment',
        '_selected_action': [str(profile1.pk), str(profile2.pk)],
        'amount': '10.00',
        'description': 'Test adjustment',
        'apply': 'Apply'
    }
    
    # Submit the form - should redirect to changelist
    response = admin_client.post(url, data)
    assert response.status_code == 302
    assert response['Location'] == '/admin/billing/billingprofile/'
    
    # Verify credits were added
    profile1.refresh_from_db()
    profile2.refresh_from_db()
    assert profile1.balance == initial_balance1 + Decimal('10.00')
    assert profile2.balance == initial_balance2 + Decimal('10.00')
    
    # Verify transactions were created
    for profile in [profile1, profile2]:
        transaction = Transaction.objects.filter(
            billing_profile=profile,
            amount=Decimal('10.00'),
            transaction_type='adjustment',
            description='Test adjustment'
        ).first()
        assert transaction is not None
        assert transaction.status == 'succeeded'


def test_credit_adjustment_validation(admin_client, test_users):
    """Test credit adjustment validation."""
    url = reverse('admin:billing_billingprofile_changelist')
    profile = test_users[0].billing_profile
    
    # Test missing description
    data = {
        'action': 'make_credit_adjustment',
        '_selected_action': [str(profile.pk)],
        'amount': '10.00',
        'description': '',
        'apply': 'Apply'
    }
    # First post should show intermediate page
    response = admin_client.post(url, data, follow=True)
    assert response.status_code == 200
    content = response.content.decode()
    assert 'Description is required' in content
    
    # Test invalid amount
    data['description'] = 'Test'
    data['amount'] = 'invalid'
    response = admin_client.post(url, data)
    assert 'Invalid amount specified' in response.content.decode()
