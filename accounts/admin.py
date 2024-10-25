from datetime import timedelta

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Count, Sum
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from accounts.models import (
    GoogleToken,
    LoginHistory,
    OrganizationProfile,
    User,
    UserNotification,
    UserTier,
)


# Inline admin descriptor for OrganizationProfile
class OrganizationProfileInline(admin.StackedInline):
    model = OrganizationProfile
    can_delete = False
    verbose_name_plural = "Organization Profile"


class UserTierAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "download_limit",
        "creation_limit",
        "customization_limit",
        "price",
        "user_count",
    )
    list_editable = ("download_limit", "creation_limit", "customization_limit", "price")
    search_fields = ("name",)

    def user_count(self, obj):
        return obj.users.count()

    user_count.short_description = "Number of Users"

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(user_count=Sum("users"))
        return queryset


class UserAdmin(admin.ModelAdmin):
    inlines = (OrganizationProfileInline,)

    list_display = (
        "email",
        "email_verified",
        "first_name",
        "last_name",
        "tier_display",
        "download_count",
        "creation_count",
        "customization_count",
        "total_usage",
        "date_joined",
        "last_login",
    )
    list_filter = ("tier", "email_verified", "is_active", "is_staff", "date_joined", "last_login")
    search_fields = ("email", "username", "first_name", "last_name", "stripe_customer_id")
    readonly_fields = ("date_joined", "last_login", "total_usage", "usage_chart")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal info",
            {"fields": ("first_name", "last_name", "date_of_birth", "profile_picture")},
        ),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        (
            "Tier & Usage",
            {
                "fields": (
                    "tier",
                    "stripe_customer_id",
                    "download_count",
                    "creation_count",
                    "customization_count",
                    "total_usage",
                    "usage_chart",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "tier", "stripe_customer_id"),
            },
        ),
    )
    ordering = ("-date_joined",)

    def tier_display(self, obj):
        if obj.tier:
            url = reverse("admin:accounts_usertier_change", args=[obj.tier.id])
            return format_html('<a href="{}">{}</a>', url, obj.tier.name)
        return "No Tier"

    tier_display.short_description = "Tier"

    def total_usage(self, obj):
        return obj.total_usage_count

    total_usage.short_description = "Total Usage"

    def usage_chart(self, obj):
        if obj.tier:
            download_percent = min(100, (obj.download_count / obj.tier.download_limit) * 100)
            creation_percent = min(100, (obj.creation_count / obj.tier.creation_limit) * 100)
            customization_percent = min(
                100, (obj.customization_count / obj.tier.customization_limit) * 100
            )

            chart = f"""
            <div style="width: 300px;">
                <div style="margin-bottom: 10px;">
                    <span style="display: inline-block; width: 100px;">Downloads:</span>
                    <div style="display: inline-block; width: 200px; background-color: #eee;">
                        <div style="width: {download_percent}%; height: 20px; background-color: #4CAF50;"></div>
                    </div>
                    <span style="margin-left: 10px;">{obj.download_count}/{obj.tier.download_limit}</span>
                </div>
                <div style="margin-bottom: 10px;">
                    <span style="display: inline-block; width: 100px;">Creations:</span>
                    <div style="display: inline-block; width: 200px; background-color: #eee;">
                        <div style="width: {creation_percent}%; height: 20px; background-color: #2196F3;"></div>
                    </div>
                    <span style="margin-left: 10px;">{obj.creation_count}/{obj.tier.creation_limit}</span>
                </div>
                <div>
                    <span style="display: inline-block; width: 100px;">Customizations:</span>
                    <div style="display: inline-block; width: 200px; background-color: #eee;">
                        <div style="width: {customization_percent}%; height: 20px; background-color: #FFC107;"></div>
                    </div>
                    <span style="margin-left: 10px;">{obj.customization_count}/{obj.tier.customization_limit}</span>
                </div>
            </div>
            """
            return format_html(chart)
        return "No tier assigned"

    usage_chart.short_description = "Usage Chart"

    actions = ["reset_usage_counts"]

    def reset_usage_counts(self, request, queryset):
        updated = queryset.update(download_count=0, creation_count=0, customization_count=0)
        self.message_user(request, f"{updated} users had their usage counts reset.")

    reset_usage_counts.short_description = "Reset usage counts for selected users"


class OrganizationProfileAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "bio", "city", "address", "country", "zip_code"]
    list_filter = ["city", "country"]
    search_fields = ["name", "bio", "city", "address", "zip_code"]
    raw_id_fields = ["user"]


class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ("user_email", "notification_type", "sent_at", "days_since_sent")
    list_filter = (
        "notification_type",
        "sent_at",
    )
    search_fields = (
        "user__email",
        "user__username",
        "notification_type",
    )
    readonly_fields = ("sent_at",)
    date_hierarchy = "sent_at"

    # Custom fields for list_display
    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = "User Email"
    user_email.admin_order_field = "user__email"

    def days_since_sent(self, obj):
        delta = timezone.now() - obj.sent_at
        return f"{delta.days} days ago"

    days_since_sent.short_description = "Sent"

    # Custom actions
    actions = ["resend_notifications", "mark_as_inactive"]

    def resend_notifications(self, request, queryset):
        # Placeholder for notification resending logic
        count = queryset.count()
        self.message_user(request, f"Queued {count} notifications for resending.")

    resend_notifications.short_description = "Resend selected notifications"

    def mark_as_inactive(self, request, queryset):
        # Placeholder for marking notifications as inactive
        count = queryset.count()
        self.message_user(request, f"Marked {count} notifications as inactive.")

    mark_as_inactive.short_description = "Mark selected notifications as inactive"

    # Custom admin views
    def changelist_view(self, request, extra_context=None):
        # Add extra statistics to the change list view
        if not extra_context:
            extra_context = {}

        # Get notification counts by type
        notification_stats = UserNotification.objects.values("notification_type").annotate(
            count=Count("id")
        )

        # Get recent notification counts
        recent_notifications = UserNotification.objects.filter(
            sent_at__gte=timezone.now() - timedelta(days=7)
        ).count()

        extra_context.update(
            {
                "notification_stats": notification_stats,
                "recent_notifications": recent_notifications,
            }
        )

        return super().changelist_view(request, extra_context=extra_context)

    # Fieldsets for organized form layout
    fieldsets = (
        ("User Information", {"fields": ("user",)}),
        (
            "Notification Details",
            {"fields": ("notification_type", "sent_at"), "classes": ("wide",)},
        ),
    )

    # Performance optimizations
    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")

    # Custom save handling
    def save_model(self, request, obj, form, change):
        if not change:  # Only for new notifications
            # Add any custom logic for new notifications here
            pass
        super().save_model(request, obj, form, change)


class GoogleTokenAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "email",
        "access_token_truncated",
        "refresh_token_truncated",
        "expires_at",
        "is_expired",
    ]
    readonly_fields = ["access_token", "refresh_token", "expires_at"]

    def access_token_truncated(self, obj):
        return format_html(
            '<span title="{}">{}</span>', obj.access_token, obj.access_token[:20] + "..."
        )

    access_token_truncated.short_description = "Access Token"

    def refresh_token_truncated(self, obj):
        return format_html(
            '<span title="{}">{}</span>', obj.refresh_token, obj.refresh_token[:20] + "..."
        )

    refresh_token_truncated.short_description = "Refresh Token"

    def is_expired(self, obj):
        return obj.expired

    is_expired.boolean = True
    is_expired.short_description = "Expired"


class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ("user", "login_time", "logout_time", "ip_address", "get_session_duration")
    list_filter = ("user", "login_time")
    search_fields = ("user__username", "ip_address")
    readonly_fields = (
        "login_time",
        "logout_time",
        "ip_address",
        "user_agent",
        "get_session_duration",
    )

    def get_session_duration(self, obj):
        duration = obj.session_duration
        if duration:
            seconds = duration.total_seconds()
            hours, remainder = divmod(seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            return f"{int(hours)} hours, {int(minutes)} minutes"
        return "Session ongoing"

    get_session_duration.short_description = "Session Duration"


admin.site.register(UserTier, UserTierAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(UserNotification, UserNotificationAdmin)
admin.site.register(OrganizationProfile, OrganizationProfileAdmin)
admin.site.register(GoogleToken, GoogleTokenAdmin)
admin.site.register(LoginHistory, LoginHistoryAdmin)
