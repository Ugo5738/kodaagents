import json
import mimetypes
import os
import re
import tempfile
import time
from enum import Enum
from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union
from uuid import uuid4

import anthropic
import boto3
import textstat as textstat_analysis
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.core.files.storage import default_storage
from langchain.schema import HumanMessage, SystemMessage
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    Docx2txtLoader,
    OnlinePDFLoader,
    PyPDFLoader,
    TextLoader,
    UnstructuredFileLoader,
)
from langchain_openai import ChatOpenAI
from sklearn.feature_extraction.text import CountVectorizer
from spellchecker import SpellChecker
from textblob import TextBlob

from koda.config.base_config import anthropic_client, openai_client
from koda.config.logging_config import configure_logger
from resume.document import generate_cover_letter_docx, generate_resume_docx
from resume.pdf_gen import generate_cv_pdf, generate_resume_pdf
from resume.samples import (
    cover_letter_improvement_instruction,
    cover_letter_optimization_instruction,
    default_cover_letter,
    resume_improvement_instruction,
    resume_optimization_instruction,
)

logger = configure_logger(__name__)


cover_letter_example_structure = json.dumps(
    {
        "name": "Full Name",
        "recipient": "Dear Hiring Manager,",
        "body": "Cover letter body text, separated into paragraphs by \\n\\n",
        "closing": "Choose an appropriate closing based on the tone and content of the letter"
    }
)


resume_fb_example_structure = json.dumps(
    {
        "contact": "Feedback on contact section",
        "summary": "Feedback on summary section",
        "experiences": {
            "experience_1": "Feedback on first experience section",
            "experience_2": "Feedback on second experience section",
            "experience_3": "Feedback on third experience section",
            # Additional education entries can be added here
        },
        "education": [
            "Feedback on first education section",
            # Additional education entries can be added here
        ],
        "skills": "Feedback on skills section",
        "certifications": [
            "Feedback on certifications section",
            # Additional certifications can be listed here
        ],
        # "projects": [
        #     "Feedback on projects section",
        #     # Additional projects can be listed here
        # ],
        "references": [
            "Feedback on references section",
            # Additional references can be added here
        ],
    },
    indent=2,
)


resume_example_structure = json.dumps(
    {
        "contact": {
            "name": "Sender Name",
            "job_title": "Job Title",
            "address": "Sender Address",
            "phone": "Sender Phone",
            "email": "Sender Email",
            "linkedIn": "LinkedIn Profile url (if available)",
        },
        "summary": "Resume Executive Summary",
        "experiences": [
            {
                "company_name": "Name of company worked for",
                "job_role": "Job Position",
                "start_date": "Start date of job",
                "end_date": "End date of job if available",
                "location": "Location of the company",
                "job_description": [
                    "First Description of Job Responsibilities and Achievements",
                    "Second Description of Job Responsibilities and Achievements",
                    "Third Description of Job Responsibilities and Achievements",
                    # Additional descriptions can be added here
                ],
            },
            {
                "company_name": "Name of company worked for",
                "job_role": "Job Position",
                "start_date": "Start date of job",
                "end_date": "End date of job if available",
                "location": "Location of the company",
                "job_description": [
                    "First Description of Job Responsibilities and Achievements",
                    "Second Description of Job Responsibilities and Achievements",
                    "Third Description of Job Responsibilities and Achievements",
                    # Additional descriptions can be added here
                ],
            },
            {
                "company_name": "Name of company worked for",
                "job_role": "Job Position",
                "start_date": "Start date of job",
                "end_date": "End date of job if available",
                "location": "Location of the company",
                "job_description": [
                    "First Description of Job Responsibilities and Achievements",
                    "Second Description of Job Responsibilities and Achievements",
                    "Third Description of Job Responsibilities and Achievements",
                    # Additional descriptions can be added here
                ],
            },
        ],
        "education": [
            {
                "institution": "Educational Institution",
                "degree": "Degree Obtained",
                "end_date": "End Date",
                "location": "Location of institution",
                "details": "Details about the Course or Achievements if available",
            },
            # Additional education entries can be added here
        ],
        "skills": [
            "Skill 1",
            "Skill 2",
            # Additional skills can be listed here
        ],
        "certifications": [
            {
                "title": "Certification Title",
                "issuing_organization": "Issuing Organization",
                "date_obtained": "Date Obtained (if applicable)",
                "validity_period": "Validity Period (if applicable)",
            },
            # Additional certifications can be listed here
        ],
        # "projects": [
        #     {
        #         "project_title": "Project Title",
        #         "duration": "Project Duration",
        #         "description": "Project Description",
        #         "technologies_used": ["Technology 1", "Technology 2"],
        #     },
        #     # Additional projects can be listed here
        # ],
        "references": [
            {
                "referee_name": "Referee Name",
                "relationship": "Relationship to the Referee",
                "contact_information": "Referee Contact Information",
            },
            # Additional references can be added here
        ],
    },
    indent=2,
)


