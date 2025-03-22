from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from billing.models import Session, Transaction


@login_required
def session_history(request):
    """Show detailed session history"""
    billing_profile = request.user.billing_profile
    
    # Get all sessions, ordered by most recent first
    sessions = Session.objects.filter(
        billing_profile=billing_profile
    ).order_by('-created_at')
    
    context = {
        'sessions': sessions,
        'billing_profile': billing_profile,
    }
    
    return render(request, 'billing/session_history.html', context)


@login_required
def transaction_history(request):
    """Show detailed transaction history"""
    billing_profile = request.user.billing_profile
    
    # Get all non-pending transactions, ordered by most recent first
    transactions = Transaction.objects.filter(
        billing_profile=billing_profile
    ).exclude(
        status='pending'
    ).order_by('-created_at')
    
    context = {
        'transactions': transactions,
        'billing_profile': billing_profile,
    }
    
    return render(request, 'billing/transaction_history.html', context)
