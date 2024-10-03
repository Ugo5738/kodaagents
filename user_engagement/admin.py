from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from user_engagement.models import Attachment, Conversation, Feedback, Message


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("email", "subject", "user", "received_at", "body_preview")
    list_filter = ("received_at", "subject")
    search_fields = ("email", "subject", "body", "user__username")
    readonly_fields = ("received_at",)
    raw_id_fields = ("user",)
    date_hierarchy = "received_at"

    def body_preview(self, obj):
        return obj.body[:50] + "..." if len(obj.body) > 50 else obj.body

    body_preview.short_description = "Body Preview"


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ("id", "sender", "content_preview", "sent_at", "is_incoming")
    readonly_fields = ("id", "content_preview", "sent_at")

    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content

    content_preview.short_description = "Content Preview"


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("subject", "email", "user", "created_at", "message_count")
    list_filter = ("created_at",)
    search_fields = ("email", "subject", "user__username")
    readonly_fields = ("created_at",)
    raw_id_fields = ("user",)
    date_hierarchy = "created_at"
    inlines = [MessageInline]

    def message_count(self, obj):
        return obj.messages.count()

    message_count.short_description = "Number of Messages"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "sender", "content_preview", "sent_at", "is_incoming")
    list_filter = ("sent_at", "is_incoming", "sender")
    search_fields = ("content", "conversation__subject", "conversation__email")
    readonly_fields = ("sent_at",)
    raw_id_fields = ("conversation",)
    date_hierarchy = "sent_at"

    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content

    content_preview.short_description = "Content Preview"

    fieldsets = (
        (None, {"fields": ("conversation", "sender", "is_incoming", "sent_at", "content")}),
    )


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ("filename", "message_link", "content_type", "size", "uploaded_at")
    list_filter = ("content_type", "uploaded_at")
    search_fields = ("filename", "message__content", "message__conversation__subject")
    readonly_fields = ("uploaded_at",)

    def message_link(self, obj):
        url = reverse("admin:user_engagement_message_change", args=[obj.message.id])
        return format_html('<a href="{}">{}</a>', url, obj.message)

    message_link.short_description = "Message"