resume_example_structure_openai = {
    "type": "object",
    "properties": {
        "contact": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "job_title": {"type": "string"},
                "address": {"type": "string"},
                "phone": {"type": "string"},
                "email": {"type": "string"},
                "linkedIn": {
                  "type": ["string", "null"],
                }
            },
            "additionalProperties": False,
            "required": ["name", "job_title", "address", "phone", "email", "linkedIn"]
        },
        "summary": {"type": "string"},
        "experiences": {
            "type": "object",
            "properties": {
                "experience_1": {
                    "type": "object",
                    "properties": {
                        "company_name": {"type": "string"},
                        "job_role": {"type": "string"},
                        "start_date": {"type": "string"},
                        "end_date": {
                          "type": ["string", "null"],
                        },
                        "location": {"type": "string"},
                        "job_description": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "additionalProperties": False,
                    "required": ["company_name", "job_role", "start_date", "end_date", "location", "job_description"]
                },
                "experience_2": {
                    "type": "object",
                    "properties": {
                        "company_name": {"type": "string"},
                        "job_role": {"type": "string"},
                        "start_date": {"type": "string"},
                        "end_date": {
                          "type": ["string", "null"],
                        },
                        "location": {"type": "string"},
                        "job_description": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "additionalProperties": False,
                    "required": ["company_name", "job_role", "start_date", "end_date", "location", "job_description"]
                },
                "experience_3": {
                    "type": "object",
                    "properties": {
                        "company_name": {"type": "string"},
                        "job_role": {"type": "string"},
                        "start_date": {"type": "string"},
                        "end_date": {
                          "type": ["string", "null"],
                        },
                        "location": {"type": "string"},
                        "job_description": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "additionalProperties": False,
                    "required": ["company_name", "job_role", "start_date", "end_date", "location", "job_description"]
                }
            },
            "additionalProperties": False,
            "required": ["experience_1", "experience_2", "experience_3"]
        },
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "institution": {"type": "string"},
                    "degree": {"type": "string"},
                    "end_date": {"type": "string"},
                    "location": {"type": "string"},
                    "details": {"type": "string"}
                },
                "additionalProperties": False,
                "required": ["institution", "degree", "end_date", "location", "details"]
            }
        },
        "skills": {
            "type": "array",
            "items": {"type": "string"}
        },
        "certifications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "issuing_organization": {"type": "string"},
                    "date_obtained": {"type": "string"},
                    "validity_period": {"type": "string"}
                },
                "additionalProperties": False,
                "required": ["title", "issuing_organization", "date_obtained", "validity_period"]
            }
        },
        "references": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "referee_name": {
                      "type": ["string", "null"],
                    },
                    "relationship": {
                      "type": ["string", "null"],
                    },
                    "contact_information": {
                      "type": ["string", "null"],
                    }
                },
                "additionalProperties": False,
                "required": ["referee_name", "relationship", "contact_information"]
            }
        }
    },
    "required": ["contact", "summary", "experiences", "education", "skills", "certifications", "references"],
    "additionalProperties": False,
}


cover_letter_example_structure_openai = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "recipient": {"type": "string"},
        "body": {"type": "string"},
        "closing": {"type": "string"}
    },
    "required": ["name", "recipient", "body", "closing"],
    "additionalProperties": False,
}


resume_fb_example_structure_openai = {
    "type": "object",
    "properties": {
        "contact": {"type": "string"},
        "summary": {"type": "string"},
        "experiences": {
            "type": "object",
            "properties": {
                "experience_1": {"type": "string"},
                "experience_2": {"type": "string"},
                "experience_3": {"type": "string"},
            }
        },
        "education": {
            "type": "array",
            "items": {"type": "string"}
        },
        "skills": {"type": "string"},
        "certifications": {
            "type": "array",
            "items": {"type": "string"}
        },
        "references": {
            "type": "array",
            "items": {"type": "string"}
        }
    }
}


job_post_keywords_example_structure = json.dumps(
    {"keywords": "List of keywords"},
    indent=2,
)


async def get_openai_chat_response(instruction, message, prompt_format):
    start_time = time.time()

    # chat = ChatOpenAI(
    #     temperature=0.9,
    #     model_name="chatgpt-4o-latest",
    #     openai_api_key=settings.OPENAI_API_KEY,
    # )

    # messages = [SystemMessage(content=instruction), HumanMessage(content=message)]

    messages = [
        {"role": "system", "content": instruction},
        {"role": "user", "content": message},
    ]

    structured_response = await openai_client.chat.completions.create(
        model="gpt-4o-2024-08-06",  # "chatgpt-4o-latest",
        messages=messages,
        response_format={
            "type": "json_schema",
            "json_schema": {
              "name": "doc_response",
              "strict": True,
              "schema": prompt_format,
            }
        },
    )

    response = json.loads(structured_response.choices[0].message.content)
    total = time.time() - start_time
    logger.info(f"Chat Response Time: {total}")

    return response


