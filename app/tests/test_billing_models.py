import pytest
from decimal import Decimal
from django.test import Client, override_settings
from django.contrib.auth.models import User
from .factories import UserFactory
from billing.models import BillingProfile, Transaction, Session, BillingSettings

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
    
    # Use credits with tokens
    amount = Decimal('30.00')
    tokens = 3000
    billing_profile.use_credits(amount, tokens=tokens)
    
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
    assert latest_session.total_tokens == tokens  # Verify tokens were recorded

def test_billing_profile_use_credits_with_existing_session(user):
    """Test using credits with an existing session."""
    # Get the billing profile created by the signal
    billing_profile = BillingProfile.objects.get(user=user)
    
    # Add some initial credits
    billing_profile.add_credits(Decimal('100.00'))
    
    # Create a session
    initial_tokens = 500
    session = Session.objects.create(
        billing_profile=billing_profile,
        total_tokens=initial_tokens,
        cost=Decimal('5.00')
    )
    
    # Count initial sessions
    initial_session_count = Session.objects.filter(
        billing_profile=billing_profile
    ).count()
    
    # Use credits with the existing session and additional tokens
    additional_amount = Decimal('15.00')
    additional_tokens = 1500
    billing_profile.use_credits(additional_amount, session=session, tokens=additional_tokens)
    
    # Verify no new session was created
    new_session_count = Session.objects.filter(
        billing_profile=billing_profile
    ).count()
    assert new_session_count == initial_session_count
    
    # Verify the session was updated correctly
    session.refresh_from_db()
    assert session.cost == Decimal('20.00')  # 5.00 + 15.00
    assert session.total_tokens == initial_tokens + additional_tokens  # Verify tokens were added

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


def test_user_receives_no_signup_credits_by_default():
    """Test that a new user receives no signup credits by default."""
    # Ensure BillingSettings exists with default value (0)
    BillingSettings.load()
    
    # Create a new user directly (not using the factory to ensure signals run)
    user = User.objects.create_user(
        username='credituser',
        email='credituser@example.com',
        password='password123'
    )
    
    # Get the billing profile created by the signal
    billing_profile = BillingProfile.objects.get(user=user)
    
    # Verify the user received no credits by default
    assert billing_profile.total_credits == Decimal('0.00')
    
    # Verify no promotion transaction was created
    transaction = Transaction.objects.filter(
        billing_profile=billing_profile,
        transaction_type='promotion'
    ).first()
    
    assert transaction is None


def test_user_receives_admin_configured_signup_credits():
    """Test that a new user receives the signup credits configured in the admin."""
    # Create or update the billing settings
    billing_settings = BillingSettings.load()
    billing_settings.signup_credits = Decimal('50.00')
    billing_settings.save()
    
    # Create a new user
    user = User.objects.create_user(
        username='admincredituser',
        email='admincredituser@example.com',
        password='password123'
    )
    
    # Get the billing profile created by the signal
    billing_profile = BillingProfile.objects.get(user=user)
    
    # Verify the user received the admin-configured credits
    assert billing_profile.total_credits == Decimal('50.00')
    
    # Verify a promotion transaction was created
    transaction = Transaction.objects.filter(
        billing_profile=billing_profile,
        transaction_type='promotion'
    ).first()
    
    assert transaction is not None
    assert transaction.amount == Decimal('50.00')





def test_add_token_usage_calculates_cost_correctly(user):
    """Test that add_token_usage calculates costs correctly based on token usage."""
    # Get the billing profile created by the signal
    billing_profile = BillingProfile.objects.get(user=user)
    
    # Add some initial credits
    billing_profile.add_credits(Decimal('100.00'))
    initial_balance = billing_profile.balance
    
    # Define token usage
    model_name = 'gpt-4o-mini-realtime-preview'
    input_tokens = 1000
    input_tokens_cached = 500
    output_tokens = 800
    
    # Calculate expected cost using token costs from database
    # Cost per million tokens * tokens / 1,000,000
    expected_cost = (
        (BillingSettings.get_token_cost(model_name, 'input') * input_tokens) + 
        (BillingSettings.get_token_cost(model_name, 'input-cached') * input_tokens_cached) + 
        (BillingSettings.get_token_cost(model_name, 'output') * output_tokens)
    ) / Decimal('1000000')
    expected_cost = expected_cost.quantize(Decimal('0.000001'))
    
    # Add token usage
    calculated_cost, new_balance = billing_profile.add_token_usage(
        model_name, 
        input_tokens, 
        input_tokens_cached, 
        output_tokens
    )
    
    # Verify the balance was updated correctly
    billing_profile.refresh_from_db()
    assert billing_profile.balance == initial_balance - expected_cost
    assert new_balance == initial_balance - expected_cost
    assert calculated_cost == expected_cost
    
    # Verify a session was created with the correct token count
    latest_session = Session.objects.filter(
        billing_profile=billing_profile
    ).latest('created_at')
    assert latest_session.cost == expected_cost
    assert latest_session.total_tokens == input_tokens + input_tokens_cached + output_tokens


