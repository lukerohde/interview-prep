from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum
from datetime import timedelta
from decimal import Decimal

from billing.models import BillingProfile, Session, Transaction


@login_required
def billing_dashboard(request):
    """
    Main billing dashboard showing credit balance, usage, and settings
    """
    # Get or create billing profile
    billing_profile, created = BillingProfile.objects.get_or_create(user=request.user)
    
    # Get recent sessions (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_sessions = Session.objects.filter(
        billing_profile=billing_profile,
        created_at__gte=thirty_days_ago
    ).order_by('-created_at')
    
    # Get recent transactions
    recent_transactions = Transaction.objects.filter(
        billing_profile=billing_profile
    ).order_by('-created_at')[:10]
    
    # Calculate monthly usage
    current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_usage = Session.objects.filter(
        billing_profile=billing_profile,
        created_at__gte=current_month_start
    ).aggregate(total=Sum('cost'))['total'] or Decimal('0.00')
    
    context = {
        'billing_profile': billing_profile,
        'recent_sessions': recent_sessions,
        'recent_transactions': recent_transactions,
        'monthly_usage': monthly_usage,
    }
    
    return render(request, 'billing/dashboard.html', context)
