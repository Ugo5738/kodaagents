from django.contrib import admin

from .models import Payment, WebhookLog


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'currency', 'status', 'reference', 'created_at', 'updated_at')
    list_filter = ('status', 'currency', 'created_at')
    search_fields = ('user__username', 'user__email', 'reference')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Payment Details', {
            'fields': ('amount', 'currency', 'reference', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

@admin.register(WebhookLog)
class WebhookLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'verified', 'processed', 'created_at')
    list_filter = ('verified', 'processed', 'created_at')
    search_fields = ('payload',)
    readonly_fields = ('created_at',)

    fieldsets = (
        ('Webhook Information', {
            'fields': ('verified', 'processed')
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
