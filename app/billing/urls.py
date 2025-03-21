from django.urls import path
from billing.views import dashboard_views, credit_views, settings_views, history_views
from billing.views.token_usage_views import add_token_usage

app_name = 'billing'

urlpatterns = [
    path('', dashboard_views.billing_dashboard, name='billing_dashboard'),
    path('recharge/', credit_views.recharge_credits, name='recharge_credits'),
    path('settings/', settings_views.BillingSettingsView.as_view(), name='billing_settings'),
    path('sessions/', history_views.SessionHistoryView.as_view(), name='session_history'),
    path('transactions/', history_views.TransactionHistoryView.as_view(), name='transaction_history'),
    
    # Stripe webhook endpoint
    path('api/stripe-webhook/', credit_views.stripe_webhook, name='stripe_webhook'),
    
    # Transaction status updates
    path('api/update-transaction-status/', credit_views.update_transaction_status, name='update_transaction_status'),
    
    # API endpoint for token usage
    path('api/token-usage/', add_token_usage, name='add_token_usage'),
]
