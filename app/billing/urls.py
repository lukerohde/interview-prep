from django.urls import path
from billing.views import dashboard_views, credit_views, settings_views, history_views

app_name = 'billing'

urlpatterns = [
    path('', dashboard_views.billing_dashboard, name='billing_dashboard'),
    path('recharge/', credit_views.RechargeCreditsView.as_view(), name='recharge_credits'),
    path('settings/', settings_views.BillingSettingsView.as_view(), name='billing_settings'),
    path('sessions/', history_views.SessionHistoryView.as_view(), name='session_history'),
    path('transactions/', history_views.TransactionHistoryView.as_view(), name='transaction_history'),
]
