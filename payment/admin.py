from django.contrib import admin
from .models import Payment, WebhookLog, Subscription

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'currency', 'status', 'reference', 'provider', 'created_at', 'updated_at')
    list_filter = ('status', 'currency', 'provider', 'created_at')
    search_fields = ('user__username', 'user__email', 'reference', 'stripe_payment_intent_id', 'stripe_charge_id')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Payment Details', {
            'fields': ('amount', 'currency', 'reference', 'status', 'provider', 'subscription')
        }),
        ('Stripe Details', {
            'fields': ('stripe_payment_intent_id', 'stripe_charge_id'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'subscription')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'provider', 'current_period_start', 'current_period_end', 'cancel_at_period_end')
    list_filter = ('status', 'provider', 'current_period_start', 'current_period_end')
    search_fields = ('user__username', 'user__email', 'stripe_subscription_id', 'paystack_subscription_code')
    readonly_fields = ('canceled_at',)

    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Subscription Details', {
            'fields': ('status', 'provider', 'stripe_subscription_id', 'paystack_subscription_code')
        }),
        ('Period Information', {
            'fields': ('current_period_start', 'current_period_end', 'cancel_at_period_end', 'canceled_at')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(WebhookLog)
class WebhookLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'provider', 'verified', 'processed', 'created_at')
    list_filter = ('verified', 'processed', 'provider', 'created_at')
    search_fields = ('payload',)
    readonly_fields = ('created_at',)

    fieldsets = (
        ('Webhook Information', {
            'fields': ('provider', 'verified', 'processed')
        }),
        ('Payload', {
            'fields': ('payload',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )

    def has_add_permission(self, request):
        return False  # Prevent manual creation of webhook logs
