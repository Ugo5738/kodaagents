import json
from typing import Any, Dict
from uuid import uuid4

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from koda.config.logging_config import configure_file_logger, configure_logger
from resume.models import (
    CustomizationAnalytics,
    CustomizationNote,
    DocumentCustomization,
    ImprovementSummary,
    JobDetails,
    KeyChange,
    OptimizationAnalytics,
    OptimizedDocument,
    OriginalDocument,
)
from resume.utils.util_funcs import (
    anth_customize_document,
    generate_documents,
    get_anth_doc_urls,
    load_document,
    upload_documents_to_s3,
)

logger = configure_logger(__name__)
file_logger = configure_file_logger(__name__)

class ResumeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
        else:
            self.user_id = f"user_{uuid4()}"
            self.resume_group_name = f"resume_{self.user_id}"
            await self.channel_layer.group_add(self.resume_group_name, self.channel_name)
            file_logger.info(f"WebSocket connected for user: {self.user_id}")
            await self.accept()
            self.session_data: Dict[str, Any] = {}

    async def disconnect(self, close_code):
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

    @database_sync_to_async
    def save_original_document(self, file_key, content):
        document = OriginalDocument.objects.get(file_key=file_key)
        document.content = content
        document.save()
        return document.id

    async def handle_resume_upload(self, data):
        file_key = data['file_key']
        self.session_data['resume_file_key'] = file_key

        doc_content = await load_document(file_key=file_key)
        original_doc_id = await self.save_original_document(file_key, doc_content)
        self.session_data['original_doc_id'] = original_doc_id

        await self.send_success("Resume file uploaded and stored successfully")

    @database_sync_to_async
    def save_job_details(self, content):
        return JobDetails.objects.create(user=self.user, content=content)

    @database_sync_to_async
    def get_latest_original_document(self, category, document_type):
        return OriginalDocument.objects.filter(
            user=self.user,
            category=category,
            document_type=document_type
        ).order_by('-uploaded_at').first()

    async def handle_job_details(self, data):
        job_details = data['details']
        category = data.get('category', 'General')  # Default to 'General' if not provided
        document_type = data.get('document_type', 'resume')  # Default to 'resume' if not provided
        job_details_obj = await self.save_job_details(job_details)
        self.session_data['job_details_id'] = job_details_obj.id

        original_doc = await self.get_latest_original_document(category, document_type)
        self.session_data['original_doc_id'] = original_doc.id

        if 'original_doc_id' in self.session_data:
            if await self.increment_usage('creation'):
                await self.process_resume_and_job_details()
        else:
            await self.send_error("Resume not uploaded yet")

    @database_sync_to_async
    def save_optimized_document(self, original_doc_id, job_details_id, document_type, pdf_url, docx_url, content):
        original_doc = OriginalDocument.objects.get(id=original_doc_id)
        job_details = JobDetails.objects.get(id=job_details_id) if job_details_id else None

        return OptimizedDocument.objects.create(
            original_document_id=original_doc_id,
            job_details=job_details,
            document_type=document_type,
            pdf_url=pdf_url,
            docx_url=docx_url,
            content=content
        )

    @database_sync_to_async
    def save_optimization_analytics(self, optimized_doc_id, job_match_score, interview_potential_score, ats_optimization, tailoring_to_job):
        return OptimizationAnalytics.objects.create(
            optimized_document_id=optimized_doc_id,
            job_match_score=job_match_score,
            interview_potential_score=interview_potential_score,
            ats_optimization=ats_optimization,
            tailoring_to_job=tailoring_to_job
        )

    @database_sync_to_async
    def save_improvement_summary(self, optimized_doc_id, key_changes):
        summary = ImprovementSummary.objects.create(optimized_document_id=optimized_doc_id)
        for change in key_changes:
            KeyChange.objects.create(improvement_summary=summary, description=change)
        return summary

    async def process_resume_and_job_details(self):
        original_doc_id = self.session_data['original_doc_id']
        job_details_id = self.session_data.get('job_details_id')

        try:
            original_doc = await self.get_original_document(original_doc_id)
            job_details = await self.get_job_details(job_details_id) if job_details_id else None

            result = await get_anth_doc_urls(original_doc.content, job_details.content if job_details else None)

            # Save optimized resume
            optimized_resume = await self.save_optimized_document(
                original_doc_id,
                job_details_id,
                'resume',
                result["documents"]["resume"]["pdf_url"],
                result["documents"]["resume"]["docx_url"],
                json.dumps(result["documents"]["resume"])
            )

            # Save optimized cover letter
            optimized_cl = await self.save_optimized_document(
                original_doc_id,
                job_details_id,
                'cover_letter',
                result["documents"]["cover_letter"]["pdf_url"],
                result["documents"]["cover_letter"]["docx_url"],
                json.dumps(result["documents"]["cover_letter"])
            )

            # Save analytics
            await self.save_optimization_analytics(
                optimized_resume.id,
                result["insights"]["scores"]["job_match"],
                result["insights"]["scores"]["interview_potential"],
                result["insights"]["improvement_summary"]["ats_optimization"],
                result["insights"]["improvement_summary"]["tailoring_to_job"]
            )

            # Save improvement summary
            await self.save_improvement_summary(
                optimized_resume.id,
                result["insights"]["improvement_summary"]["key_changes"]
            )

            final_result = {
                "documents": {
                    "resume_pdf_url": optimized_resume.pdf_url,
                    "resume_docx_url": optimized_resume.docx_url,
                    "cover_letter_pdf_url": optimized_cl.pdf_url,
                    "cover_letter_docx_url": optimized_cl.docx_url,
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

    @database_sync_to_async
    def get_original_document(self, doc_id):
        return OriginalDocument.objects.get(id=doc_id)

    @database_sync_to_async
    def get_job_details(self, job_details_id):
        return JobDetails.objects.get(id=job_details_id)

    @database_sync_to_async
    def get_optimized_document(self, original_doc_id, doc_type):
        try:
            return OptimizedDocument.objects.get(
                original_document_id=original_doc_id,
                document_type=doc_type,
                is_latest=True
            )
        except OptimizedDocument.DoesNotExist:
            return None

    @database_sync_to_async
    def save_document_customization(self, optimized_doc_id, instruction, pdf_url, docx_url, content):
        return DocumentCustomization.objects.create(
            optimized_document_id=optimized_doc_id,
            instruction=instruction,
            pdf_url=pdf_url,
            docx_url=docx_url,
            content=content
        )

    @database_sync_to_async
    def save_customization_analytics(self, customization_id, effectiveness_impact):
        return CustomizationAnalytics.objects.create(
            customization_id=customization_id,
            effectiveness_impact=effectiveness_impact
        )

    @database_sync_to_async
    def save_customization_notes(self, customization_id, notes):
        for note in notes:
            CustomizationNote.objects.create(customization_id=customization_id, content=note)

    async def handle_customize_document(self, data):
        doc_type = data.get('doc_type')
        doc_url = data.get('doc_url')
        custom_instruction = data.get('custom_instruction')

        if not all([doc_type, doc_url, custom_instruction]):
            await self.send_error("Missing required fields for document customization")
            return

        if await self.increment_usage('customization'):
            await self.customize_document(doc_type, doc_url, custom_instruction)

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

            # Retrieve the OptimizedDocument instance
            optimized_doc = await self.get_optimized_document(self.session_data['original_doc_id'], doc_type)

            if optimized_doc is None:
                await self.send_error("No optimized document found for customization")
                return

            # Save customization
            customization = await self.save_document_customization(
                optimized_doc.id,
                custom_instruction,
                pdf_url,
                docx_url,
                json.dumps(customized_content["customized_document"])
            )

            # Save customization analytics
            await self.save_customization_analytics(
                customization.id,
                customized_content["effectiveness_impact"]
            )

            # Save customization notes
            await self.save_customization_notes(
                customization.id,
                customized_content["customization_notes"]
            )

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

    async def handle_download_document(self, data):
        if await self.increment_usage('download'):
            # Implement download logic here
            pass

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