# =========================== PROP-UP FUNCTIONS ===========================
class Readability:
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
    tone_feedback = await get_openai_chat_response(instruction, text)

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

    resume_feedback = await get_openai_chat_response(
        instruction, doc_text, doc_type="R-sections-fb"
    )

    feedback_title = "RESUME Review:\n"
    final_feedback = feedback_title + json.dumps(resume_feedback)

    logger.info(f"{final_feedback}")

    total = time.time() - start_time
    logger.info(f"Resume Review Response Time: {total}")
    return final_feedback


async def get_job_post_feedback(doc_text):
    start_time = time.time()

    logger.info(f"----------------------- JOB POST REVIEW -----------------------")

    instruction = f"""
    As an experienced recruiter, review the following job post and provide detailed feedback analysis to help improve and optimize it.

    Use these considerations below in your review:
    - Enhancing SEO (Search Engine Optimization):
    - Keyword Optimization
    - Industry-Specific Terminology

    - Improving Clarity of Job Descriptions:
    - Clear Job Titles
    - Concise Job Duties
    - Required Qualifications
    """

    job_post_feedback = await get_openai_chat_response(instruction, doc_text)

    logger.info(f"{job_post_feedback}")

    total = time.time() - start_time
    logger.info(f"Job Post Review Time: {total}")
    return job_post_feedback


async def create_doc(doc_type_1, doc_type_2, doc_content, default_doc):
    start_time = time.time()

    logger.info("----------------------- DOC CREATION -----------------------")

    instruction = f"""
    Create a generic {doc_type_1} using the {doc_type_2} provided as a guide. Use \
    only the details in the provided content and not the sample given. if profile data is present ALWAYS GIVE PRIORITY TO THE APPLICANT PROFILE CONTACT AND/OR PROFILE DETAILS if present over the general document information even when there is an overlap
    """

    content = f"""
    {doc_type_2.upper()} PROVIDED:
    {doc_content}

    DOC SAMPLE:
    {default_doc}
    """

    created_content = await get_openai_chat_response(instruction, content, doc_type="CL")

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

    instruction_base = f"Your objective is to improve the quality of {doc_type}s to ensure they are professional, well-structured, and highlight the candidate's strengths and experiences.\n\n"

    if doc_type == "resume":
        instruction_base = instruction_base + resume_improvement_instruction
    elif doc_type == "cover letter":
        instruction_base = instruction_base + cover_letter_improvement_instruction

    if doc_feedback:
        instruction = f"{instruction_base} \n\nEnsure you use the feedback provided to improve the document"
        content_feedback_combined = f"ORIGINAL CONTENT:\n{doc_content}\n\n{doc_type_upper} FEEDBACK:\n{doc_feedback}"
    else:
        content_feedback_combined = f"ORIGINAL CONTENT:\n{doc_content}"

    if doc_type == "cover letter":
        optimized_content = await get_openai_chat_response(
            instruction, content_feedback_combined, doc_type="CL"
        )
    elif doc_type == "resume":
        optimized_content = await get_openai_chat_response(
            instruction, content_feedback_combined, doc_type="R"
        )
    elif doc_type == "job post":
        optimized_content = await get_openai_chat_response(
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

    logger.info("----------------------- CUSTOMIZATION STARTS -----------------------")

    instruction = f"""
    Make adjustments to the {doc_type} using the adjustment instruction provided.
    """

    content = f"""
    ORIGINAL CONTENT:
    {doc_content}

    {doc_type.upper()} ADJUSTMENT INSTRUCTION:
    {custom_instruction}
    """

    if doc_type == "cover_letter":
        doc_type = "cover letter"
    if doc_type == "cover letter":
        optimized_content = await get_openai_chat_response(instruction, content, doc_type="CL")
    elif doc_type == "resume":
        optimized_content = await get_openai_chat_response(instruction, content, doc_type="R")

    logger.info(
        f"----------------------- CUSTOMIZATION DONE -----------------------"
    )
    logger.info(f"{optimized_content}")

    total = time.time() - start_time
    logger.info(f"Improved Doc Response Time: {total}")
    return optimized_content


# =========================== PROP-UP FUNCTIONS ===========================


# =========================== TAILORING FUNCTIONS ===========================
async def keyword_analysis1(doc_text_1, doc_text_2):
    # Configure CountVectorizer to convert text to lowercase
    vectorizer = CountVectorizer(lowercase=True)

    # Fit the vectorizer to the second doc to extract keywords. E.g Job description
    vectorizer.fit([doc_text_2])
    doc_text_2_keywords = vectorizer.get_feature_names_out()

    # Tokenize the first text text to ensure accurate matching. E.g Resume
    doc_text_1_words = set(doc_text_1.lower().split())

    # Find the intersection of extracted keywords and doc text words
    matched_keywords = list(doc_text_1_words.intersection(doc_text_2_keywords))

    # Optionally, calculate a matching score
    matching_score = len(matched_keywords) / len(doc_text_2_keywords)

    return matched_keywords, matching_score


# Might not be required
# async def keyword_analysis1(doc_text, job_keywords):
#     matching_keywords = []
#     for keyword in job_keywords:
#         if keyword.lower() in doc_text.lower():
#             matching_keywords.append(keyword)

#     matching_score = len(matching_keywords) / len(job_keywords)
#     return matching_keywords, matching_score


async def optimize_doc(doc_type, doc_text, job_description):
    logger.info("----------------------- OPTIMIZATION -----------------------")
    instruction = f"""
        You are a seasoned professional recruiter with decades experience that helps applicant optimize their {doc_type} to the job being applied for. \
        Your objective is to provide an optimized {doc_type}s to increase the likelihood of securing an interview at top brands across various industries by tailoring them to specific job descriptions.
    """

    if doc_type == "resume":
        instruction = instruction + "\n\n" + resume_optimization_instruction
    elif doc_type == "cover letter":
        instruction = instruction + "\n\n" + cover_letter_optimization_instruction

    content = f"""
    ORIGINAL CONTENT:
    {doc_text}

    JOB DESCRIPTION:
    {job_description}
    """

    if doc_type == "cover letter":
        optimized_content = await get_openai_chat_response(instruction, content, doc_type="CL")
    elif doc_type == "resume":
        optimized_content = await get_openai_chat_response(instruction, content, doc_type="R")

    logger.info(
        f"----------------------- {doc_type.upper()} TAILORED -----------------------"
    )
    # logger.info(f"{optimized_content}")
    return optimized_content


# =========================== TAILORING FUNCTIONS ===========================


# =========================== DATABASE FUNCTIONS ===========================
def upload_directly_to_s3(file: BinaryIO, bucket_name: str, s3_key: str, content_type: Optional[str] = None) -> None:
    """
    Upload a file directly to S3.

    Args:
        file (BinaryIO): File-like object to upload.
        bucket_name (str): Name of the S3 bucket.
        s3_key (str): S3 object key (path) for the uploaded file.
        content_type (Optional[str]): MIME type of the file. If None, it will be guessed.

    Raises:
        ValueError: If the file object doesn't have a 'read' method.
        boto3.exceptions.S3UploadFailedError: If the upload to S3 fails.
    """
    if not hasattr(file, 'read'):
        raise ValueError("File object must have a read method")

    try:
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            # region_name='your-region',  # Uncomment and set your region if necessary
        )

        # Determine the content type if not provided
        if content_type is None:
            content_type, _ = mimetypes.guess_type(s3_key)
            content_type = content_type or 'application/octet-stream'

        # Set the appropriate content disposition based on the file type
        content_disposition = 'inline' if content_type == 'application/pdf' else 'attachment'

        # Include ExtraArgs to set content type and content disposition
        s3.upload_fileobj(
            file,
            bucket_name,
            s3_key,
            ExtraArgs={
                "ContentType": content_type,
                "ContentDisposition": content_disposition,
            },
        )
    except (BotoCoreError, ClientError) as e:
        # Log the error and re-raise as a custom exception
        error_message = f"Failed to upload file to S3. Error: {str(e)}"
        logger.error(error_message)
        raise boto3.exceptions.S3UploadFailedError(error_message)


