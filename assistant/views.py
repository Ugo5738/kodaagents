# from datacenter import models as datacenter_models
from koda.config.logging_config import configure_logger
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Sum
from django.shortcuts import render
from django.views import View
from django.views.generic import View

from accounts.models import OrganizationCustomer
from assistant.models import (
    Conversation,
    GeneralChatAnalytics,
    Message,
    MessageVote,
    Session,
)

logger = configure_logger(__name__)


# Template Views
def index(request):
    print(request.user)
    return render(request, "judy/dashboard.html")


class DashboardView(View, LoginRequiredMixin):
    template_name = "judy/dashboard.html"

    def get(self, request):
        total_customer = OrganizationCustomer.objects.all().count()

        total_convo_num = Conversation.objects.all().count()
        conversation_total_upvotes = GeneralChatAnalytics.objects.aggregate(
            Sum("thumbs_up")
        )["thumbs_up__sum"]
        conversation_total_downvotes = GeneralChatAnalytics.objects.aggregate(
            Sum("thumbs_down")
        )["thumbs_down__sum"]
        avg_response_time = GeneralChatAnalytics.objects.aggregate(
            Avg("avg_response_time")
        )["avg_response_time__avg"]

        # Count message-level upvotes and downvotes
        message_total_upvotes = MessageVote.objects.filter(vote_type="UP").count()
        message_total_downvotes = MessageVote.objects.filter(vote_type="DOWN").count()

        # Average response time for "Learn" and "Recommend" channels
        avg_response_time_learn = GeneralChatAnalytics.objects.filter(
            conversation__channel__name="learn"
        ).aggregate(Avg("avg_response_time"))["avg_response_time__avg"]
        avg_response_time_recommend = GeneralChatAnalytics.objects.filter(
            conversation__channel__name="recommend"
        ).aggregate(Avg("avg_response_time"))["avg_response_time__avg"]

        # Total number of sessions
        total_sessions = Session.objects.all().count()

        # Total number of unanswered questions and failed recommendations
        total_unanswered_questions = GeneralChatAnalytics.objects.aggregate(
            Sum("unanswered_questions")
        )["unanswered_questions__sum"]
        total_failed_recommendations = GeneralChatAnalytics.objects.aggregate(
            Sum("failed_recommendations")
        )["failed_recommendations__sum"]

        # Total number of anonymous users
        total_anonymous_users = Conversation.objects.filter(
            customer__isnull=True
        ).count()

        # total_mortgage_plans = datacenter_models.MortgagePlan.objects.all().count()
        # total_locations = datacenter_models.GeographicalLocation.objects.all().count()
        # total_properties = datacenter_models.Property.objects.all().count()
        # total_providers = datacenter_models.Provider.objects.all().count()

        context = {
            "total_customer": total_customer,
            "conversation_total_upvotes": conversation_total_upvotes,
            "conversation_total_downvotes": conversation_total_downvotes,
            "avg_response_time": avg_response_time,
            "total_convo_num": total_convo_num,
            "message_total_upvotes": message_total_upvotes,
            "message_total_downvotes": message_total_downvotes,
            "avg_response_time_learn": avg_response_time_learn,
            "avg_response_time_recommend": avg_response_time_recommend,
            "total_sessions": total_sessions,
            "total_unanswered_questions": total_unanswered_questions,
            "total_failed_recommendations": total_failed_recommendations,
            "total_anonymous_users": total_anonymous_users,
        }

        return render(request, self.template_name, context)


class ConversationView(View):
    def get(self, request, *args, **kwargs):
        messages = Message.objects.select_related(
            "conversation__customer", "conversation__channel"
        ).all()
        for message in messages:
            message.channel_name = (
                message.conversation.channel.name
                if message.conversation.channel
                else "N/A"
            )
            message.customer_id = (
                message.conversation.customer.id
                if message.conversation.customer
                else "N/A"
            )

        return render(request, "judy/conversations.html", {"messages": messages})


class AnalyticsView(View):
    def get(self, request, *args, **kwargs):
        analytics = (
            GeneralChatAnalytics.objects.select_related(
                "conversation__customer", "conversation__channel"
            )
            .prefetch_related("sessions")
            .all()
        )
        flat_analytics = []

        for analytic in analytics:
            analytic_base = {
                "customer_name": analytic.conversation.customer.name
                if analytic.conversation.customer
                else "N/A",
                "conversation_uuid": analytic.conversation.id
                if analytic.conversation
                else "N/A",
                "channel_name": analytic.conversation.channel.name
                if analytic.conversation.channel
                else "N/A",
                "avg_response_time": analytic.avg_response_time,
                "unanswered_questions": analytic.unanswered_questions,
                "failed_recommendations": analytic.failed_recommendations,
                "thumbs_up": analytic.thumbs_up,
                "thumbs_down": analytic.thumbs_down,
            }
            sessions = analytic.sessions.all()
            for session in sessions:
                new_row = analytic_base.copy()
                new_row["start_time"] = session.start_time
                new_row["end_time"] = session.end_time
                flat_analytics.append(new_row)

        return render(request, "judy/analytics.html", {"analytics": flat_analytics})


class ChatbotView(View):
    template_name = "judy/chatbot_widget.html"

    def get(self, request):
        return render(request, self.template_name)
