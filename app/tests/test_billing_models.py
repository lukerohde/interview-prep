import pytest
from decimal import Decimal
from django.test import Client
from .factories import UserFactory
from billing.models import BillingProfile, Transaction, Session

pytestmark = pytest.mark.django_db

@pytest.fixture
def user():
    return UserFactory()

def test_billing_profile_add_credits(user):
    """Test adding credits to a billing profile."""
    # Get the billing profile created by the signal
    billing_profile = BillingProfile.objects.get(user=user)
    initial_credits = billing_profile.total_credits
    
    # Count initial transactions
    initial_transaction_count = Transaction.objects.filter(
        billing_profile=billing_profile,
        transaction_type='recharge'
    ).count()
    
    # Add credits
    amount = Decimal('50.00')
    billing_profile.add_credits(amount)
    
    # Verify credits were added
    billing_profile.refresh_from_db()
    assert billing_profile.total_credits == initial_credits + amount
    
    # Verify a new transaction was created
    new_transaction_count = Transaction.objects.filter(
        billing_profile=billing_profile,
        transaction_type='recharge'
    ).count()
    assert new_transaction_count == initial_transaction_count + 1
    
    # Verify the transaction details
    latest_transaction = Transaction.objects.filter(
        billing_profile=billing_profile,
        transaction_type='recharge'
    ).latest('created_at')
    assert latest_transaction.amount == amount

def test_billing_profile_add_credits_with_custom_transaction_type(user):
    """Test adding credits with a custom transaction type."""
    # Get the billing profile created by the signal
    billing_profile = BillingProfile.objects.get(user=user)
    initial_credits = billing_profile.total_credits
    
    # Count initial transactions of the custom type
    initial_transaction_count = Transaction.objects.filter(
        billing_profile=billing_profile,
        transaction_type='promotion'
    ).count()
    
    # Add credits with a promotion transaction type
    amount = Decimal('25.00')
    billing_profile.add_credits(amount, transaction_type='promotion')
    
    # Verify credits were added
    billing_profile.refresh_from_db()
    assert billing_profile.total_credits == initial_credits + amount
    
    # Verify a new transaction was created with the correct type
    new_transaction_count = Transaction.objects.filter(
        billing_profile=billing_profile,
        transaction_type='promotion'
    ).count()
    assert new_transaction_count == initial_transaction_count + 1
    
    # Verify the transaction details
    latest_transaction = Transaction.objects.filter(
        billing_profile=billing_profile,
        transaction_type='promotion'
    ).latest('created_at')
    assert latest_transaction.amount == amount

def test_billing_profile_use_credits(user):
    """Test using credits from a billing profile."""
    # Get the billing profile created by the signal
    billing_profile = BillingProfile.objects.get(user=user)
    
    # Add some initial credits
    billing_profile.add_credits(Decimal('100.00'))
    initial_credits = billing_profile.total_credits
    initial_usage = billing_profile.total_usage
    
    # Count initial sessions
    initial_session_count = Session.objects.filter(
        billing_profile=billing_profile
    ).count()
    
    # Use credits
    amount = Decimal('30.00')
    billing_profile.use_credits(amount)
    
    # Verify usage was updated
    billing_profile.refresh_from_db()
    assert billing_profile.total_usage == initial_usage + amount
    assert billing_profile.total_credits == initial_credits  # Credits total doesn't change
    assert billing_profile.balance == initial_credits - (initial_usage + amount)
    
    # Verify a new session was created
    new_session_count = Session.objects.filter(
        billing_profile=billing_profile
    ).count()
    assert new_session_count == initial_session_count + 1
    
    # Verify the session details
    latest_session = Session.objects.filter(
        billing_profile=billing_profile
    ).latest('created_at')
    assert latest_session.cost == amount
    # Note: In the current implementation, tokens are not set when creating a session through use_credits

def test_billing_profile_use_credits_with_existing_session(user):
    """Test using credits with an existing session."""
    # Get the billing profile created by the signal
    billing_profile = BillingProfile.objects.get(user=user)
    
    # Add some initial credits
    billing_profile.add_credits(Decimal('100.00'))
    
    # Create a session
    session = Session.objects.create(
        billing_profile=billing_profile,
        total_tokens=500,
        cost=Decimal('5.00')
    )
    
    # Count initial sessions
    initial_session_count = Session.objects.filter(
        billing_profile=billing_profile
    ).count()
    
    # Use credits with the existing session
    additional_amount = Decimal('15.00')
    billing_profile.use_credits(additional_amount, session=session)
    
    # Verify no new session was created
    new_session_count = Session.objects.filter(
        billing_profile=billing_profile
    ).count()
    assert new_session_count == initial_session_count
    
    # Verify the session was updated correctly
    session.refresh_from_db()
    assert session.cost == Decimal('20.00')  # 5.00 + 15.00
    # Note: In the current implementation, tokens are not updated when using an existing session

def test_billing_profile_balance_calculation(user):
    """Test that the balance property correctly calculates credits minus usage."""
    # Get the billing profile created by the signal
    billing_profile = BillingProfile.objects.get(user=user)
    
    # Record the initial state
    initial_credits = billing_profile.total_credits
    initial_usage = billing_profile.total_usage
    initial_balance = billing_profile.balance
    
    # Add some credits and use some
    billing_profile.add_credits(Decimal('200.00'))
    billing_profile.use_credits(Decimal('75.00'))
    
    # Verify the balance calculation
    billing_profile.refresh_from_db()
    expected_balance = (initial_credits + Decimal('200.00')) - (initial_usage + Decimal('75.00'))
    assert billing_profile.balance == expected_balance


def test_session_add_usage_with_tokens(user):
    """Test adding usage with tokens to a session."""
    # Get the billing profile created by the signal
    billing_profile = BillingProfile.objects.get(user=user)
    
    # Create a session
    session = Session.objects.create(
        billing_profile=billing_profile,
        total_tokens=0,
        cost=Decimal('0.00')
    )
    
    # Add usage with tokens
    cost = Decimal('10.00')
    tokens = 1000
    session.add_usage(cost, tokens=tokens)
    
    # Verify the session was updated correctly
    session.refresh_from_db()
    assert session.cost == cost
    assert session.total_tokens == tokens
    
    # Add more usage
    additional_cost = Decimal('5.00')
    additional_tokens = 500
    session.add_usage(additional_cost, tokens=additional_tokens)
    
    # Verify the session was updated correctly
    session.refresh_from_db()
    assert session.cost == cost + additional_cost
    assert session.total_tokens == tokens + additional_tokens
