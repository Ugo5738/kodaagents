import asyncio
import base64
import re
from email.mime.text import MIMEText
from typing import Dict, List, Tuple

import requests
from asgiref.sync import async_to_sync, sync_to_async
from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from accounts.models import GoogleToken
from koda.config.logging_config import configure_logger
from resume.utils.util_funcs import get_anth_chat_response

logger = configure_logger(__name__)


def get_gmail_service():
    # Retrieve stored credentials
    google_token = GoogleToken.objects.filter(
        scopes__contains="https://www.googleapis.com/auth/gmail.send"
    ).first()

    if not google_token:
        raise Exception("No Gmail token found. Please authenticate first.")

    creds = Credentials.from_authorized_user_info(
        {
            "token": google_token.access_token,
            "refresh_token": google_token.refresh_token,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "scopes": google_token.get_scopes(),
            "expiry": google_token.expires_at.isoformat(),
        }
    )

    if creds.expired:
        try:
            creds.refresh(Request())
            google_token.access_token = creds.token
            google_token.expires_at = timezone.now() + timezone.timedelta(seconds=creds.expiry)
            google_token.save()
        except Exception as e:
            raise Exception(f"Failed to refresh token: {str(e)}")

    return build("gmail", "v1", credentials=creds)


def gmail_send_message(to, subject, body):
    try:
        service = get_gmail_service()
        google_token = GoogleToken.objects.first()
        if google_token is None:
            raise ValueError("No Gmail token found")

        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        message["from"] = google_token.email
        create_message = {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode()}

        sent_message = service.users().messages().send(userId="me", body=create_message).execute()
        print(f'Sent message to {to} Message Id: {sent_message["id"]}')
        return True
    except HttpError as error:
        print(f"An HTTP error occurred: {error}")
        return False
    except Exception as error:
        print(f"An error occurred: {error}")
        return False


def send_verification_email(to_email, verification_link):
    html_content = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f4f4f8;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <img src="https://kodastorage1.s3.amazonaws.com/static/logos/resumelogo.png" alt="ResumeGuru Logo" style="display: block; margin: 0 auto; max-width: 200px;">
        <h2 style="color: #4f46e5;">Welcome to ResumeGuru!</h2>
        <p>Hello,</p>
        <p>Thank you for registering with ResumeGuru. We're excited to have you on board! To get started, please verify your email address by clicking the button below:</p>
        <p style="text-align: center;">
            <a href="{verification_link}" style="background-color: #4f46e5; color: white; padding: 14px 20px; text-align: center; text-decoration: none; display: inline-block; border-radius: 4px; font-weight: bold; transition: background-color 0.3s;">Verify Your Email</a>
        </p>
        <p>If the button doesn't work, you can also copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #4f46e5;">{verification_link}</p>
        <p>If you didn't create an account with ResumeGuru, please ignore this email.</p>
        <p>Best regards,<br>The ResumeGuru Team</p>
    </div>
    <div style="text-align: center; padding-top: 20px; font-size: 12px; color: #666;">
        <p>© 2024 ResumeGuru. All rights reserved.</p>
        <p>
            <a href="#" style="color: #4f46e5; text-decoration: none;">Terms of Service</a> |
            <a href="#" style="color: #4f46e5; text-decoration: none;">Privacy Policy</a>
        </p>
    </div>
</body>
</html>
"""
    return requests.post(
        f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages",
        auth=("api", settings.MAILGUN_API_KEY),
        data={
            "from": "ResumeGuru Support <support@resumeguru.pro>",
            "to": [to_email],
            "subject": "Verify your email",
            "text": f"Please click this link to verify your email: {verification_link}",
            "html": html_content,
        },
    )


def send_payment_confirmation_email(payment):
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #4A4A4A;">Payment Confirmation</h2>
            <p>Your payment has been successfully processed:</p>
            <ul>
                <li><strong>Reference:</strong> {payment.reference}</li>
                <li><strong>Amount:</strong> {payment.amount} {payment.currency}</li>
                <li><strong>Date:</strong> {payment.created_at}</li>
            </ul>
            <p>Thank you for your payment!</p>
        </div>
    </body>
    </html>
    """
    return requests.post(
        f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages",
        auth=("api", settings.MAILGUN_API_KEY),
        data={
            "from": "ResumeGuru Payments <payments@resumeguru.pro>",
            "to": [payment.user.email],
            "subject": f"Payment Confirmation - {payment.reference}",
            "text": f"Your payment of {payment.amount} {payment.currency} has been processed successfully. Reference: {payment.reference}",
            "html": html_content,
        },
    )


