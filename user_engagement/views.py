import hashlib
import hmac

import openai
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from helpers.email_utils import extract_recent_html_message, extract_recent_message
from koda.config.logging_config import configure_logger
from user_engagement.models import Attachment, Conversation, Message
from user_engagement.serializers import FeedbackSerializer
from user_engagement.tasks import process_incoming_email

logger = configure_logger(__name__)

# Initialize OpenAI
openai.api_key = settings.OPENAI_API_KEY


class FeedbackAPIView(APIView):
    def post(self, request):
        serializer = FeedbackSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                user=request.user if request.user.is_authenticated else None,
                email=(
                    request.user.email
                    if request.user.is_authenticated
                    else request.data.get("email")
                ),
            )
            return Response(
                {"message": "Feedback submitted successfully"}, status=status.HTTP_201_CREATED
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name="dispatch")
class MailgunInboundEmailView(View):
    def post(self, request, *args, **kwargs):
        # Verify the webhook signature
        token = request.POST.get("token")
        timestamp = request.POST.get("timestamp")
        signature = request.POST.get("signature")

        # Log the incoming values
        logger.debug(
            f"Mailgun webhook received - timestamp: {timestamp}, token: {token}, signature: {signature}"
        )

        # Verify the webhook signature
        if not self.verify_mailgun_signature(token, timestamp, signature):
            logger.error("Mailgun signature verification failed.")
            return HttpResponse(status=403)
        else:
            logger.debug("Mailgun signature verification succeeded.")

        sender = request.POST.get("sender")
        subject = request.POST.get("subject")
        body_plain = request.POST.get("body-plain")
        body_html = request.POST.get("body-html")
        recipient = request.POST.get("recipient")
        message_id = request.POST.get("Message-Id") or request.POST.get("Message-ID")

        # Process attachments
        attachments = request.FILES.getlist("attachment")
        for attachment in attachments:
            handle_file_attachment(attachment)

        # Find or create the user based on the sender's email
        user = User.objects.filter(email=sender).first()

        # Find or create a conversation
        conversation, created = Conversation.objects.get_or_create(
            email=sender,
            subject=subject,
            user=user,
        )

        recent_body_plain = extract_recent_message(body_plain)
        recent_body_html = extract_recent_html_message(body_html)

        # Save the incoming message
        message = Message.objects.create(
            conversation=conversation,
            sender="user",
            content=recent_body_html,
            message_id=message_id,
        )

        # Process attachments
        attachments = request.FILES.getlist("attachment")
        for attachment in attachments:
            handle_file_attachment(attachment, message)

        # Schedule the asynchronous task
        process_incoming_email.delay(conversation.id)

        return HttpResponse(status=200)

    def verify_mailgun_signature(self, token, timestamp, signature):
        signing_key = settings.MAILGUN_WEBHOOK_SIGNING_KEY
        message = f"{timestamp}{token}".encode("utf-8")
        hmac_digest = hmac.new(
            key=signing_key.encode("utf-8"),
            msg=message,
            digestmod=hashlib.sha256,
        ).hexdigest()

        # # Log the computed digest for debugging
        # logger.debug(f"Computed HMAC digest: {hmac_digest}")
        # logger.debug(f"Provided signature: {signature}")

        is_valid = hmac.compare_digest(hmac_digest, signature)
        # logger.debug(f"Signature valid: {is_valid}")
        return is_valid


def handle_file_attachment(attachment, message):
    file_content = attachment.read()
    filename = attachment.name
    content_type = attachment.content_type
    size = attachment.size

    # Save the file using Django's FileField
    django_file = ContentFile(file_content, name=filename)

    # Create the Attachment instance
    Attachment.objects.create(
        message=message,
        file=django_file,
        filename=filename,
        content_type=content_type,
        size=size,
    )


@login_required
def serve_attachment(request, attachment_id):
    # Only allow staff or superusers to access attachments
    if not request.user.is_staff:
        return HttpResponse(status=403)

    attachment = get_object_or_404(Attachment, id=attachment_id)
    response = FileResponse(attachment.file)
    response["Content-Disposition"] = f'attachment; filename="{attachment.filename}"'
    return response
