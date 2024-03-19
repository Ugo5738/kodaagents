import json
import time

import textstat as textstat_analysis
from channels.layers import get_channel_layer
from spellchecker import SpellChecker
from textblob import TextBlob

from koda.config.logging_config import configure_logger
from resume.utils.openai_utils import get_chat_response

logger = configure_logger(__name__)


# =========================== ANALYSIS FUNCTIONS ===========================
class Readablity:
    def __init__(self, text):
        self.text = text

    async def analyze_readability(self):
        self.complexity_score = textstat_analysis.flesch_kincaid_grade(self.text)
        self.readability_score = textstat_analysis.flesch_reading_ease(self.text)
        return self.complexity_score, self.readability_score

    async def get_readability_text(self, doc_type):
        start_time = time.time()
        await self.analyze_readability()

        feedback = "Readability:\n"
        if self.complexity_score >= 12:
            feedback += f"- Your {doc_type} has a Flesch-Kincaid Grade Level of {self.complexity_score}, indicating a collegiate reading level. Consider simplifying the language for broader accessibility.\n\n"
        else:
            feedback += f"- Your {doc_type} has a Flesch-Kincaid Grade Level of {self.complexity_score}, indicating it's suitable for a wide range of readers. Good job!\n\n"

        if self.readability_score <= 60:
            feedback += f"- Your {doc_type} has a Flesch Reading Ease score of {self.readability_score}, which is considered difficult to read. Consider simplifying the language.\n\n"
        else:
            feedback += f"- Your {doc_type} has a Flesch Reading Ease score of {self.readability_score}, which is considered easy to read. Good job!\n\n"

        total = time.time() - start_time
        logger.info(f"Readability Response Time: {total}")

        return feedback


class Polarity:
    def __init__(self, text):
        self.text = text

    async def analyze_sentiment(self):
        logger.info(f"----------------------- TONE (POLARITY) -----------------------")

        analysis = TextBlob(self.text)
        self.polarity = analysis.sentiment.polarity

        # logger.info(f"{self.polarity}")

        return self.polarity

    async def get_polarity_text(self, doc_type):
        start_time = time.time()

        await self.analyze_sentiment()
        feedback = "Sentiment Analysis:\n"
        if self.polarity < 0:
            feedback += f"- The tone of your {doc_type} is more negative (polarity: {self.polarity}). Consider revising to convey a more positive or neutral tone.\n\n"
        else:
            feedback += f"- The tone of your {doc_type} is positive or neutral (polarity: {self.polarity}). Good job!\n\n"

        total = time.time() - start_time
        logger.info(f"Polarity Response Time: {total}")

        return feedback


async def check_grammar_and_spelling(text):
    logger.info(
        f"----------------------- GRAMMAR & SPELLING CORRECTIONS -----------------------"
    )

    spell = SpellChecker()
    misspelled = spell.unknown(text.split())
    corrections = {word: spell.correction(word) for word in misspelled}

    logger.info(f"{corrections}")

    return corrections


async def review_tone(doc_type, text):
    start_time = time.time()

    logger.info(f"----------------------- TONE REVIEW -----------------------")

    instruction = f"""
    Review the following {doc_type} based on professionalism, assertiveness, and compassion:

    Provide feedback on each of these aspects.
    """
    tone_feedback = await get_chat_response(instruction, text)

    feedback_title = "Tone Review:\n"
    final_feedback = feedback_title + tone_feedback

    # logger.info(ff"{final_feedback}")

    total = time.time() - start_time
    logger.info(f"Tone Review Response Time: {total}")
    return final_feedback


async def resume_sections_feedback(doc_text):
    start_time = time.time()

    logger.info(
        f"----------------------- RESUME SECTIONS REVIEW -----------------------"
    )

    instruction = f"""
    You are a professional recruiter. Review each resume section based on professionalism, assertiveness, compassion and impact where necessary and provide constructive feedback to help in improving the resume:
    """

    resume_feedback = await get_chat_response(
        instruction, doc_text, doc_type="R-sections-fb"
    )

    feedback_title = "RESUME Review:\n"
    final_feedback = feedback_title + json.dumps(resume_feedback)

    logger.info(f"{final_feedback}")

    total = time.time() - start_time
    logger.info(f"Resume Review Response Time: {total}")
    return final_feedback


# =========================== ANALYSIS FUNCTIONS ===========================


# =========================== DOCUMENT CREATION ===========================
async def send_content_to_group(self, group_name, content):
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        group_name,
        {
            "type": "document.creation",
            "message": content,
        },
    )


async def create_cover_letter(
    group_name=None, resume_content=None, job_post_content=None
):
    start_time = time.time()
    logger.info(
        "----------------------- COVER LETTER CREATION STARTED -----------------------"
    )

    if job_post_content:
        if resume_content:
            doc_type_1 = "cover_letter"
            doc_type_2 = "job post and resume"
            doc_content = f"{job_post_content}\n\n{resume_content}"

    instruction = f"""
    Create a {('tailored ' if job_post_content else '')}{doc_type_1} using the {doc_type_2} provided.
    """

    content = f"""
    {doc_type_2.upper()} PROVIDED:
    {doc_content}

    Please ensure the {doc_type_1} is professional and tailored to the job description provided, if applicable.
    """

    created_content = await get_chat_response(
        instruction, content, doc_type=doc_type_1.upper()
    )

    logger.info(
        f"----------------------- CREATED {doc_type_1.upper()} -----------------------"
    )
    logger.info(f"{created_content}")

    await send_content_to_group(
        group_name, {"type": "document.creation", "data": created_content}
    )

    total = time.time() - start_time
    logger.info(f"Cover Letter Creation Response Time: {total}")
    # return created_content