def get_full_url(s3_key):
    return f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"


# =========================== DATABASE FUNCTIONS ===========================


# =========================== TO BE REVIEWED ==============================
async def improve_resume_with_analysis(resume_content):
    readability = Readability(resume_content)
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


async def get_doc_urls(resume_content=None, job_post_content=None):
    start_time = time.time()

    improved_content = await improve_resume_with_analysis(resume_content)
    created_cl = await create_doc("cover letter", "resume", improved_content, default_cover_letter)

    if job_post_content:
        # Tailor resume and cover letter
        resume_content = await optimize_doc(
            doc_type="resume", doc_text=improved_content, job_description=job_post_content
        )
        cover_letter_content = await optimize_doc(
            doc_type="cover letter", doc_text=created_cl, job_description=job_post_content
        )
        resume_key_suffix = "optimized"
        cover_letter_key_suffix = "optimized"
    else:
        resume_content = improved_content
        cover_letter_content = created_cl
        resume_key_suffix = "improved"
        cover_letter_key_suffix = "improved"

    id = uuid4()
    resume_s3_key = f"media/resume/{resume_key_suffix}/{id}.pdf"
    cl_s3_key = f"media/cl/{cover_letter_key_suffix}/{id}.pdf"

    resume_pdf = generate_resume_pdf(resume_content, filename=f"{resume_key_suffix.capitalize()} Resume.pdf")
    cl_pdf = await generate_cv_pdf(cover_letter_content, filename=f"{cover_letter_key_suffix.capitalize()} Cover Letter.pdf", doc_type="CL")

    upload_directly_to_s3(resume_pdf, settings.AWS_STORAGE_BUCKET_NAME, resume_s3_key)
    upload_directly_to_s3(cl_pdf, settings.AWS_STORAGE_BUCKET_NAME, cl_s3_key)

    resume_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{resume_s3_key}"
    cl_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{cl_s3_key}"

    duration = time.time() - start_time
    logger.info(f"ENTIRE PROCESS TOOk {duration} seconds")

    return resume_url, cl_url


