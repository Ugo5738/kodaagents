import json
from typing import Any, Dict
from uuid import uuid4

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from koda.config.logging_config import configure_file_logger, configure_logger
from resume.utils.util_funcs import (
    anth_customize_document,
    generate_documents,
    get_anth_doc_urls,
    load_document,
    upload_documents_to_s3,
)

# Main logger for console output
logger = configure_logger(__name__)
# File logger for connection logs
file_logger = configure_file_logger(__name__)

class ResumeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
        else:
            self.user_id = f"user_{uuid4()}"
            self.resume_group_name = f"resume_{self.user_id}"

            # Join resume group
            await self.channel_layer.group_add(self.resume_group_name, self.channel_name)

            file_logger.info(f"WebSocket connected for user: {self.user_id}")

            await self.accept()
            self.session_data: Dict[str, Any] = {}

    async def disconnect(self, close_code):
        # Leave resume group
        await self.channel_layer.group_discard(self.resume_group_name, self.channel_name)
        file_logger.info(f"WebSocket disconnected for user: {self.user_id}")

    async def receive(self, text_data):
        logger.info("=========================== MESSAGE RECEIVED ===========================")

        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get("type")

            handlers = {
                'resume_uploaded': self.handle_resume_upload,
                'jobDetails': self.handle_job_details,
                'customize_document': self.handle_customize_document,
                'download_document': self.handle_download_document
            }

            handler = handlers.get(message_type)
            if handler:
                await handler(text_data_json)
            else:
                await self.send_error("Invalid message type")

        except json.JSONDecodeError:
            await self.send_error("Invalid JSON")
        except Exception as e:
            logger.exception("Error processing message")
            await self.send_error(str(e))

    async def handle_resume_upload(self, data):
        self.session_data['resume_file_key'] = data['file_key']
        await self.send_success("Resume file key stored successfully")

    async def handle_job_details(self, data):
        self.session_data['job_details'] = data['details']
        if 'resume_file_key' in self.session_data:
            if await self.increment_usage('creation'):
                await self.process_resume_and_job_details()
        else:
            await self.send_error("Resume not uploaded yet")

    async def handle_customize_document(self, data):
        doc_type = data.get('doc_type')
        doc_url = data.get('doc_url')
        custom_instruction = data.get('custom_instruction')

        if not all([doc_type, doc_url, custom_instruction]):
            await self.send_error("Missing required fields for document customization")
            return

        if await self.increment_usage('customization'):
            await self.customize_document(doc_type, doc_url, custom_instruction)

    async def handle_download_document(self, data):
        if await self.increment_usage('download'):
            # Implement download logic here
            pass

    async def process_resume_and_job_details(self):
        resume_file_key = self.session_data['resume_file_key']
        job_details = self.session_data['job_details']

        try:
            doc_content = await load_document(file_key=resume_file_key)
            result = await get_anth_doc_urls(doc_content, job_details)

            final_result = {
                "documents": {
                    "resume_pdf_url": result["documents"]["resume"]["pdf_url"],
                    "resume_docx_url": result["documents"]["resume"]["docx_url"],
                    "cover_letter_pdf_url": result["documents"]["cover_letter"]["pdf_url"],
                    "cover_letter_docx_url": result["documents"]["cover_letter"]["docx_url"],
                },
                "initial_optimization": {
                    "improvement_summary": result["insights"]["improvement_summary"],
                    "scores": result["insights"]["scores"]
                }
            }

            await self.send_message(final_result)
        except Exception as e:
            logger.exception("Error processing resume and job details")
            await self.send_error(str(e))

    async def customize_document(self, doc_type: str, doc_url: str, custom_instruction: str) -> None:
        try:
            doc_content = await load_document(doc_url=doc_url)
            customized_content = await anth_customize_document(doc_type, doc_content, custom_instruction)

            if customized_content is None:
                await self.send_error("Failed to customize document")
                return

            is_optimized = True
            pdf, docx = await generate_documents(doc_type, customized_content["customized_document"], is_optimized)
            pdf_url, docx_url = await upload_documents_to_s3(pdf, docx, doc_type, is_optimized)

            result = {
                "documents": {
                    f"{doc_type}_pdf_url": pdf_url,
                    f"{doc_type}_docx_url": docx_url
                },
                "customization_info": {
                    "notes": customized_content["customization_notes"],
                    "effectiveness_impact": customized_content["effectiveness_impact"]
                },
                "metadata": customized_content["metadata"]
            }

            await self.send_message(result)
        except Exception as e:
            logger.exception(f"Error customizing document: {e}")
            await self.send_error(f"Error customizing document: {str(e)}")

    @database_sync_to_async
    def _increment_usage(self, action_type):
        if self.user.tier is None:
            return False, "No active subscription"

        if action_type == 'creation':
            self.user.creation_count += 1
        elif action_type == 'customization':
            self.user.customization_count += 1
        elif action_type == 'download':
            self.user.download_count += 1

        self.user.save()

        if self.user.has_reached_limit(action_type):
            return False, f"Usage limit reached for {action_type}"
        return True, None

    async def increment_usage(self, action_type):
        success, error_message = await self._increment_usage(action_type)
        if not success:
            await self.send_error(error_message)
        return success

    async def send_message(self, message):
        await self.channel_layer.group_send(
            self.resume_group_name,
            {"type": "resume_message", "message": message},
        )

    async def send_error(self, error_message):
        await self.send(text_data=json.dumps({"error": error_message}))

    async def send_success(self, success_message):
        await self.send(text_data=json.dumps({"message": success_message}))

    async def resume_message(self, event):
        await self.send(text_data=json.dumps({"message": event["message"]}))

