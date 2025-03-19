import factory
from django.utils import timezone
from decimal import Decimal
from billing.models import BillingProfile, Session, Transaction
from .factories import UserFactory

class BillingProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BillingProfile
        django_get_or_create = ('user',)
    
    user = factory.SubFactory(UserFactory)
    total_credits = Decimal('100.00')
    total_usage = Decimal('0.00')
    auto_recharge_enabled = False
    auto_recharge_amount = Decimal('5.00')
    monthly_recharge_limit = Decimal('50.00')

class SessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Session
    
    billing_profile = factory.SubFactory(BillingProfileFactory)
    total_tokens = 1000
    cost = Decimal('10.00')

class TransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Transaction
    
    billing_profile = factory.SubFactory(BillingProfileFactory)
    amount = Decimal('50.00')
    transaction_type = 'recharge'
    description = "Test transaction"