def send_payment_notification_email(payment):
    html_content = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #4A4A4A;">New Payment Received</h2>
        <p>A new payment has been successfully processed:</p>
        <ul>
            <li><strong>Reference:</strong> {payment.reference}</li>
            <li><strong>Amount:</strong> {payment.amount} {payment.currency}</li>
            <li><strong>User:</strong> {payment.user.email}</li>
            <li><strong>Status:</strong> {payment.status}</li>
            <li><strong>Date:</strong> {payment.created_at}</li>
        </ul>
        <p>Please login to the admin panel for more details.</p>
    </div>
</body>
</html>
"""
    return requests.post(
        f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages",
        auth=("api", settings.MAILGUN_API_KEY),
        data={
            "from": "ResumeGuru Payments <payments@resumeguru.pro>",
            "to": ["resumegurupro@gmail.com"],
            "subject": f"New Payment Received - {payment.reference}",
            "text": f"New payment received. Reference: {payment.reference}, Amount: {payment.amount} {payment.currency}, User: {payment.user.email}, Status: {payment.status}, Date: {payment.created_at}",
            "html": html_content,
        },
    )


def send_subscription_status_email(email, status):
    subject_map = {
        "created": "Welcome to ResumeGuru.Pro!",
        "cancelled": "Your Subscription Has Been Cancelled",
        "payment_failed": "Subscription Payment Failed",
    }

    message_map = {
        "created": "Welcome onboard ResumeGuru.pro. Build your best resumes and get your dream job",
        "cancelled": "Your subscription has been cancelled. We hope you'll consider rejoining in the future.",
        "payment_failed": "We were unable to process your subscription payment. Please update your payment method to continue your service.",
    }

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #4A4A4A;">{subject_map[status]}</h2>
            <p>{message_map[status]}</p>
            <p>If you have any questions, please don't hesitate to contact our support team.</p>
        </div>
    </body>
    </html>
    """

    return requests.post(
        f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages",
        auth=("api", settings.MAILGUN_API_KEY),
        data={
            "from": "ResumeGuru Support <support@resumeguru.pro>",
            "to": [email],
            "subject": subject_map[status],
            "text": message_map[status],
            "html": html_content,
        },
    )


