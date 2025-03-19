from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

from billing.models import Session, Transaction


class SessionHistoryView(LoginRequiredMixin, View):
    """
    Show detailed session history
    """
    template_name = 'billing/session_history.html'
    
    def get(self, request):
        """Handle GET request - display session history"""
        billing_profile = request.user.billing_profile
        
        # Get all sessions, ordered by most recent first
        sessions = Session.objects.filter(
            billing_profile=billing_profile
        ).order_by('-created_at')
        
        context = {
            'sessions': sessions,
            'billing_profile': billing_profile,
        }
        
        return render(request, self.template_name, context)


class TransactionHistoryView(LoginRequiredMixin, View):
    """
    Show detailed transaction history
    """
    template_name = 'billing/transaction_history.html'
    
    def get(self, request):
        """Handle GET request - display transaction history"""
        billing_profile = request.user.billing_profile
        
        # Get all transactions, ordered by most recent first
        transactions = Transaction.objects.filter(
            billing_profile=billing_profile
        ).order_by('-created_at')
        
        context = {
            'transactions': transactions,
            'billing_profile': billing_profile,
        }
        
        return render(request, self.template_name, context)
