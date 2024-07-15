from django.contrib import admin
from django.utils.html import format_html

from accounts.models import GoogleToken, OrganizationProfile, User


class UserAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "email",
        "username",
        "phone",
        "gender",
        "email_verified",
        "is_paid",
        "usage_count"
    ]
    list_filter = ["email_verified", "date_of_birth", "is_paid"]
    search_fields = ["email", "username", "phone"]


class OrganizationProfileAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "bio", "city", "address", "country", "zip_code"]
    list_filter = ["city", "country"]
    search_fields = ["name", "bio", "city", "address", "zip_code"]
    raw_id_fields = ["user"]


class GoogleTokenAdmin(admin.ModelAdmin):
    list_display = ["user", "email", "access_token_truncated", "refresh_token_truncated", "expires_at", "is_expired"]
    readonly_fields = ["access_token", "refresh_token", "expires_at"]

    def access_token_truncated(self, obj):
        return format_html('<span title="{}">{}</span>', obj.access_token, obj.access_token[:20] + '...')
    access_token_truncated.short_description = 'Access Token'

    def refresh_token_truncated(self, obj):
        return format_html('<span title="{}">{}</span>', obj.refresh_token, obj.refresh_token[:20] + '...')
    refresh_token_truncated.short_description = 'Refresh Token'

    def is_expired(self, obj):
        return obj.expired
    is_expired.boolean = True
    is_expired.short_description = 'Expired'


admin.site.register(User, UserAdmin)
admin.site.register(OrganizationProfile, OrganizationProfileAdmin)
admin.site.register(GoogleToken, GoogleTokenAdmin)
