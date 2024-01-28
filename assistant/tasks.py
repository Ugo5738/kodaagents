import logging
import uuid

from celery import shared_task

from accounts.models import OrganizationCustomer, OrganizationProfile, User
from assistant.memory import BaseMemory
from assistant.models import (
    Channel,
    Conversation,
    GeneralChatAnalytics,
    Message,
    MessageVote,
    Session,
)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@shared_task
def save_conversation(
    conversation_memory_dict, conversation_id, user_details, channel_name
):
    logger.info(f"---------------- SAVING CONVERSATION STARTED ---------------")
    conversation_memory = BaseMemory()
    conversation_memory.full_conversation_history = conversation_memory_dict[
        "full_conversation_history"
    ]
    conversation_memory.votes = conversation_memory_dict["votes"]
    session_start_time = conversation_memory_dict.get("session_start_time")
    session_end_time = conversation_memory_dict.get("session_end_time")

    username_id, email, name, role = user_details

    logger.info(f"CONVERSATION MEMORY: {conversation_memory}")

    # Create or find the channel
    channel, _ = Channel.objects.get_or_create(name=channel_name)
    logger.info(f"CHANNEL: {channel}")

    # Fetch the user
    user, user_created = User.objects.get_or_create(email=email, username=username_id)
    logger.info(f"USER: {user}")

    # Fetch the organization
    org_name = "Koda Client"
    org, org_created = OrganizationProfile.objects.get_or_create(name=org_name)
    logger.info(f"ORGANIZATION: {org}")

    # Fetch the customer
    customer, customer_created = OrganizationCustomer.objects.get_or_create(
        organization=org, name=name, role=role
    )
    logger.info(f"CUSTOMER: {customer}")

    # Fetch the conversation by its ID
    try:
        conversation, conversation_created = Conversation.objects.get_or_create(
            thread=conversation_id
        )
        conversation.customer = customer
        conversation.channel = channel
        conversation.status = "COMPLETED"
        conversation.save()
        logger.info(f"CONVERSATION SAVED: {conversation}")

        # Create or update GeneralChatAnalytics
        analytics, created = GeneralChatAnalytics.objects.get_or_create(
            conversation=conversation
        )
        if created:
            analytics.avg_response_time = calculate_average_response_time(
                conversation_memory.get_history()
            )
            analytics.thumbs_up = sum(
                [vote for vote in conversation_memory.votes.values() if vote > 0]
            )
            analytics.thumbs_down = sum(
                [vote for vote in conversation_memory.votes.values() if vote < 0]
            )
            analytics.save()
            logger.info(f"ANALYTICS SAVED: {analytics}")

        analytics.unique_users.add(customer)

        # Create a new Session linked to this analytics
        session = Session.objects.create(
            start_time=session_start_time,
            end_time=session_end_time,
            analytics=analytics,
        )

    except Conversation.DoesNotExist:
        logger.error("Conversation does not exist")
        return

    for message in conversation_memory.get_history():
        message_id = message.get("message_id", None)
        Message.objects.create(
            message_id=message_id,  # This will be None if 'message_id' is not in message, and a new UUID will be auto-generated.
            conversation=conversation,
            content=message["content"],
            sender=(
                "BOT" if message["role"] == "assistant" else message["role"].upper()
            ),
            timestamp=message["timestamp"],
        )
    logger.info(f"MESSAGES SAVED")

    # Save votes to MessageVote
    for message_id, vote_value in conversation_memory.votes.items():
        try:
            message = Message.objects.get(pk=message_id)
        except Message.DoesNotExist:
            logger.error(f"Message {message_id} does not exist")
            continue

        vote_type = "UP" if vote_value > 0 else "DOWN"
        MessageVote.objects.create(message=message, vote_type=vote_type)
    logger.info(f"MESSAGE VOTE SAVED")
    logger.info(f"---------------- SAVING CONVERSATION ENDED ---------------")


def calculate_average_response_time(conversation_history):
    # Initialize sum and count variables
    total_response_time = 0
    total_messages = 0

    # Loop through each message in the conversation
    for message in conversation_history:
        # Check if the role is 'assistant'
        if message["role"] == "assistant":
            # Check if 'duration' exists and is not None
            if "duration" in message and message["duration"] is not None:
                total_response_time += message["duration"]
                total_messages += 1

    # Calculate average
    if total_messages == 0:
        return 0  # To avoid division by zero
    else:
        return total_response_time / total_messages
