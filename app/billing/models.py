from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from uuid import uuid4


class BillingProfile(models.Model):
    """
    One-to-one relationship with User.
    Holds billing-related settings and running totals.
    """
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='billing_profile')
    auto_recharge_enabled = models.BooleanField(default=False)
    auto_recharge_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    monthly_recharge_limit = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_credits = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_usage = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Billing Profile"

    @property
    def balance(self):
        """Calculate the current balance as total_credits - total_usage"""
        return self.total_credits - self.total_usage

    def add_credits(self, amount, transaction_type='recharge'):
        """
        Add credits to the user's account and create a transaction record
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        self.total_credits += amount
        self.save()
        
        # Create transaction record
        Transaction.objects.create(
            billing_profile=self,
            amount=amount,
            transaction_type=transaction_type
        )
        
        return self.balance
    
    def use_credits(self, amount, session=None):
        """
        Use credits and update the appropriate session
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        if self.balance < amount:
            # Handle insufficient credits
            if self.auto_recharge_enabled and self.auto_recharge_amount > 0:
                # Check monthly limit
                month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                month_recharges = Transaction.objects.filter(
                    billing_profile=self,
                    transaction_type='auto_recharge',
                    created_at__gte=month_start
                ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
                
                if month_recharges + self.auto_recharge_amount <= self.monthly_recharge_limit:
                    # Auto-recharge
                    self.add_credits(self.auto_recharge_amount, 'auto_recharge')
                else:
                    raise ValueError("Monthly recharge limit reached")
            else:
                raise ValueError("Insufficient credits")
        
        # Update total usage
        self.total_usage += amount
        self.save()
        
        # Update or create session
        if session:
            session.add_usage(amount)
        else:
            # Check for recent session
            recent_session = self.sessions.filter(
                updated_at__gte=timezone.now() - timezone.timedelta(minutes=30)
            ).order_by('-updated_at').first()
            
            if recent_session:
                recent_session.add_usage(amount)
            else:
                # Create new session
                Session.objects.create(
                    billing_profile=self,
                    cost=amount,
                    total_tokens=0  # This would need to be calculated based on your token pricing
                )
        
        return self.balance


class Session(models.Model):
    """
    Represents a contiguous usage session (within 30 minutes).
    One-to-many relationship with BillingProfile.
    """
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    billing_profile = models.ForeignKey(BillingProfile, on_delete=models.CASCADE, related_name='sessions')
    total_tokens = models.IntegerField(default=0)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Session {self.id} for {self.billing_profile.user.username}"

    @property
    def duration(self):
        """Calculate session duration in minutes"""
        return (self.updated_at - self.created_at).total_seconds() / 60
    
    def add_usage(self, cost, tokens=0):
        """
        Add usage to this session
        """
        self.cost += cost
        self.total_tokens += tokens
        self.updated_at = timezone.now()
        self.save()


class Transaction(models.Model):
    """
    Records changes to credits (recharges, refunds, etc.)
    One-to-many relationship with BillingProfile.
    """
    TRANSACTION_TYPES = [
        ('recharge', 'Manual Recharge'),
        ('auto_recharge', 'Automatic Recharge'),
        ('refund', 'Refund'),
        ('adjustment', 'Account Adjustment'),
        ('promotion', 'Promotion')
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    billing_profile = models.ForeignKey(BillingProfile, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type.capitalize()} of ${self.amount} for {self.billing_profile.user.username}"

    class Meta:
        ordering = ['-created_at']
