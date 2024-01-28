from django.contrib import admin

from assistant.models import (
    Channel,
    Conversation,
    GeneralChatAnalytics,
    Message,
    MessageVote,
    Session,
)


class ChannelAdmin(admin.ModelAdmin):
    list_display = ["name", "description"]
    search_fields = ["name"]


class ConversationAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "get_customer_name",
        "get_channel_name",
        "started_at",
        "status",
    ]
    list_filter = ["status", "channel__name"]
    search_fields = ["customer__name", "channel__name"]
    date_hierarchy = "started_at"

    def get_customer_name(self, obj):
        return obj.customer.name if obj.customer else "N/A"

    get_customer_name.short_description = "Customer Name"

    def get_channel_name(self, obj):
        return obj.channel.name if obj.channel else "N/A"

    get_channel_name.short_description = "Channel Name"


class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "get_conversation_uuid", "content", "sender", "timestamp"]
    list_filter = ["sender", "timestamp"]
    search_fields = ["conversation__id", "content"]
    date_hierarchy = "timestamp"

    def get_conversation_uuid(self, obj):
        return obj.conversation.id

    get_conversation_uuid.short_description = "Conversation UUID"


class GeneralChatAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "get_conversation_uuid",
        "get_channel_name",
        "avg_response_time",
        "unanswered_questions",
        "failed_recommendations",
        "thumbs_up",
        "thumbs_down",
    ]
    search_fields = ["conversation__id", "conversation__channel__name"]

    def get_conversation_uuid(self, obj):
        return obj.conversation.id if obj.conversation else "N/A"

    get_conversation_uuid.short_description = "Conversation UUID"

    def get_channel_name(self, obj):
        return (
            obj.conversation.channel.name
            if obj.conversation and obj.conversation.channel
            else "N/A"
        )

    get_channel_name.short_description = "Channel Name"


class SessionAdmin(admin.ModelAdmin):
    list_display = ["id", "get_analytics_id", "start_time", "end_time"]
    list_filter = ["start_time", "end_time"]
    date_hierarchy = "start_time"

    def get_analytics_id(self, obj):
        return obj.analytics.id if obj.analytics else "N/A"

    get_analytics_id.short_description = "Analytics ID"


class MessageVoteAdmin(admin.ModelAdmin):
    list_display = ["id", "get_message_uuid", "vote_type", "timestamp"]
    list_filter = ["vote_type", "timestamp"]
    date_hierarchy = "timestamp"

    def get_message_uuid(self, obj):
        return obj.message.id if obj.message else "N/A"

    get_message_uuid.short_description = "Message UUID"


admin.site.register(Channel, ChannelAdmin)
admin.site.register(Conversation, ConversationAdmin)
admin.site.register(Message, MessageAdmin)
admin.site.register(GeneralChatAnalytics, GeneralChatAnalyticsAdmin)
admin.site.register(Session, SessionAdmin)
admin.site.register(MessageVote, MessageVoteAdmin)
