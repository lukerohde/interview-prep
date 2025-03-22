from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
from uuid import uuid4


class BillingProfile(models.Model):
    """
    One-to-one relationship with User.
    Holds billing-related settings and running totals.
    """
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='billing_profile')
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_payment_method_id = models.CharField(max_length=100, blank=True, null=True)
    auto_recharge_enabled = models.BooleanField(default=False)
    auto_recharge_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    monthly_recharge_limit = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_credits = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_usage = models.DecimalField(max_digits=10, decimal_places=6, default=Decimal('0.00'))
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
        Add credits to the user's account and create a successful transaction record
        """
        if amount < 0:
            raise ValueError("Amount must be positive")
        
        self.total_credits += amount
        self.save()
        
        # Create transaction record with succeeded status
        Transaction.objects.create(
            billing_profile=self,
            amount=amount,
            transaction_type=transaction_type,
            status='succeeded'
        )
        
        return self.balance

    def add_credit_intent(self, amount, intent_id, type='recharge', description=None):
        """
        Create a pending transaction for a credit recharge intent
        
        Args:
            amount (Decimal): Amount to add
            intent_id (str): Stripe payment intent ID
            
        Returns:
            Transaction: The created transaction
        """
        if amount < 0:
            raise ValueError("Amount must be positive")
        
        description = description or f'Credit recharge of ${amount}'
        
        transaction = Transaction.objects.create(
            billing_profile=self,
            amount=amount,
            transaction_type=type,
            status='pending',
            stripe_payment_intent_id=intent_id,
            description=description
        )
        
        return transaction
    
    def update_credit_intent(self, intent_id, status):
        """
        Update a credit recharge intent's status and adjust credits accordingly
        
        Args:
            intent_id (str): Stripe payment intent ID
            status (str): New status ('succeeded', 'failed', 'cancelled')
            
        Returns:
            bool: True if transaction was found and updated
        """
        try:
            transaction = Transaction.objects.get(
                billing_profile=self,
                stripe_payment_intent_id=intent_id
            )
            
            if transaction.status != status:
                old_status = transaction.status
                transaction.status = status
                transaction.save()
                
                # Handle credit adjustments based on status change
                if old_status != 'succeeded' and status == 'succeeded':
                    # Going from not successful to successful - add credits
                    self.total_credits += transaction.amount
                    self.save()
                elif old_status == 'succeeded' and status != 'succeeded':
                    # Going from successful to not successful - remove credits
                    self.total_credits -= transaction.amount
                    self.save()
                
            return True
            
        except Transaction.DoesNotExist:
            return False
            
    def delete_credit_intent(self, intent_id):
        """
        Delete a pending credit recharge intent
        
        Args:
            intent_id (str): Stripe payment intent ID
            
        Returns:
            bool: True if transaction was found and deleted
        """
        try:
            transaction = Transaction.objects.get(
                billing_profile=self,
                stripe_payment_intent_id=intent_id,
                status__in=['pending', 'processing']  # Only delete if not completed
            )
            
            # Delete the transaction
            transaction.delete()
            return True
            
        except Transaction.DoesNotExist:
            return False
    
    def use_credits(self, amount, session=None, tokens=0):
        """
        Use credits and update the appropriate session
        
        Args:
            amount (Decimal): Amount of credits to use
            session (Session, optional): Session to update. If None, finds recent session or creates new one.
            tokens (int, optional): Number of tokens used in this transaction
            
        Returns:
            Decimal: Current balance after usage
        """
        if amount < 0:
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
                    # Create PaymentIntent for auto-recharge
                    if not self.stripe_payment_method_id:
                        raise ValueError("No payment method configured for auto-recharge")
                        
                    import stripe
                    stripe.api_key = settings.STRIPE_API_KEY
                    
                    # Create payment intent with the saved payment method
                    try:
                        intent = stripe.PaymentIntent.create(
                            amount=int(self.auto_recharge_amount * 100),  # Convert to cents
                            currency='usd',
                            customer=self.stripe_customer_id,
                            payment_method=self.stripe_payment_method_id,
                            payment_method_types=['card'],
                            confirm=True,  # Confirm immediately since we have the payment method
                            off_session=True,  # This is an automatic payment
                            description=f'Auto-recharge for {self.user.email}'
                        )
                        
                        # Create transaction record with auto_recharge type and update to processing
                        transaction = self.add_credit_intent(self.auto_recharge_amount, intent.id, type='auto_recharge', description=f'Auto-recharge for {self.user.email}')
                        self.update_credit_intent(intent.id, 'processing')
                        
                        # Note: Credits will be added by the webhook when payment succeeds
                    except stripe.error.StripeError as e:
                        # Create a failed transaction to track the error
                        Transaction.objects.create(
                            billing_profile=self,
                            amount=self.auto_recharge_amount,
                            transaction_type='auto_recharge',
                            status='failed',
                            description=f'Auto-recharge failed: {str(e)}'
                        )
                        raise ValueError(f"Auto-recharge failed: {str(e)}")
                else:
                    raise ValueError("Monthly recharge limit reached")
            else:
                raise ValueError("Insufficient credits")
        
        # Update total usage (balance is calculated as total_credits - total_usage)
        self.total_usage += amount
        self.save() # TODO Make this a transaction! 
        
        # Update or create session
        if session:
            session.add_usage(amount, tokens)
        else:
            # Check for recent session
            recent_session = self.sessions.filter(
                updated_at__gte=timezone.now() - timezone.timedelta(minutes=30)
            ).order_by('-updated_at').first()
            
            if recent_session:
                recent_session.add_usage(amount, tokens)
            else:
                # Create new session
                Session.objects.create(
                    billing_profile=self,
                    cost=amount,
                    total_tokens=tokens
                )
        
        return self.balance
        
    def add_token_usage(self, model_name, input_tokens, input_tokens_cached, output_tokens, session=None):
        """
        Add token usage to the user's account and calculate the cost
        
        Args:
            model_name (str): The model name (e.g., 'gpt-4o-mini-realtime-preview')
            input_tokens (int): Number of input tokens
            input_tokens_cached (int): Number of cached input tokens
            output_tokens (int): Number of output tokens
            session (Session, optional): Session to update. If None, finds recent session or creates new one.
            
        Returns:
            Decimal: Current balance after usage
        """
        # Get token costs from settings
        if input_tokens < 0 or input_tokens_cached < 0 or output_tokens < 0:
            raise ValueError("Token counts must be positive")

        input_cost = BillingSettings.get_token_cost(model_name, 'input')
        input_cached_cost = BillingSettings.get_token_cost(model_name, 'input-cached')
        output_cost = BillingSettings.get_token_cost(model_name, 'output')
        
        # Calculate total cost in dollars
        cost = ((input_tokens * input_cost) + 
                (input_tokens_cached * input_cached_cost) + 
                (output_tokens * output_cost)) / Decimal('1000000')
        
        # Round to 6 decimal places for precision in billing
        cost = cost.quantize(Decimal('0.000001'))
        
        # Total tokens used
        total_tokens = input_tokens + input_tokens_cached + output_tokens
        
        # Use credits and update session
        balance = self.use_credits(cost, session, total_tokens)
        return cost, balance


class Session(models.Model):
    """
    Represents a contiguous usage session (within 30 minutes).
    One-to-many relationship with BillingProfile.
    """
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    billing_profile = models.ForeignKey(BillingProfile, on_delete=models.CASCADE, related_name='sessions')
    total_tokens = models.IntegerField(default=0)
    cost = models.DecimalField(max_digits=10, decimal_places=6, default=Decimal('0.00'))
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
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled')
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    billing_profile = models.ForeignKey(BillingProfile, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    stripe_payment_intent_id = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type.capitalize()} of ${self.amount} for {self.billing_profile.user.username}"

    class Meta:
        ordering = ['-created_at']


class BillingSettingItem(models.Model):
    """
    Key-value pairs for billing settings.
    This allows for flexible configuration of token costs and other billing parameters.
    """
    key = models.CharField(max_length=100)
    value = models.DecimalField(max_digits=10, decimal_places=6)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.key}: {self.value}"
    
    class Meta:
        unique_together = ('key',)


class BillingSettings(models.Model):
    """
    Singleton model for global billing settings.
    This allows administrators to configure billing settings through the admin interface.
    """
    signup_credits = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Default credits to grant to new users upon signup. Set to zero to disable signup credits."
    )
    
    default_recharge_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('10.00'),
        help_text="Default amount shown in the recharge form. Must be between $5 and $1000, in increments of $5."
    )
    
    class Meta:
        verbose_name = "Billing Settings"
        verbose_name_plural = "Billing Settings"
    
    def save(self, *args, **kwargs):
        """Ensure only one instance of BillingSettings exists"""
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def load(cls):
        """Get the singleton settings object or create it if it doesn't exist"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
    
    @staticmethod
    def get_token_cost(model_name, token_type):
        """
        Get the cost per million tokens for a specific model and token type
        
        Args:
            model_name (str): The model name (e.g., 'gpt-4o-mini-realtime-preview')
            token_type (str): The token type (e.g., 'input', 'input-cached', 'output')
            
        Returns:
            Decimal: Cost per million tokens
        """
        key = f"{model_name}-{token_type}-cost"
        item = BillingSettingItem.objects.get(key=key)
        return item.value
        
        # try:
        #     item = BillingSettingItem.objects.get(key=key)
        #     return item.value
        # except BillingSettingItem.DoesNotExist:
        #     # Return default values if not found - use the highest price as a fallback
        #     # This ensures we don't undercharge if a specific model's pricing isn't found
        #     defaults = {
        #         # GPT-4o-realtime-preview prices 2025-03-19 https://platform.openai.com/docs/pricing
        #         'input': Decimal('5.00'),       # Default input token cost
        #         'input-cached': Decimal('2.50'),  # Default cached input token cost
        #         'output': Decimal('20.00')        # Default output token cost
        #     }
        #     # Extract the token type from the key
        #     return defaults.get(token_type, Decimal('20.00'))  # Default to highest price if token type unknown
    
    def __str__(self):
        return "Global Billing Settings"
