from datetime import timedelta

from asgiref.sync import async_to_sync
from celery import shared_task
from django.core.exceptions import ValidationError
from django.utils import timezone

from accounts.models import User, UserNotification
from helpers.email_utils import (
    generate_personalized_email,
    generate_support_team_email,
    generate_user_escalation_email,
    send_email,
    wrap_in_template,
)
from koda.config.logging_config import configure_logger
from resume.utils.util_funcs import get_anth_chat_response
from user_engagement.models import Conversation, Message

logger = configure_logger(__name__)


@shared_task
def notify_users_nearing_free_limit():
    """
    Task to send emails to users who are at or approaching their free tier limit.
    """
    FREE_TIER_CREATION_LIMIT = 2
    threshold = FREE_TIER_CREATION_LIMIT - 1
    notification_interval = timedelta(days=7)  # Only notify once every 7 days

    users = User.objects.filter(
        tier__name="free",
        creation_count__gte=threshold,
    )

    for user in users:
        # Check if a notification was sent within the interval
        recent_notification = UserNotification.objects.filter(
            user=user,
            notification_type="nearing_limit",
            sent_at__gte=timezone.now() - notification_interval,
        ).exists()

        if not recent_notification:
            send_email_to_user_nearing_limit(user)
            # Record the notification
            UserNotification.objects.create(user=user, notification_type="nearing_limit")


def send_email_to_user_nearing_limit(user):
    prompt = f"""
You are Taylor R., a customer success assistant for ResumeGuru. Generate an email to inform a free-tier user that they've reached their usage limit.

ResumeGuru is an AI powered platform that helps users optimize their resumes to specific job posts and it creates corresponding cover letters
- This is the login url: https://resumeguru.pro/login
- This is the dashboard where the user can edit and create resumes and cover letter: https://resumeguru.pro/dashboard
- This is the billing page url where the user can upgrade his account: https://resumeguru.pro/dashboard/billing
- ResumeGuru's theme color is indigo, so the buttons should match
- Use your name as the closing greeting because you are part of the ResumeGuru Team

Please output the email as a JSON object with the following keys:
- "subject": The subject of the email.
- "body": The HTML content of the email body.

Include personalized elements using the user's first name: {user.first_name}.

Example format:
{{
  "subject": "Your Subject Here",
  "body": "Your HTML body here"
}}

Generate only the JSON response.
"""

    try:
        email_content = async_to_sync(get_anth_chat_response)(prompt)
    except Exception as e:
        logger.error(f"Failed to generate email content: {e}")
        email_content = {
            "subject": "You're nearing your free usage limit on ResumeGuru",
            "body": f"""
                <p>Hi {user.first_name},</p>
                <p>You're nearing your free usage limit on ResumeGuru. Upgrade now to continue enjoying our services without interruption.</p>
                <p>Best regards,<br>ResumeGuru Team</p>
            """,
        }

    html_content = wrap_in_template(email_content["body"])
    subject = email_content["subject"]

    send_email(
        to_email=user.email,
        subject=subject,
        message="",
        html_content=html_content,
        from_email="ResumeGuru Support <support@resumeguru.pro>",
    )


@shared_task
def notify_inactive_paid_users():
    """
    Task to send re-engagement emails to paid users who have been inactive.
    """
    inactivity_period = timezone.now() - timedelta(days=7)
    notification_interval = timedelta(days=14)  # Notify once every 14 days

    users = User.objects.filter(
        tier__name__in=["essential", "professional", "premium"],
        last_login__lt=inactivity_period,
    )

    for user in users:
        # Check if a notification was sent within the interval
        recent_notification = UserNotification.objects.filter(
            user=user,
            notification_type="inactive_paid_user",
            sent_at__gte=timezone.now() - notification_interval,
        ).exists()

        if not recent_notification:
            send_email_to_inactive_paid_user(user)
            # Record the notification
            UserNotification.objects.create(user=user, notification_type="inactive_paid_user")


def send_email_to_inactive_paid_user(user):
    prompt = f"""
You are Taylor R., a customer success assistant for ResumeGuru. Generate a personalized re-engagement email for a paid user who has been inactive.

ResumeGuru is an AI powered platform that helps users optimize their resumes to specific job posts and it creates corresponding cover letters
- This is the dashboard where the user can edit and create resumes and cover letter: https://resumeguru.pro/dashboard
- This is the login url: https://resumeguru.pro/login
- ResumeGuru's theme color is indigo, so the buttons you use should match
- Use your name as the closing greeting because you are part of the ResumeGuru Team

Please output the email as a JSON object with the following keys:
- "subject": The subject of the email.
- "body": The HTML content of the email body.

Include personalized elements using the user's first name: {user.first_name}.

Example format:
{{   
  "subject": "Your Subject Here",
  "body": "Your HTML body here"
}}

Generate only the JSON response.
"""

    try:
        email_content = async_to_sync(get_anth_chat_response)(prompt)
    except Exception as e:
        logger.error(f"Failed to generate email content: {e}")
        email_content = {
            "subject": "We miss you at ResumeGuru!",
            "body": f"""
                <p>Hi {user.first_name},</p>
                <p>We noticed you haven't used ResumeGuru in a while. We miss you! Log back in to make the most of your subscription.</p>
                <p>Best regards,<br>ResumeGuru Team</p>
            """,
        }

    html_content = wrap_in_template(email_content["body"])
    subject = email_content["subject"]

    send_email(
        to_email=user.email,
        subject=subject,
        message="",
        html_content=html_content,
        from_email="ResumeGuru Support <support@resumeguru.pro>",
    )


