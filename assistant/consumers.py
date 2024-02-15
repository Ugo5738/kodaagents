import json
import time
import uuid
from datetime import datetime

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

from assistant.knowledge_vec import query_vec_database
from assistant.memory import BaseMemory
from assistant.models import Conversation
from assistant.tasks import save_conversation
from assistant.utils import convert_markdown_to_html
from koda.config.base_config import openai_client as client
from koda.config.logging_config import configure_logger

logger = configure_logger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """
    ChatConsumer handles WebSocket connections for chat rooms, managing user messages,
    chatbot responses, and conversation state.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def connect(self):
        """
        Handles a new WebSocket connection, joining the user to the appropriate chat room,
        and initializing the conversation state.
        """
        logger.info("---------- CONNECTION ATTEMPT RECEIVED ----------")

        # Generate a unique ID for the conversation
        self.room_name = str(uuid.uuid4())
        self.room_group_name = f"chat_{self.room_name}"

        self.conversation_memory = BaseMemory()

        # Create the Conversation instance without setting the customer and channel
        self.conversation = await database_sync_to_async(Conversation.objects.create)()

        # Initialize the conversation start time
        self.conversation_memory.session_start_time = datetime.now()
        logger.info(
            f"Conversation start time: {self.conversation_memory.session_start_time}"
        )

        # Send message to room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        logger.info("---------- CONNECTION DISCONNECTED ----------")
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        logger.info("---------- MESSAGE RECEIVED ----------")

        text_data_json = json.loads(text_data)
        message_type = text_data_json.get("type")

        try:
            logger.info(f"MESSAGE TYPE: {message_type}")

            if message_type == "user_message":
                start = time.time()
                self.user_id = text_data_json.get("userId")
                user_message = text_data_json.get("message")
                message_id = str(uuid.uuid4())

                self.conversation_memory.add_message(
                    role="user", content=user_message, message_id=message_id
                )

                bot_response = "bot_message"  # replace this when ready
                logger.info(bot_response)

                stop = time.time()
                duration = stop - start

                # Add to the conversation tracker
                judy_response_id = str(uuid.uuid4())
                self.conversation_memory.add_message(
                    role="assistant",
                    content=bot_response,
                    duration=duration,
                    message_id=judy_response_id,
                )

                logger.info(f"RESPONSE DURATION: {duration}")

                # Send message to room group
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat_message",
                        "message": bot_response,
                        "messageId": message_id,
                    },
                )

            elif message_type == "upvote":
                message_id = text_data_json.get("messageId")
                self.conversation_memory.upvote(message_id)
                logger.info(f"MESSAGE {message_id} UPVOTED!")

            elif message_type == "downvote":
                message_id = text_data_json.get("messageId")
                self.conversation_memory.downvote(message_id)
                logger.info(f"MESSAGE {message_id} DOWNVOTED!")

            # not in use
            # elif message_type == "end_session":
            #     logger.info(f"---------- CONVERSATION ENDED ----------")
            #     self.username_id = text_data_json.get("userId")
            #     self.email = text_data_json.get("email")
            #     self.name = text_data_json.get("name")
            #     self.role = text_data_json.get("role")
            #     self.user_detail = [self.username_id, self.email, self.name, self.role]
            #     await self.end_conversation()

            # # Send message to room group
            # await self.channel_layer.group_send(
            #     self.room_group_name,
            #     {
            #         "type": "chat_message",
            #         "message": "session_ended",
            #     },
            # )

        except json.JSONDecodeError:
            logger.error("Received invalid JSON data")
            return
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while processing the received data: {str(e)}"
            )
            return

    # Receive message from room group
    async def chat_message(self, event):
        """
        Receives a message from the room group and sends it to the WebSocket.
        """
        # logger.info("---------- FORWARDING BOT MESSAGE ----------")

        message = event.get("message")
        message_id = event.get("messageId")

        json_message = json.dumps({"message": message, "messageId": message_id})

        # logger.info(f"MESSAGE TO WEBSOCKET: ")
        # logger.info(f"{json_message}")

        # Send message to WebSocket
        await self.send(text_data=json_message)

    # ----------------------- CUSTOM ASYNC FUNCTIONS --------------------------
    async def get_interpreter_result(self, user_message):
        logger.info("---------- BOT ENGINE STARTED ----------")

        interpreter.auto_run = True
        response = interpreter.chat(user_message)

        logger.info("---------- BOT ENGINE STOPPED ----------")

        return response

    async def end_conversation(self):
        self.conversation = await database_sync_to_async(Conversation.objects.create)()
        self.conversation_memory.session_end_time = datetime.now()
        conversation_memory_dict = self.conversation_memory.to_dict()
        save_conversation.apply_async(
            args=[
                conversation_memory_dict,
                str(self.conversation.id),
                self.user_detail,
                "learn",
            ]
        )

        return "Done!"

    # ----------------------- CUSTOM ASYNC FUNCTIONS --------------------------
