import json
import time

from django.conf import settings
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from koda.config.base_config import openai_client as client
from koda.config.logging_config import configure_logger
from resume.utils.samples import (
    cover_letter_example_structure,
    resume_example_structure,
    resume_fb_example_structure,
)

logger = configure_logger(__name__)


async def get_chat_response(instruction, message, doc_type=None):
    start_time = time.time()

    chat = ChatOpenAI(
        temperature=0.7,
        model_name=settings.MODEL_NAME,
        openai_api_key=settings.OPENAI_API_KEY,
    )

    messages = [SystemMessage(content=instruction), HumanMessage(content=message)]

    if doc_type:
        if doc_type == "RESUME":
            structured_instruction = f"{instruction}\n\nHere is how I would like the information to be structured in JSON format:\n{resume_example_structure}\n\nIf there isn't any provided value for the required key in the json format, return None as corresponding value.\nInclude line breaks where appropriate in all the sections of the letter. Now, based on the content provided above, please structure the document content accordingly."
        elif doc_type == "R-sections-fb":
            structured_instruction = f"{instruction}\n\nHere is how I would like the information to be structured in JSON format:\n{resume_fb_example_structure}\n\nDo not miss any key value pair when creating the JSON data."
        if doc_type == "COVER_LETTER":
            structured_instruction = f"{instruction}\n\nHere is how I would like the information to be structured in JSON format:\n{cover_letter_example_structure}\n\nInclude line breaks where appropriate in all the sections of the letter. Now, based on the content provided above, please structure the document content accordingly."

        messages = [
            {"role": "system", "content": structured_instruction},
            {"role": "user", "content": message},
        ]

        structured_response = await client.chat.completions.create(
            model=settings.MODEL_NAME,
            messages=messages,
            response_format={"type": "json_object"},
        )

        response = json.loads(structured_response.choices[0].message.content)

        total = time.time() - start_time
        logger.info(f"Chat Response Time: {total}")

        return response

    response = chat(messages).content

    total = time.time() - start_time
    logger.info(f"Chat Response Time: {total}")
    return response
