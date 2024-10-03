from django.db import models

from accounts.models import User


class Feedback(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="feedbacks", null=True, blank=True
    )
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback from {self.email} at {self.received_at}"


class Conversation(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="conversations", null=True, blank=True
    )
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Conversation with {self.email} - {self.subject}"


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    message_id = models.CharField(max_length=255, null=True, blank=True)
    sender = models.CharField(max_length=255)  # 'user' or 'system'
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_incoming = models.BooleanField(default=True)  # True if received, False if sent

    def __str__(self):
        return f"Message from {self.sender} at {self.sent_at}"


class Attachment(models.Model):
    message = models.ForeignKey("Message", related_name="attachments", on_delete=models.CASCADE)
    file = models.FileField(upload_to="attachments/%Y/%m/%d/")
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
