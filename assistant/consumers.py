import json
import time
import uuid
from datetime import datetime

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from koda.config.base_config import openai_client as client
from koda.config.logging_config import configure_logger
from django.conf import settings

from assistant.knowledge_vec import query_vec_database
from assistant.memory import BaseMemory
from assistant.models import Conversation
from assistant.tasks import save_conversation
from assistant.utils import convert_markdown_to_html

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

                contexts = await query_vec_database(query=user_message, num_results=3)
                context_parts = []

                for idx, ctx in enumerate(contexts, start=1):
                    context_text = ctx["metadata"]["text"]
                    context_parts.append(f"Context {idx}:\n\n{context_text}")
                context_combined = "\n\n".join(context_parts)

                # Build the prompt with the retrieved contexts
                refined_ques = (
                    "Use the detailed information provided in the contexts to formulate a comprehensive and accurate response to the user's question. "
                    # "Incorporate any relevant details seamlessly, as if drawing from a deep well of knowledge. "
                    "If there is additional pertinent information not covered by the contexts that you know would enrich the answer, feel free to include it. "
                    "In cases where a context includes a reference URL, present it as a clickable link that opens in a new tab or window, ensuring a smooth conversation flow. Here is a sample [here](https://www.link.com) (link opens in a new tab)"
                    "Remember, your responses should be engaging and come across as if they're from a knowledgeable and informed guide, with a touch of your unique personality, without explicitly stating the use of provided contexts. "
                    "Focus on delivering a response that is thorough, informative, and engaging. And make your response easily formatable with dangerouslySetInnerhtml\n\n"
                    "Contexts:\n\n"
                    + context_combined
                    + "\n\n---\n\nQuestion: "
                    + user_message
                    + "\n\nAnswer:"
                )

                self.conversation_memory.add_message(
                    role="user", content=refined_ques, message_id=message_id
                )

                bot_response = await self.generate_bot_response(refined_ques)
                # logger.info(bot_response)

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

            elif message_type == "end_session":
                logger.info(f"---------- CONVERSATION ENDED ----------")
                self.username_id = text_data_json.get("userId")
                self.email = text_data_json.get("email")
                self.name = text_data_json.get("name")
                self.role = text_data_json.get("role")
                self.user_detail = [self.username_id, self.email, self.name, self.role]
                await self.end_conversation()

                # Send message to room group
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat_message",
                        "message": "session_ended",
                    },
                )

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
    async def generate_bot_response(self, user_message):
        logger.info("---------- BOT ENGINE STARTED ----------")

        full_history = self.conversation_memory.get_openai_history()

        # logger.info(f"CONVERSATION MEMORY: ")
        # logger.info(full_history)

        # Make a copy and remove the most recent message (presumably the user's latest question)
        history_except_last = full_history[
            :-1
        ]  # RECTIFY: this should be the latest context not latest question

        SYSTEM_PROMPT = """You are Judy which is short for Job Buddy, an AI Licensing Guide with a fun personality, tailored for medical professionals. Your role is to facilitate the licensing process and assist those looking to work in the medical field in Canada or other countries. Judy is knowledgeable, approachable, and has a flair for making conversations lively and enjoyable. Use conversational language, sprinkle in a touch of humor where appropriate, but always keep it professional.
            When you encounter general queries like 'I want a job', engage the user with clarifying questions to pinpoint their specific needs. For instance, you might respond, 'Oh great! What kind of job are you looking for? Which province are you interested in, or would you like an overview of all regions?'. Such interactions should feel like chatting with a well-informed friend who's eager to help.
            If a user's question pertains to licensing or immigration, and they could benefit from extra assistance, subtly direct them to the ER support team. You can say, 'For more in-depth help with licensing or immigration, the ER support team is super helpful! Check them out [here](https://www.er-support-link.com) - they’re pros at this stuff!'
            Additionally, when the conversation requires detailed knowledge about regulatory and licensing bodies in Canada, utilize the information from your knowledge base accurately and effectively. Feel free to add extra, relevant information to the context you retrieve, ensuring your responses are not just informative but also tailored and engaging.
            Your goal is to make every interaction with users informative, personal, and enjoyable, balancing your unique personality with the depth of knowledge you provide.
        """

        messages = [{"role": "system", "content": SYSTEM_PROMPT}, *full_history]

        judy_response = await self.single_bot_query(messages)

        # Convert Markdown (including handling for newlines) to HTML, then sanitize
        processed_message_html = await convert_markdown_to_html(judy_response)

        logger.info("---------- BOT ENGINE STOPPED ----------")

        return processed_message_html

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

    async def single_bot_query(self, messages):
        response = client.chat.completions.create(
            model="gpt-4-1106-preview", messages=messages
        )
        return response.choices[0].message.content

    # ----------------------- CUSTOM ASYNC FUNCTIONS --------------------------
