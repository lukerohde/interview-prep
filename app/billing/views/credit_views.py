from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from billing.models import BillingProfile
from billing.forms import RechargeCreditsForm


class RechargeCreditsView(LoginRequiredMixin, View):
    """
    Handle credit recharging
    """
    template_name = 'billing/recharge.html'
    
    def get(self, request):
        """Handle GET request - display the recharge form"""
        billing_profile = request.user.billing_profile
        form = RechargeCreditsForm()
        
        context = {
            'form': form,
            'billing_profile': billing_profile,
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Handle POST request - process the recharge form"""
        billing_profile = request.user.billing_profile
        form = RechargeCreditsForm(request.POST)
        
        if form.is_valid():
            amount = form.cleaned_data['amount']
            
            # In a real application, you would integrate with a payment processor here
            # For now, we'll just add the credits directly
            
            billing_profile.add_credits(amount)
            messages.success(request, f'Successfully added ${amount} to your account.')
            return redirect('billing:billing_dashboard')
        
        context = {
            'form': form,
            'billing_profile': billing_profile,
        }
        
        return render(request, self.template_name, context)