# SAMPLE RESULTS
# {
#   'documents': {
#     'resume_pdf_url': 'https://kodastorage.s3.amazonaws.com/media/resume/optimized/3083b985-e22d-4b29-a1ee-608f87ea1d41.pdf',
#     'resume_docx_url': 'https://kodastorage.s3.amazonaws.com/media/resume/optimized/9102fac0-64cc-4fe0-97bd-165281656620.docx',
#     'cover_letter_pdf_url': 'https://kodastorage.s3.amazonaws.com/media/cover_letter/optimized/5c3e16e3-4a53-4f98-a341-59869ade526d.pdf',
#     'cover_letter_docx_url': 'https://kodastorage.s3.amazonaws.com/media/cover_letter/optimized/9641adf1-981a-4d97-8ea4-c2851e44e751.docx'
#   },
#   'initial_optimization': {
#     'improvement_summary': {
#       'key_changes': [
#         'Restructured the resume to highlight most relevant and impactful experiences',
#         'Rewrote job descriptions to focus on quantifiable achievements and results',
#         'Added a powerful summary statement tailored to the Digital Marketing Specialist role',
#         'Reorganized and expanded the skills section to better match job requirements',
#         'Created a compelling cover letter that addresses specific job requirements and showcases relevant achievements'
#       ],
#       'ats_optimization': "Incorporated key terms from the job description such as 'campaign management', 'content creation', 'SEO/SEM', and 'email marketing' throughout the resume to improve ATS compatibility.",
#       'tailoring_to_job': 'Emphasized experiences and skills most relevant to the Digital Marketing Specialist role, such as campaign management, analytics, and content creation. Highlighted achievements that demonstrate ability to drive results in areas specified in the job description.'
#     },
#     'scores': {
#       'job_match': 85,
#       'interview_potential': 90
#     }
#   }
# }


# {
#   'documents': {
#     'resume_pdf_url': 'https://kodastorage.s3.amazonaws.com/media/resume/optimized/c71f6ac6-82bd-4ba2-9a21-b192f3e6baf7.pdf',
#     'resume_docx_url': 'https://kodastorage.s3.amazonaws.com/media/resume/optimized/8c46a338-044a-4b61-8739-7b3e582b179b.docx'
#   },
#   'customization_info': {
#     'notes': [
#       'Removed the Parmz Digital Technologies experience as requested.',
#       'Maintained the chronological order of the remaining experiences.',
#       'No other changes were made to preserve the overall structure and content of the resume.'
#     ],
#     'effectiveness_impact': -0.2
#   },
#   'metadata': {
#     'document_type': 'resume',
#     'customization_request': 'remove palmz experience'
#   }
# }