def wrap_in_template(content):
    return f"""
<html>
<head>
    <style>
        /* Add responsive styles */
        @media only screen and (max-width: 600px) {{
            .content {{
                padding: 10px !important;
            }}
        }}
    </style>
</head>
<body style="margin: 0; padding: 0; background-color: #f6f6f6;">
    <table width="100%" bgcolor="#f6f6f6" cellpadding="0" cellspacing="0">
        <tr>
            <td>
                <table align="center" width="600" bgcolor="#ffffff" class="content" style="margin: 20px auto; padding: 20px; border-radius: 10px;">
                    <tr>
                        <td style="text-align: center;">
                            <img src="https://kodastorage1.s3.amazonaws.com/static/logos/resumelogo.png" alt="ResumeGuru" style="width: 150px; margin-bottom: 20px;">
                        </td>
                    </tr>
                    <tr>
                        <td>
                            {content}
                        </td>
                    </tr>
                    <tr>
                        <td style="text-align: center; color: #888888; font-size: 12px; padding-top: 30px;">
                            <p>© {timezone.now().year} ResumeGuru. All rights reserved.</p>
                            <p>
                                <a href="https://resumeguru.pro/terms" style="color: #4f46e5; text-decoration: none;">Terms of Service</a> |
                                <a href="https://resumeguru.pro/terms" style="color: #4f46e5; text-decoration: none;">Privacy Policy</a>
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""


async def generate_personalized_email(conversation, user_message: str = None) -> Tuple[bool, str]:
    """
    Uses the Anthropic API to generate a personalized email response.

    Args:
        conversation: The conversation object containing message history.
        user_message: Optional latest user message if not yet added to conversation.

    Returns:
        A tuple containing (human_needed: bool, assistant_message: str)

    Raises:
        ValidationError: If the API response is invalid.
    """
    # Construct the conversation history
    messages = await sync_to_async(list)(conversation.messages.all().order_by("sent_at"))
    chat_history = [
        {"role": "user" if msg.is_incoming else "assistant", "content": msg.content}
        for msg in messages
    ]

    if user_message:
        chat_history.append({"role": "user", "content": user_message})

    prompt = create_prompt(chat_history, conversation.email, conversation.subject)

    try:
        response = await get_anth_chat_response(prompt)

        if (
            not isinstance(response, dict)
            or "human_needed" not in response
            or "body" not in response
        ):
            raise ValidationError("Invalid response format from API")

        return response["human_needed"], response["body"]
    except Exception as e:
        logger.error(f"Error in generate_personalized_email: {str(e)}")
        raise ValidationError("An error occurred while generating the email")


def create_prompt(chat_history: List[Dict[str, str]], user_email: str, subject: str) -> str:
    history = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in chat_history])

    return f"""
    You are Taylor R., a helpful customer success assistant for ResumeGuru. Your role is to provide professional, friendly, and informative responses to user inquiries about ResumeGuru's services. You are capable of handling multi-turn conversations and maintaining context throughout the interaction.

    User Email: {user_email}
    Subject: {subject}

    About ResumeGuru:
    - AI-powered platform for resume optimization and cover letter creation
    - Tailors resumes to specific job postings
    - Dashboard URL (to manage all documents): https://resumeguru.pro/dashboard
    - Login URL: https://resumeguru.pro/login
    
    Guidelines:
    1. Analyze the entire conversation history to understand the context and user's needs.
    2. If you can fully address the user's query:
       - Provide a helpful, concise response that directly addresses the latest user message while considering the full context
       - The only services of ResumeGuru are the one mentioned above and nothing else. 
       - Use HTML formatting for the email body
       - Include appropriate indigo-colored buttons or links when relevant
       - Sign off with your name, as you're part of the ResumeGuru team
    3. If the user makes a suggestion or the query requires human assistance at any point:
       - Set 'human_needed' to true
       - In the 'body', create a summary for the ResumeGuru team, including:
         * User's email and subject
         * Brief overview of the issue
         * Relevant parts of the conversation history
         * Any additional context that might help the team address the issue
    4. Maintain a consistent tone and personality throughout the conversation.
    5. If the user refers to something mentioned earlier in the conversation, acknowledge it and provide context-aware responses.

    CONVERSATION HISTORY:
    {history}

    Respond in the following JSON format:
    {{
      "human_needed": boolean,
      "body": "Your HTML formatted email body here"
    }}

    Ensure your response is valid JSON. The 'body' field should contain properly escaped HTML.
    """


def convert_newlines_to_html(text):
    # Convert newlines to <br> tags and wrap paragraphs
    paragraphs = text.split("\n\n")
    formatted_paragraphs = ["<p>" + p.replace("\n", "<br>") + "</p>" for p in paragraphs]
    return "".join(formatted_paragraphs)


def generate_user_escalation_email(conversation):
    messages = conversation.messages.order_by("sent_at").all()
    conversation_history = []

    for msg in messages:
        sender = "User" if msg.sender == "user" else "ResumeGuru (Taylor R.)"
        content = convert_newlines_to_html(msg.content)
        conversation_history.append(f"<p><strong>{sender}:</strong> {content}</p>")

    prompt = f"""
    Create an HTML email to inform the user that their request has been escalated to our specialized team. 
    The email should be reassuring and professional. Include the following details:

    User Email: {conversation.email}
    Subject: {conversation.subject}
    
    Conversation history:
    {"".join(conversation_history)}

    Key points to include:
    1. Acknowledgment of their inquiry
    2. Assurance that a specialized team member will review their request
    3. Expected timeframe for a response (e.g., within 24-48 hours)
    4. Appreciation for their patience
    5. Signature from Taylor R., ResumeGuru Support Team

    Respond in the following JSON format:
    {{
      "body": "Your HTML formatted email body here"
    }}

    Ensure your response is valid JSON. The 'body' field should contain properly escaped HTML.
    """

    try:
        response = async_to_sync(get_anth_chat_response)(prompt)
        return response["body"]
    except Exception as e:
        logger.error(f"Error generating user escalation email: {str(e)}")
        # Fallback to a simple escalation message
        return "<html><body><p>Your request has been escalated to our specialized team. We'll get back to you soon.</p></body></html>"


def generate_support_team_email(conversation):
    messages = conversation.messages.order_by("sent_at").all()
    conversation_history = []

    for msg in messages:
        if msg.sender == "user":
            sender = "User"
        else:
            sender = "ResumeGuru (Taylor R.)"
        content = convert_newlines_to_html(msg.content)

        if msg.attachments.exists():
            attachments_info = (
                "<ul>"
                + "".join(
                    f'<li><a href="{build_attachment_url(attachment)}">{attachment.filename}</a></li>'
                    for attachment in msg.attachments.all()
                )
                + "</ul>"
            )
            content += f"<p><strong>Attachments:</strong>{attachments_info}</p>"

        conversation_history.append(f"<p><strong>{sender}:</strong> {content}</p>")

    email_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .message {{ margin-bottom: 15px; }}
            .user {{ background-color: #f0f0f0; padding: 10px; }}
            .resumeguru {{ background-color: #e6f3ff; padding: 10px; }}
        </style>
    </head>
    <body>
        <h2>Support Team Escalation</h2>
        <p><strong>User Email:</strong> {conversation.email}</p>
        <p><strong>Subject:</strong> {conversation.subject}</p>
        <h3>Issue Overview:</h3>
        <p>The user requires assistance with their request that could not be automatically resolved.</p>
        <h3>Relevant Conversation History:</h3>
        {"".join(conversation_history)}
        <p>Reach out to the user to gather more detailed information about their experience. Offer personalized assistance to address their concerns and improve their satisfaction with our service.</p>
    </body>
    </html>
    """
    return email_content


