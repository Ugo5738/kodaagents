import base64
from email.mime.text import MIMEText

import requests
from django.conf import settings
from django.utils import timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from accounts.models import GoogleToken


def get_gmail_service():
    # Retrieve stored credentials
    google_token = GoogleToken.objects.filter(scopes__contains='https://www.googleapis.com/auth/gmail.send').first()

    if not google_token:
        raise Exception("No Gmail token found. Please authenticate first.")

    creds = Credentials.from_authorized_user_info(
        {
            "token": google_token.access_token,
            "refresh_token": google_token.refresh_token,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "scopes": google_token.get_scopes(),
            "expiry": google_token.expires_at.isoformat()
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

    return build('gmail', 'v1', credentials=creds)


def gmail_send_message(to, subject, body):
    try:
        service = get_gmail_service()
        google_token = GoogleToken.objects.first()
        if google_token is None:
            raise ValueError("No Gmail token found")

        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        message['from'] = google_token.email
        create_message = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}

        sent_message = (service.users().messages().send(userId="me", body=create_message).execute())
        print(f'Sent message to {to} Message Id: {sent_message["id"]}')
        return True
    except HttpError as error:
        print(f'An HTTP error occurred: {error}')
        return False
    except Exception as error:
        print(f'An error occurred: {error}')
        return False


def send_verification_email(to_email, verification_link):
    html_content = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <img src="https://your-logo-url.com" alt="ResumeGuru Logo" style="display: block; margin: 0 auto; max-width: 200px;">
        <h2 style="color: #4A4A4A;">Welcome to ResumeGuru!</h2>
        <p>Hello,</p>
        <p>Thank you for registering with ResumeGuru. We're excited to have you on board! To get started, please verify your email address by clicking the button below:</p>
        <p style="text-align: center;">
            <a href="{verification_link}" style="background-color: #4CAF50; color: white; padding: 14px 20px; text-align: center; text-decoration: none; display: inline-block; border-radius: 4px; font-weight: bold;">Verify Your Email</a>
        </p>
        <p>If the button doesn't work, you can also copy and paste this link into your browser:</p>
        <p>{verification_link}</p>
        <p>If you didn't create an account with ResumeGuru, please ignore this email.</p>
        <p>Best regards,<br>The ResumeGuru Team</p>
    </div>
    <div style="text-align: center; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #888;">
        <p>© 2024 ResumeGuru. All rights reserved.</p>
        <p>
            <a href="#" style="color: #888; text-decoration: none;">Terms of Service</a> |
            <a href="#" style="color: #888; text-decoration: none;">Privacy Policy</a>
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
            "html": html_content
        }
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
            "html": html_content
        }
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
            "html": html_content
        }
    )


def send_subscription_status_email(email, status):
    subject_map = {
        'created': 'Welcome to Your New Subscription!',
        'cancelled': 'Your Subscription Has Been Cancelled',
        'payment_failed': 'Subscription Payment Failed'
    }

    message_map = {
        'created': 'Your subscription has been successfully created. Thank you for joining!',
        'cancelled': 'Your subscription has been cancelled. We hope you\'ll consider rejoining in the future.',
        'payment_failed': 'We were unable to process your subscription payment. Please update your payment method to continue your service.'
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
            "html": html_content
        }
    )
