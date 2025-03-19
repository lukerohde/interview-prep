from django.contrib import admin
from .models import BillingProfile, Session, Transaction


@admin.register(BillingProfile)
class BillingProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'auto_recharge_enabled', 'auto_recharge_amount', 'monthly_recharge_limit', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('total_credits', 'total_usage', 'created_at', 'updated_at')
    list_filter = ('auto_recharge_enabled',)


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('billing_profile', 'total_tokens', 'cost', 'created_at', 'updated_at', 'duration')
    search_fields = ('billing_profile__user__username', 'billing_profile__user__email')
    readonly_fields = ('created_at', 'updated_at')
    list_filter = ('created_at',)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('billing_profile', 'amount', 'transaction_type', 'created_at')
    search_fields = ('billing_profile__user__username', 'billing_profile__user__email', 'description')
    readonly_fields = ('created_at',)
    list_filter = ('transaction_type', 'created_at')