def build_attachment_url(attachment):
    # Assuming you have a view to serve the attachment
    return settings.SITE_URL + reverse("serve_attachment", args=[attachment.id])


def send_email(to_email, subject, message, html_content, from_email, headers=None):
    data = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "text": message,
        "html": html_content,
    }

    # Include custom headers
    if headers:
        for header_name, header_value in headers.items():
            data[f"h:{header_name}"] = header_value

    return requests.post(
        f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages",
        auth=("api", settings.MAILGUN_API_KEY),
        data=data,
    )


def list_stored_messages():
    base_url = f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}"
    auth = ("api", settings.MAILGUN_API_KEY)

    # Get the list of stored messages
    response = requests.get(f"{base_url}/events", auth=auth, params={"event": "stored"})

    if response.status_code != 200:
        print(f"Failed to retrieve messages: {response.text}")
        return

    messages = response.json()["items"]

    # List each message
    for message in messages:
        print(f"Message ID: {message['storage']['key']}")
        print(f"Subject: {message.get('message', {}).get('headers', {}).get('subject', 'N/A')}")
        print(f"From: {message.get('message', {}).get('headers', {}).get('from', 'N/A')}")
        print(f"To: {message.get('message', {}).get('headers', {}).get('to', 'N/A')}")
        print(f"Date: {message.get('timestamp')}")
        print("---")


def extract_recent_message(body_plain):
    """
    Extracts the most recent message from an email thread by removing quoted sections.
    This version handles plain text emails.
    """
    # Regex to identify the start of quoted email trail (commonly found patterns)
    quoted_message_pattern = (
        r"(On\s.+?wrote:|^>|\n>|\n-----Original Message-----|\n__|\nFrom:|\nSent:)"
    )
    split_body = re.split(quoted_message_pattern, body_plain, flags=re.IGNORECASE)
    return split_body[0].strip()  # Return the first part, which is the most recent message


def extract_recent_html_message(body_html):
    """
    Extracts the most recent message from an HTML email thread by removing quoted sections.
    This version handles HTML emails.
    """
    # Remove quoted content based on patterns or blockquote tags
    cleaned_body = re.sub(r'<div class="gmail_quote">.*', "", body_html, flags=re.DOTALL)
    return cleaned_body.strip()
