import json

from django.conf import settings

from koda.config.base_config import openai_client as client
from koda.config.logging_config import configure_logger

logger = configure_logger(__name__)


async def get_tasks_from_transcript(input_text: str):
    """
    Creates to-do tasks from of conversation or meeting transcripts.
    Args:
        input_text (str): conversation or meeting transcripts.
    Returns:
        dict: Structured tasks.
    """
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant. Convert the conversation or meeting transcipt into structured tasks in JSON format.",
        },
        {"role": "user", "content": input_text},
    ]

    structured_response = await client.chat.completions.create(
        model=settings.MODEL_NAME,
        messages=messages,
        response_format={"type": "json_object"},
    )
    try:
        response = json.loads(structured_response.choices[0].message.content)
        return response
    except Exception as e:
        logger(f"An error occurred: {e}")
        return {"error": "Could not interpret transcript"}
