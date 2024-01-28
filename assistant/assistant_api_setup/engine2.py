import asyncio

from koda.config.base_config import openai_client as client
from django.conf import settings


class OpenAIChatEngine:
    def __init__(self):
        self.assistant_id = settings.OPENAI_ASSISTANT_ID

    async def create_thread(self):
        """Create a new conversation thread."""
        thread = client.beta.threads.create()
        return thread.id

    async def send_message(self, thread_id, message):
        """Send a message to the specified thread."""
        user_message = client.beta.threads.messages.create(
            thread_id=thread_id, role="user", content=message
        )
        return user_message

    async def run_thread(self, thread_id):
        """Run the assistant on the thread."""
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=self.assistant_id,
        )
        return run.id

    async def check_status(self, run_id, thread_id):
        """Check the status of the conversation run."""
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run_id,
        )
        return run.status

    async def get_response(self, thread_id):
        """Retrieve the response from the thread."""
        response = client.beta.threads.messages.list(thread_id=thread_id)
        if response.data:
            return response.data[0].content[0].text.value
        return ""

    async def handle_chat(self, thread_id, user_input):
        """Handle the entire chat process."""
        thread_message = await self.send_message(thread_id, user_input)
        message_id = thread_message.id

        run_id = await self.run_thread(thread_id)

        # Wait for the response
        while await self.check_status(run_id, thread_id) != "completed":
            await asyncio.sleep(1)  # Implement a more efficient waiting mechanism

        return await self.get_response(thread_id), message_id


# Example usage
# chat_engine = OpenAIChatEngine()
# final_text = chat_engine.handle_chat("Your user's initial message")