def test_add_token_usage_with_existing_session(user):
    """Test adding token usage to an existing session."""
    # Get the billing profile created by the signal
    billing_profile = BillingProfile.objects.get(user=user)
    
    # Add some initial credits
    billing_profile.add_credits(Decimal('100.00'))
    
    # Create a session
    initial_tokens = 1000
    initial_cost = Decimal('0.01')
    session = Session.objects.create(
        billing_profile=billing_profile,
        total_tokens=initial_tokens,
        cost=initial_cost
    )
    
    # Define token usage
    model_name = 'gpt-4o-mini-realtime-preview'
    input_tokens = 2000
    input_tokens_cached = 1000
    output_tokens = 1500
    
    # Calculate expected cost using token costs from database
    expected_additional_cost = (
        (BillingSettings.get_token_cost(model_name, 'input') * input_tokens) + 
        (BillingSettings.get_token_cost(model_name, 'input-cached') * input_tokens_cached) + 
        (BillingSettings.get_token_cost(model_name, 'output') * output_tokens)
    ) / Decimal('1000000')
    expected_additional_cost = expected_additional_cost.quantize(Decimal('0.000001'))
    
    # Add token usage to the existing session
    billing_profile.add_token_usage(
        model_name, 
        input_tokens, 
        input_tokens_cached, 
        output_tokens,
        session=session
    )
    
    # Verify the session was updated correctly
    session.refresh_from_db()
    assert session.cost == initial_cost + expected_additional_cost
    assert session.total_tokens == initial_tokens + input_tokens + input_tokens_cached + output_tokens


def test_add_token_usage_with_insufficient_credits(user):
    """Test adding token usage when the user has insufficient credits."""
    # Get the billing profile created by the signal
    billing_profile = BillingProfile.objects.get(user=user)
    
    # Set up auto-recharge
    billing_profile.auto_recharge_enabled = True
    billing_profile.auto_recharge_amount = Decimal('20.00')
    billing_profile.monthly_recharge_limit = Decimal('100.00')
    billing_profile.save()
    
    # Define token usage that will cost more than the user's balance
    model_name = 'gpt-4o-mini-realtime-preview'
    input_tokens = 10000
    input_tokens_cached = 5000
    output_tokens = 8000
    
    # Calculate expected cost using token costs from database
    expected_cost = (
        (BillingSettings.get_token_cost(model_name, 'input') * input_tokens) + 
        (BillingSettings.get_token_cost(model_name, 'input-cached') * input_tokens_cached) + 
        (BillingSettings.get_token_cost(model_name, 'output') * output_tokens)
    ) / Decimal('1000000')
    expected_cost = expected_cost.quantize(Decimal('0.000001'))
    
    # Add token usage - this should trigger auto-recharge
    billing_profile.add_token_usage(
        model_name, 
        input_tokens, 
        input_tokens_cached, 
        output_tokens
    )
    
    # Verify auto-recharge occurred
    billing_profile.refresh_from_db()
    
    # Check for auto-recharge transaction
    auto_recharge_transaction = Transaction.objects.filter(
        billing_profile=billing_profile,
        transaction_type='auto_recharge'
    ).first()
    
    assert auto_recharge_transaction is not None
    assert auto_recharge_transaction.amount == Decimal('20.00')


def test_add_credit_intent(user):
    """Test creating a new credit intent."""
    profile = BillingProfile.objects.get(user=user)
    initial_credits = profile.total_credits
    
    # Create a pending transaction
    amount = Decimal('50.00')
    intent_id = 'pi_123'
    transaction = profile.add_credit_intent(amount, intent_id)
    
    # Verify transaction was created with correct state
    assert transaction.amount == amount
    assert transaction.status == 'pending'
    assert transaction.stripe_payment_intent_id == intent_id
    
    # Verify credits weren't added yet
    profile.refresh_from_db()
    assert profile.total_credits == initial_credits


def test_update_credit_intent_success_flow(user):
    """Test successful credit intent flow."""
    profile = BillingProfile.objects.get(user=user)
    initial_credits = profile.total_credits
    
    # Create and process a transaction
    amount = Decimal('50.00')
    intent_id = 'pi_123'
    transaction = profile.add_credit_intent(amount, intent_id)
    
    # Update to processing
    profile.update_credit_intent(intent_id, 'processing')
    transaction.refresh_from_db()
    assert transaction.status == 'processing'
    assert profile.total_credits == initial_credits  # Still no credits added
    
    # Update to succeeded
    profile.update_credit_intent(intent_id, 'succeeded')
    transaction.refresh_from_db()
    profile.refresh_from_db()
    assert transaction.status == 'succeeded'
    assert profile.total_credits == initial_credits + amount  # Credits added


def test_update_credit_intent_failure_flow(user):
    """Test failed credit intent flow."""
    profile = BillingProfile.objects.get(user=user)
    initial_credits = profile.total_credits
    
    # Create and process a transaction
    amount = Decimal('50.00')
    intent_id = 'pi_123'
    transaction = profile.add_credit_intent(amount, intent_id)
    
    # Update to processing then failed
    profile.update_credit_intent(intent_id, 'processing')
    profile.update_credit_intent(intent_id, 'failed')
    
    transaction.refresh_from_db()
    profile.refresh_from_db()
    assert transaction.status == 'failed'
    assert profile.total_credits == initial_credits  # No credits added


def test_delete_credit_intent(user):
    """Test deleting a credit intent."""
    profile = BillingProfile.objects.get(user=user)
    initial_credits = profile.total_credits
    
    # Create a pending transaction
    amount = Decimal('50.00')
    intent_id = 'pi_123'
    transaction = profile.add_credit_intent(amount, intent_id)
    
    # Delete the intent
    profile.delete_credit_intent(intent_id)
    
    # Verify transaction was deleted
    assert not Transaction.objects.filter(stripe_payment_intent_id=intent_id).exists()
    
    # Verify credits weren't affected
    profile.refresh_from_db()
    assert profile.total_credits == initial_credits
