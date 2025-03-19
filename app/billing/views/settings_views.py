from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from billing.models import BillingProfile
from billing.forms import BillingSettingsForm


class BillingSettingsView(LoginRequiredMixin, View):
    """
    Handle billing settings updates
    """
    template_name = 'billing/settings.html'
    
    def get(self, request):
        """Handle GET request - display the settings form"""
        billing_profile = request.user.billing_profile
        form = BillingSettingsForm(instance=billing_profile)
        
        context = {
            'form': form,
            'billing_profile': billing_profile,
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Handle POST request - process the settings form"""
        billing_profile = request.user.billing_profile
        form = BillingSettingsForm(request.POST, instance=billing_profile)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Billing settings updated successfully.')
            return redirect('billing:billing_dashboard')
        
        context = {
            'form': form,
            'billing_profile': billing_profile,
        }
        
        return render(request, self.template_name, context)
