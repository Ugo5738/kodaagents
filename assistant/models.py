import uuid

from django.db import models
from django.utils import timezone

from accounts.models import OrganizationCustomer


class Channel(models.Model):
    name = models.CharField(max_length=255)  # "Learn" or "Recommend"
    description = models.TextField()

    def save(self, *args, **kwargs):
        self.name = self.name.lower()
        super(Channel, self).save(*args, **kwargs)

    def __str__(self):
        return self.name


class Conversation(models.Model):
    STATUS_CHOICES = [
        ("ONGOING", "Ongoing"),
        ("COMPLETED", "Completed"),
        ("ABANDONED", "Abandoned"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.CharField(
        max_length=50, unique=True, editable=False, null=True, blank=True
    )
    customer = models.ForeignKey(
        OrganizationCustomer, on_delete=models.CASCADE, null=True, blank=True
    )
    channel = models.ForeignKey(
        Channel, on_delete=models.CASCADE, null=True, blank=True
    )
    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="ONGOING")

    class Meta:
        ordering = ["-started_at"]


class Message(models.Model):
    SENDER_CHOICES = [
        ("BOT", "Bot"),
        ("USER", "User"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message_id = models.CharField(
        max_length=50, unique=True, editable=False, null=True, blank=True
    )
    conversation = models.ForeignKey(
        Conversation, related_name="messages", on_delete=models.CASCADE, db_index=True
    )
    content = models.TextField()
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["timestamp"]


class GeneralChatAnalytics(models.Model):
    conversation = models.OneToOneField(Conversation, on_delete=models.CASCADE)
    avg_response_time = models.FloatField(null=True, blank=True)
    unanswered_questions = models.IntegerField(default=0)
    failed_recommendations = models.IntegerField(default=0)
    thumbs_up = models.IntegerField(default=0)
    thumbs_down = models.IntegerField(default=0)
    unique_users = models.ManyToManyField(
        OrganizationCustomer, related_name="chat_analytics"
    )

    def __str__(self):
        return f"Analytics for {self.conversation.id}"


class Session(models.Model):
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    analytics = models.ForeignKey(
        GeneralChatAnalytics, related_name="sessions", on_delete=models.CASCADE
    )


class MessageVote(models.Model):
    VOTE_CHOICES = [
        ("UP", "Upvote"),
        ("DOWN", "Downvote"),
    ]

    message = models.ForeignKey(Message, related_name="votes", on_delete=models.CASCADE)
    vote_type = models.CharField(max_length=4, choices=VOTE_CHOICES)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["timestamp"]