@shared_task
def send_satisfaction_survey():
    recent_period = timezone.now() - timedelta(days=1)
    notification_interval = timedelta(days=30)  # Only request feedback once a month

    users = User.objects.filter(
        last_login__gte=recent_period,
    )

    for user in users:
        # Check if a notification was sent within the interval
        recent_notification = UserNotification.objects.filter(
            user=user,
            notification_type="feedback_request",
            sent_at__gte=timezone.now() - notification_interval,
        ).exists()

        if not recent_notification:
            send_survey_email_to_user(user)
            # Record the notification
            UserNotification.objects.create(user=user, notification_type="feedback_request")


def send_survey_email_to_user(user):
    prompt = f"""
You are Taylor R., an AI assistant for ResumeGuru. Generate an email requesting feedback from an active user.
The feedback can be given by responding to the mail or by filling the form.

Please output the email as a JSON object with the following keys:
- "subject": The subject of the email.
- "body": The HTML content of the email body.

Include personalized elements using the user's first name: {user.first_name}.

Include a link to the survey for if the user chooses to fill the form instead of responding via mail: https://resumeguru.pro/feedback

Example format:
{{
  "subject": "Your Subject Here",
  "body": "Your HTML body here"
}}

Generate only the JSON response.
"""

    try:
        email_content = async_to_sync(get_anth_chat_response)(prompt)
    except Exception as e:
        logger.error(f"Failed to generate email content: {e}")
        # Fallback content
        email_content = {
            "subject": "We value your feedback at ResumeGuru",
            "body": f"""
                <p>Hi {user.first_name},</p>
                <p>We hope you're enjoying ResumeGuru. We'd love to hear your thoughts and feedback. Please take a moment to fill out our short survey.</p>
                <p><a href="https://resumeguru.pro/feedback">Take the Survey</a></p>
                <p>Best regards,<br>ResumeGuru Team</p>
            """,
        }

    html_content = wrap_in_template(email_content["body"])
    subject = email_content["subject"]

    send_email(
        to_email=user.email,
        subject=subject,
        message="",
        html_content=html_content,
        from_email="ResumeGuru Support <support@resumeguru.pro>",
    )


@shared_task
def process_incoming_email(conversation_id):
    try:
        conversation = Conversation.objects.get(id=conversation_id)
        human_needed, assistant_message = async_to_sync(generate_personalized_email)(conversation)

        # Save the assistant's response
        assistant_message_instance = Message.objects.create(
            conversation=conversation,
            sender="system",
            content=assistant_message,
            is_incoming=False,
            # message_id will be set after sending the email
        )

        # Fetch the latest user message
        last_user_message = conversation.messages.filter(sender="user").latest("sent_at")

        # Prepare headers for threading
        headers = {}
        if last_user_message.message_id:
            headers["In-Reply-To"] = last_user_message.message_id
            headers["References"] = last_user_message.message_id

        if human_needed:
            # Send an email to the support team
            support_email_content = generate_support_team_email(conversation)
            send_email(
                to_email="resumegurupro@gmail.com",
                subject=f"Escalation Needed: Assistance Required for {conversation.email}",
                message="",
                html_content=wrap_in_template(support_email_content),
                from_email="ResumeGuru Support <support@resumeguru.pro>",
                headers=headers,
            )

            # Send an additional email to the user about the escalation
            user_escalation_message = generate_user_escalation_email(conversation)
            html_content = wrap_in_template(user_escalation_message)
            response = send_email(
                to_email=conversation.email,
                subject=f"Re: {conversation.subject}",
                message="",
                html_content=html_content,
                from_email="ResumeGuru Support <support@resumeguru.pro>",
                headers=headers,
            )
        else:
            # Send the assistant's response to the user
            html_content = wrap_in_template(assistant_message)
            response = send_email(
                to_email=conversation.email,
                subject=f"Re: {conversation.subject}",
                message="",
                html_content=html_content,
                from_email="ResumeGuru Support <support@resumeguru.pro>",
                headers=headers,
            )

        # Extract and store the Message-ID of the sent email
        sent_message_id = response.headers.get("Message-ID")
        if sent_message_id:
            assistant_message_instance.message_id = sent_message_id
            assistant_message_instance.save()

        logger.info(f"Processed and sent email for conversation {conversation_id}")

    except Conversation.DoesNotExist:
        logger.error(f"Conversation with id {conversation_id} not found")
    except ValidationError as e:
        logger.error(f"Validation error in process_incoming_email: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in process_incoming_email: {str(e)}")