async def load_document(file_key=None, doc_url=None):
    if doc_url:
        loader = OnlinePDFLoader(doc_url)
        data = loader.load()
        # text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        # texts = text_splitter.split_documents(data)
        # return "   ".join(t.page_content for t in texts)
    elif file_key:
        with default_storage.open(file_key, 'rb') as file:
            file_content = file.read()
            file_extension = os.path.splitext(file_key)[1].lower()

            # Create a temporary file for all types
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name

            try:
                if file_extension == ".pdf":
                    loader = PyPDFLoader(temp_file_path)
                elif file_extension in ['.docx', '.doc']:
                    loader = Docx2txtLoader(temp_file_path)
                elif file_extension == '.txt':
                    loader = TextLoader(temp_file_path)
                else:
                    # For unknown file types, use a more generic loader
                    loader = UnstructuredFileLoader(temp_file_path)

                data = loader.load()
            finally:
                os.unlink(temp_file_path)  # Delete the temporary file
    else:
        raise ValueError("Either file_key or doc_url must be provided")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    texts = text_splitter.split_documents(data)
    return "   ".join(t.page_content for t in texts)


async def generate_documents(doc_type: str, content: str, is_optimized: bool) -> Tuple[bytes, bytes]:
    filename_prefix = "Customized Optimized" if is_optimized else "Improved"

    if doc_type == "resume":
        pdf = generate_resume_pdf(content, filename=f"{filename_prefix} Resume.pdf")
        docx = generate_resume_docx(content, filename=f"{filename_prefix} Resume.docx")
    elif doc_type == "cover_letter":
        pdf = await generate_cv_pdf(content, filename=f"{filename_prefix} Cover Letter.pdf", doc_type="CL")
        docx = generate_cover_letter_docx(content, filename=f"{filename_prefix} Cover Letter.docx")
    else:
        raise ValueError(f"Unsupported document type: {doc_type}")

    return pdf, docx


async def upload_documents_to_s3(pdf: bytes, docx: bytes, doc_type: str, is_optimized: bool) -> Tuple[str, str]:
    folder = "optimized" if is_optimized else "improved"
    pdf_key = f"media/{doc_type}/{folder}/{uuid4()}.pdf"
    docx_key = f"media/{doc_type}/{folder}/{uuid4()}.docx"

    pdf_mime = mimetypes.guess_type('dummy.pdf')[0] or 'application/pdf'
    docx_mime = mimetypes.guess_type('dummy.docx')[0] or 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

    upload_directly_to_s3(pdf, settings.AWS_STORAGE_BUCKET_NAME, pdf_key, content_type=pdf_mime)
    upload_directly_to_s3(docx, settings.AWS_STORAGE_BUCKET_NAME, docx_key, content_type=docx_mime)

    pdf_url = get_full_url(pdf_key)
    docx_url = get_full_url(docx_key)

    return pdf_url, docx_url


# =========================== ANTHROPIC FUNCTIONS ===========================
def extract_json(text):
    """
    Extract JSON content from text, handling potential nested structures.
    """
    stack = []
    start = -1
    for i, char in enumerate(text):
        if char == '{':
            if not stack:
                start = i
            stack.append(char)
        elif char == '}':
            if stack and stack[-1] == '{':
                stack.pop()
                if not stack:
                    return text[start:i+1]
            else:
                stack.append(char)
    return None


def repair_json(json_str):
    """
    Attempt to repair common JSON issues.
    """
    # Replace single quotes with double quotes
    json_str = json_str.replace("'", '"')

    # Remove trailing commas in objects and arrays
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*\]', ']', json_str)

    # Ensure property names are in double quotes
    json_str = re.sub(r'(\w+)(?=\s*:)', r'"\1"', json_str)

    return json_str


def parse_json_safely(json_str):
    """
    Attempt to parse JSON with multiple fallback methods.
    """
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning(f"Initial JSON parsing failed: {e}")

        # Try repairing the JSON
        repaired_json = repair_json(json_str)
        try:
            return json.loads(repaired_json)
        except json.JSONDecodeError as e:
            logger.warning(f"Parsing repaired JSON failed: {e}")

            # As a last resort, try ast.literal_eval
            try:
                import ast
                return ast.literal_eval(repaired_json)
            except (SyntaxError, ValueError) as e:
                logger.error(f"All parsing attempts failed: {e}")
                logger.error(f"Problematic JSON content: {json_str}")
                raise ValueError("Unable to parse JSON content")


