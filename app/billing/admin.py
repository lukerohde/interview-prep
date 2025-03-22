from django.contrib import admin
from django.template.response import TemplateResponse
from decimal import Decimal, InvalidOperation
from .models import BillingProfile, Session, Transaction, BillingSettings


@admin.register(BillingProfile)
class BillingProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'auto_recharge_enabled', 'auto_recharge_amount', 'monthly_recharge_limit', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('total_credits', 'total_usage', 'created_at', 'updated_at')
    list_filter = ('auto_recharge_enabled',)
    actions = ['make_credit_adjustment']
    
    def make_credit_adjustment(self, request, queryset):
        if request.method == 'POST' and 'apply' in request.POST:
            amount_str = request.POST.get('amount', '0')
            description = request.POST.get('description', '')
            
            try:
                amount = Decimal(amount_str)
            except (ValueError, TypeError, InvalidOperation):
                context = {
                    **self.admin_site.each_context(request),
                    'opts': self.model._meta,
                    'title': 'Bulk Credit Adjustment',
                    'queryset': queryset,
                    'count': queryset.count(),
                    'media': self.media,
                    'error': 'Invalid amount specified'
                }
                return TemplateResponse(
                    request,
                    'admin/billing/billingprofile/bulk_credit_adjustment.html',
                    context,
                )
            
            for billing_profile in queryset:
                try:
                    billing_profile.adjust_credits(amount, description)
                except ValueError as e:
                    context = {
                        **self.admin_site.each_context(request),
                        'opts': self.model._meta,
                        'title': 'Bulk Credit Adjustment',
                        'queryset': queryset,
                        'count': queryset.count(),
                        'media': self.media,
                        'error': str(e)
                    }
                    return TemplateResponse(
                        request,
                        'admin/billing/billingprofile/bulk_credit_adjustment.html',
                        context,
                    )
            
            self.message_user(request, f'Successfully adjusted credits by {amount} for {queryset.count()} users')
            return None
        
        context = {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'title': 'Bulk Credit Adjustment',
            'queryset': queryset,
            'count': queryset.count(),
            'media': self.media,
        }
        
        return TemplateResponse(
            request,
            'admin/billing/billingprofile/bulk_credit_adjustment.html',
            context,
        )
    make_credit_adjustment.short_description = 'Make credit adjustment'


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('billing_profile', 'total_tokens', 'cost', 'created_at', 'updated_at', 'duration')
    search_fields = ('billing_profile__user__username', 'billing_profile__user__email')
    readonly_fields = ('created_at', 'updated_at')
    list_filter = ('created_at',)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('billing_profile', 'amount', 'transaction_type', 'status', 'description','created_at')
    search_fields = ('billing_profile__user__username', 'billing_profile__user__email', 'description', 'status', 'transaction_type')
    readonly_fields = ('created_at',)
    list_filter = ('transaction_type', 'created_at', 'status')


@admin.register(BillingSettings)
class BillingSettingsAdmin(admin.ModelAdmin):
    list_display = ('signup_credits', 'default_recharge_amount')
    
    def has_add_permission(self, request):
        # Only allow one instance of BillingSettings
        return not BillingSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of the settings object
        return False
