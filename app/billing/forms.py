from django import forms
from decimal import Decimal
from .models import BillingProfile


class RechargeCreditsForm(forms.Form):
    """Form for recharging credits"""
    amount = forms.DecimalField(
        min_value=Decimal('1.00'),
        max_digits=10,
        decimal_places=2,
        label="Amount to add ($)",
        help_text="Enter the amount you want to add to your account"
    )


class BillingSettingsForm(forms.ModelForm):
    """Form for updating billing settings"""
    class Meta:
        model = BillingProfile
        fields = [
            'auto_recharge_enabled',
            'auto_recharge_amount',
            'monthly_recharge_limit'
        ]
        widgets = {
            'auto_recharge_amount': forms.NumberInput(attrs={'min': '1.00', 'step': '0.01'}),
            'monthly_recharge_limit': forms.NumberInput(attrs={'min': '1.00', 'step': '0.01'}),
        }
        help_texts = {
            'auto_recharge_enabled': 'Enable automatic recharging when your balance is low',
            'auto_recharge_amount': 'Amount to automatically add when your balance is low',
            'monthly_recharge_limit': 'Maximum amount that can be auto-recharged in a month'
        }