async def create_docs(group_name=None, resume_content=None, job_post_content=None):
    start_time = time.time()
    logger.info("----------------------- DOC CREATION STARTED -----------------------")

    if job_post_content:
        if resume_content:
            doc_type_1 = "resume"
            doc_type_2 = "job post and resume"
            doc_content = f"{job_post_content}\n\n{resume_content}"
            await create_cover_letter(
                group_name=group_name,
                resume_content=resume_content,
                job_post_content=job_post_content,
            )
        else:
            # Fallback if only job_post_content is provided without specific direction
            doc_type_1 = "document"
            doc_type_2 = "job post"
            doc_content = job_post_content
    elif resume_content:
        doc_type_1 = "resume"
        doc_type_2 = "resume content"
        doc_content = resume_content
    else:
        logger.error("No valid content provided for document creation.")
        return "Error: No content provided."

    instruction = f"""
    Create a {('tailored ' if job_post_content else '')}{doc_type_1} using the {doc_type_2} provided.
    """

    content = f"""
    {doc_type_2.upper()} PROVIDED:
    {doc_content}

    Please ensure the {doc_type_1} is professional and tailored to the job description provided, if applicable.
    """

    created_content = await get_chat_response(
        instruction, content, doc_type=doc_type_1.upper()
    )

    logger.info(
        f"----------------------- CREATED {doc_type_1.upper()} -----------------------"
    )
    logger.info(f"{created_content}")

    total = time.time() - start_time
    logger.info(f"Doc Creation Response Time: {total}")
    return created_content


async def improve_doc(doc_type, doc_content, doc_feedback):
    """Optimizes a document based on its type and provided feedback.

    Args:
        doc_type (str): The type of the document (e.g., 'cover letter', 'resume', 'job post').
        content (str): The original content of the document.
        feedback (str, optional): Feedback provided for optimization. Defaults to None.

    Returns:
        str: The optimized content.
    """

    start_time = time.time()
    doc_type_upper = doc_type.upper()
    logger.info(
        f"----------------------- {doc_type_upper} OPTIMIZATION STARTED -----------------------"
    )

    instruction_base = f"Provide an optimized version of the {doc_type}."

    if doc_feedback:
        instruction = f"{instruction_base} Use the feedback provided and ensure not to miss out on any part of the document"
        content_feedback_combined = f"ORIGINAL CONTENT:\n{doc_content}\n\n{doc_type_upper} FEEDBACK:\n{doc_feedback}"
    else:
        instruction = (
            f"{instruction_base} Ensure not to miss out on any part of the document."
        )
        content_feedback_combined = f"ORIGINAL CONTENT:\n{doc_content}"

    if doc_type == "cover letter":
        optimized_content = await get_chat_response(
            instruction, content_feedback_combined, doc_type="CL"
        )
    elif doc_type == "resume":
        optimized_content = await get_chat_response(
            instruction, content_feedback_combined, doc_type="R"
        )
    elif doc_type == "job post":
        optimized_content = await get_chat_response(
            instruction, content_feedback_combined
        )

    logger.info(
        f"----------------------- FULL {doc_type_upper} FEEDBACK -----------------------"
    )
    logger.info(f"{optimized_content}")

    total = time.time() - start_time
    logger.info(f"Improved Doc Response Time: {total}")
    return optimized_content


async def customize_doc(doc_type, doc_content, custom_instruction):
    start_time = time.time()

    logger.info("----------------------- CUSTOMIZATION BEGINS -----------------------")

    instruction = f"""
    Make adjustments to the {doc_type} using the adjustment instruction provided. 
    """

    content = f"""
    ORIGINAL CONTENT:
    {doc_content}

    {doc_type.upper()} ADJUSTMENT INSTRUCTION:
    {custom_instruction}
    """

    if doc_type == "cover letter":
        optimized_content = await get_chat_response(instruction, content, doc_type="CL")
    elif doc_type == "resume":
        optimized_content = await get_chat_response(instruction, content, doc_type="R")

    logger.info(
        f"----------------------- FULL {doc_type.upper()} FEEDBACK -----------------------"
    )
    logger.info(f"{optimized_content}")

    total = time.time() - start_time
    logger.info(f"Improved Doc Response Time: {total}")
    return optimized_content


# =========================== DOCUMENT CREATION ===========================


# =========================== COLLATION ===========================
async def get_feedback_and_improve(resume_content):
    readability = Readablity(resume_content)
    readability_feedback = await readability.get_readability_text(doc_type="resume")

    sections_feedback = await resume_sections_feedback(resume_content)
    feedbacks = [readability_feedback, sections_feedback]
    resume_feedback = "\n\n".join(feedbacks)

    improved_content = await improve_doc(
        doc_type="resume",
        doc_content=resume_content,
        doc_feedback=resume_feedback,
    )
    return improved_content


# =========================== COLLATION ===========================