async def get_anth_chat_response(prompt, to_json=True):
    start_time = time.time()

    response = await anthropic_client.messages.create(
        model="claude-3-5-sonnet-20240620", # "claude-3-5-sonnet-20240620", # "claude-3-haiku-20240307",
        max_tokens=4096,  # try 8192
        temperature=0.2,
        messages=[
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": "Here is the JSON requested:\n{"}
        ]
    )
    message = response.content[0].text
    edited_message = "{" + message[:message.rfind("}") + 1]

    if to_json:
        # Extract JSON content
        json_content = extract_json(edited_message)
        if not json_content:
            raise ValueError("No JSON content found in the response")

        # Parse JSON safely
        try:
            output_json = parse_json_safely(json_content)

            total = time.time() - start_time
            logger.info(f"Chat Response Time: {total}")
            return output_json
        except ValueError as e:
            logger.error(str(e))
            raise

    total = time.time() - start_time
    logger.info(f"Chat Response Time: {total}")

    return edited_message


class ApiType(Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


def get_structure(api_type: ApiType) -> Dict:
    if api_type == ApiType.ANTHROPIC:
        return {
            "analysis": {
                "readability": "string",
                "tone": "string",
                "structure": "string",
                "keywords": "string",  # Only if job description provided
            },
            "general_section_review": {
                "section_name": "review"
            },
            "job_tailored_section_review": {
                "section_name": "review"
            },
            "improved_resume_content": resume_example_structure,
            "job_match_score": "float",  # Only if job description provided
            "cover_letter": cover_letter_example_structure,
            "improvement_summary": {
                "key_changes": ["string"],
                "ats_optimization": "string",
                "tailoring_to_job": "string"  # if job description provided
            },
            "interview_potential_score": "float"  # On a scale of 0 to 100
        }
    elif api_type == ApiType.OPENAI:
        return {
            "type": "object",
            "properties": {
                "analysis": {
                    "type": "object",
                    "properties": {
                        "readability": {"type": "string"},
                        "tone": {"type": "string"},
                        "structure": {"type": "string"},
                        "keywords": {
                            "type": ["string", "null"],
                        },
                    },
                    "required": ["readability", "tone", "structure", "keywords"],
                    "additionalProperties": False,
                },
                "general_section_review": {"type": "string"},
                "job_tailored_section_review": {
                    "type": ["string", "null"],
                },
                "improved_resume_content": resume_example_structure_openai,
                "job_match_score": {
                    "type": ["number", "null"],
                },
                "cover_letter": cover_letter_example_structure_openai,
                "improvement_summary": {
                    "type": "object",
                    "properties": {
                        "key_changes": {
                            "type": "array",
                            "description": "Description of changes and improvements made to resume and cover letter",
                            "items": {
                                "type": "string",
                            }
                        },
                        "ats_optimization": {"type": "string"},
                        "tailoring_to_job": {"type": "string"},
                    },
                    "required": ["key_changes", "ats_optimization", "tailoring_to_job"],
                    "additionalProperties": False,
                },
                "interview_potential_score": {"type": "number"},
            },
            "required": ["analysis", "general_section_review", "job_tailored_section_review", "improved_resume_content", "job_match_score", "cover_letter", "improvement_summary", "interview_potential_score"],
            "additionalProperties": False,
        }
    raise ValueError(f"Invalid API type: {api_type}")


def get_customization_structure(api_type: ApiType, document_type: str) -> Dict:
    if api_type == ApiType.ANTHROPIC:
        return {
            f"customized_{document_type}": json.loads(resume_example_structure if document_type == "resume" else cover_letter_example_structure),
            "customization_notes": ["List of strings explaining the changes made and any relevant notes or suggestions"],
            "effectiveness_impact": "float  // Scale from -1 to 1, where -1 is very negative, 0 is neutral, and 1 is very positive"
        }
    elif api_type == ApiType.OPENAI:
        return {
            "type": "object",
            "properties": {
                f"customized_{document_type}": resume_example_structure_openai if document_type == "resume" else cover_letter_example_structure_openai,
                "customization_notes": {
                    "type": "array",
                    "description": "List of strings explaining the changes made and any relevant notes or suggestions",
                    "items": {
                        "type": "string",
                    }
                },
                "effectiveness_impact": {"type": "number"}
            },
            "required": [f"customized_{document_type}", "customization_notes", "effectiveness_impact"],
            "additionalProperties": False
        }
    raise ValueError(f"Invalid API type: {api_type}")


def get_prompt(api_type, document_type, structure, content=None, job_description=None):
    if api_type == ApiType.OPENAI:
        content = "Given below"
    elif api_type == ApiType.ANTHROPIC:
        content = content

    prompt = f"""
        You are an expert resume writer and career coach with over 20 years of experience helping candidates secure interviews at top companies. Your task is to optimize the provided {document_type} and create a compelling cover letter that will maximize the applicant's chances of getting an interview.

        DOCUMENT TYPE: {document_type}
        CONTENT: {content}
        JOB DESCRIPTION: {job_description if job_description else 'Not provided'}

        Follow these steps to create the best possible resume and cover letter:

        1. Resume Optimization:
          a) Analyze the current resume for strengths and weaknesses.
          b) Rewrite and restructure the resume to highlight the applicant's most relevant skills and achievements.
          c) Use powerful action verbs and quantify achievements wherever possible.
          d) Ensure the resume is ATS-friendly by incorporating relevant keywords from the job description (if provided).
          e) Tailor the content to the specific job or industry, emphasizing the most relevant experiences and skills.
          f) Improve the overall readability and visual appeal of the resume.

        2. Cover Letter Creation:
          a) Write a compelling, personalized cover letter that complements the resume.
          b) Address the specific requirements mentioned in the job description (if provided).
          c) Highlight the applicant's unique value proposition and most relevant achievements.
          d) Demonstrate enthusiasm for the position and knowledge of the company.
          e) Keep the tone professional yet engaging, and limit the length to one page.

        3. Overall Improvements:
          a) Ensure consistency in formatting and language between the resume and cover letter.
          b) Proofread for any grammatical or spelling errors.
          c) Optimize the documents for both human readers and ATS systems.

        Return the results in the following JSON format:
        {json.dumps(structure, indent=2)}

        Focus on creating the most impactful and interview-worthy documents possible. Be creative and strategic in your improvements while maintaining honesty and professionalism.
        """
    return prompt


async def analyze_and_improve_document(doc_type="resume", content=None, job_description=None):
    # treat bug of incorrect pdf document formating that happens occasionally
    start_time = time.time()
    result = {}

    try:
        api_type = ApiType.ANTHROPIC
        structure = get_structure(api_type)
        prompt = get_prompt(api_type, doc_type, structure, content, job_description)
        result = await get_anth_chat_response(prompt)

        experiences_list = result["improved_resume_content"]["experiences"]
        experiences_dict = {
            f"experience_{i+1}": experience for i, experience in enumerate(experiences_list)
        }
        result["improved_resume_content"]["experiences"] = experiences_dict

        total = time.time() - start_time
        logger.info(f"Chat Response Time: {total}")

    except anthropic.InternalServerError as e:
        logger.error("Anthropic API internal server error. Switching to OpenAI.")

        api_type = ApiType.OPENAI
        structure = get_structure(api_type)
        prompt = get_prompt(api_type, doc_type, structure, content, job_description)
        result = await get_openai_chat_response(prompt, content, structure)

        total = time.time() - start_time
        logger.info(f"Chat Response Time: {total}")

    except anthropic.RateLimitError as e:
        logger.error("Anthropic API rate limit exceeded. Switching to OpenAI.")
        api_type = ApiType.OPENAI
        structure = get_structure(api_type)
        prompt = get_prompt(api_type, doc_type, structure, content, job_description)
        result = await get_openai_chat_response(prompt, content, structure)

        total = time.time() - start_time
        logger.info(f"Chat Response Time: {total}")

    except anthropic.APIConnectionError as e:
        logger.error("Anthropic API connection error. Switching to OpenAI.")
        api_type = ApiType.OPENAI
        structure = get_structure(api_type)
        prompt = get_prompt(api_type, doc_type, structure, content, job_description)
        result = await get_openai_chat_response(prompt, content, structure)

        total = time.time() - start_time
        logger.info(f"Chat Response Time: {total}")

    except Exception as e:
        logger.error(f"Unexpected error occurred: {e}. Switching to OpenAI.")
        api_type = ApiType.OPENAI
        structure = get_structure(api_type)
        prompt = get_prompt(api_type, doc_type, structure, content, job_description)
        result = await get_openai_chat_response(prompt, content, structure)

        total = time.time() - start_time
        logger.info(f"Chat Response Time: {total}")

    return result


def get_customization_prompt(api_type, document_type, customization_request, customization_structure, original_content=None):
    if api_type == ApiType.OPENAI:
        original_content = "Given below"
    elif api_type == ApiType.ANTHROPIC:
        original_content = json.dumps(original_content) if isinstance(original_content, dict) else original_content

    prompt = f"""
    As an expert resume writer and career coach, your task is to customize the provided {document_type}
    based on the user's specific request. Apply the requested changes while maintaining the overall
    quality and effectiveness of the document.

    DOCUMENT TYPE: {document_type}
    ORIGINAL CONTENT: {original_content}
    CUSTOMIZATION REQUEST: {customization_request}

    Guidelines for customization:
    1. Carefully interpret the user's request and apply changes accordingly.
    2. Maintain the professional tone and structure of the document.
    3. Ensure any additions or changes align with best practices for {document_type}s.
    4. Preserve the document's ATS-friendly qualities if applicable.
    5. If the request might negatively impact the document's effectiveness, provide a brief explanation and suggestion.

    Return the customized document in the following format:
    {json.dumps(customization_structure, indent=2)}
    """
    return prompt


async def anth_customize_document(
    document_type: str,
    original_content: Union[Dict, str],
    customization_request: str
) -> Optional[Dict[str, Union[Dict, List[str], float]]]:
    """
    Customizes a resume or cover letter based on user input.

    Args:
        document_type (str): Either "resume" or "cover_letter"
        original_content (Union[Dict, str]): The original optimized document
        customization_request (str): The user's customization request

    Returns:
        Optional[Dict[str, Union[Dict, List[str], float]]]: Customized document info or None if failed
    """

    try:
        api_type = ApiType.ANTHROPIC
        customization_structure = get_customization_structure(api_type, document_type)
        customization_prompt = get_customization_prompt(api_type, document_type, customization_request, customization_structure, original_content)
        result = await get_anth_chat_response(customization_prompt)
        if document_type == "resume":
            experiences_list = result["improved_resume_content"]["experiences"]
            experiences_dict = {
                f"experience_{i+1}": experience for i, experience in enumerate(experiences_list)
            }
            result["improved_resume_content"]["experiences"] = experiences_dict
        prepared_result = {
            "customized_document": result.get(f"customized_{document_type}", {}),
            "customization_notes": result.get("customization_notes", []),
            "effectiveness_impact": result.get("effectiveness_impact", 0),
            "metadata": {
                "document_type": document_type,
                "customization_request": customization_request
            }
        }
        return prepared_result
    except Exception as e:
        logger.error(f"Failed to customize document: {e}")
        try:
            api_type = ApiType.OPENAI
            customization_structure = get_customization_structure(api_type, document_type)
            customization_prompt = get_customization_prompt(api_type, document_type, customization_request, customization_structure, original_content)
            result = await get_openai_chat_response(customization_prompt, original_content, customization_structure)
            prepared_result = {
                "customized_document": result.get(f"customized_{document_type}", {}),
                "customization_notes": result.get("customization_notes", []),
                "effectiveness_impact": result.get("effectiveness_impact", 0),
                "metadata": {
                    "document_type": document_type,
                    "customization_request": customization_request
                }
            }
            return prepared_result
        except Exception as e:
            logger.error(f"Failed to customize document with OpenAI: {e}")
            return None


async def get_anth_doc_urls(resume_content: Optional[str] = None, job_post_content: Optional[str] = None) -> Dict[str, Any]:
    start_time = time.time()

    is_optimized = bool(job_post_content)
    result = await analyze_and_improve_document(content=resume_content, job_description=job_post_content)

    if not result.get("improved_resume_content"):
        logger.warning("improved_resume_content missing from result")
    if not result.get("cover_letter"):
        logger.warning("cover_letter missing from result")
    if not result.get("improvement_summary"):
        logger.warning("improvement_summary missing from result")
    if is_optimized and "job_match_score" not in result:
        logger.warning("job_match_score missing from result for optimized document")
    if "interview_potential_score" not in result:
        logger.warning("interview_potential_score missing from result")

    resume_content = result.get("improved_resume_content", {})
    cover_letter_content = result.get("cover_letter", {})

    # Generate and upload documents
    resume_pdf, resume_docx = await generate_documents("resume", resume_content, is_optimized)
    cl_pdf, cl_docx = await generate_documents("cover_letter", cover_letter_content, is_optimized)

    resume_pdf_url, resume_docx_url = await upload_documents_to_s3(resume_pdf, resume_docx, "resume", is_optimized)
    cl_pdf_url, cl_docx_url = await upload_documents_to_s3(cl_pdf, cl_docx, "cover_letter", is_optimized)

    duration = time.time() - start_time
    logger.info(f"ENTIRE PROCESS TOOK {duration:.2f} seconds")

    improvement_summary = result.get("improvement_summary", {})

    return {
        "documents": {
            "resume": {
                "pdf_url": resume_pdf_url,
                "docx_url": resume_docx_url
            },
            "cover_letter": {
                "pdf_url": cl_pdf_url,
                "docx_url": cl_docx_url
            }
        },
        "insights": {
            "improvement_summary": {
                "key_changes": improvement_summary.get("key_changes", []),
                "ats_optimization": improvement_summary.get("ats_optimization", ""),
                "tailoring_to_job": improvement_summary.get("tailoring_to_job", "N/A" if not is_optimized else "")
            },
            "scores": {
                "job_match": result.get("job_match_score", 0 if is_optimized else None),
                "interview_potential": result.get("interview_potential_score", 0)
            }
        },
        "metadata": {
            "is_optimized": is_optimized,
            "processing_time": f"{duration:.2f} seconds"
        }
    }
# =========================== ANTHROPIC FUNCTIONS ===========================
