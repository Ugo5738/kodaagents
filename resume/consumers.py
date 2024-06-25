import json
import os
from uuid import uuid4
from typing import Any, Dict

from channels.generic.websocket import AsyncWebsocketConsumer
from langchain_community.document_loaders import OnlinePDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

from koda.config.logging_config import configure_logger, configure_file_logger
from resume.utils.util_funcs import improve_resume_with_analysis, customize_doc, get_doc_urls, load_document, generate_pdf, upload_pdf_to_s3


# Main logger for console output
logger = configure_logger(__name__)
# File logger for connection logs
file_logger = configure_file_logger(__name__)

class ResumeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope["url_route"]["kwargs"]["resume_id"]
        self.resume_group_name = f"resume_{self.user_id}"

        # Join resume group
        await self.channel_layer.group_add(self.resume_group_name, self.channel_name)

        file_logger.info(f"WebSocket connected for user {self.user_id}")
        
        await self.accept()
        self.session_data: Dict[str, Any] = {}

    async def disconnect(self, close_code):
        # Leave resume group
        await self.channel_layer.group_discard(self.resume_group_name, self.channel_name)
        file_logger.info(f"WebSocket disconnected for user {self.user_id}")

    async def receive(self, text_data):
        logger.info("=========================== MESSAGE RECEIVED ===========================")

        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get("type")

            handlers = {
                'resume_uploaded': self.handle_resume_upload,
                'jobDetails': self.handle_job_details,
                'customize_document': self.handle_customize_document
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
        
        await self.customize_document(doc_type, doc_url, custom_instruction)

    async def process_resume_and_job_details(self):
        resume_file_key = self.session_data['resume_file_key']
        job_details = self.session_data['job_details']

        try:
            doc_content = await load_document(file_key=resume_file_key)
            rez_pdf_url, cl_pdf_url = await get_doc_urls(doc_content, job_details)
            result = {"resume_url": rez_pdf_url, "cover_letter_url": cl_pdf_url}
            await self.send_message(result)
        except Exception as e:
            logger.exception("Error processing resume and job details")
            await self.send_error(str(e))
    
    async def customize_document(self, doc_type, doc_url, custom_instruction):
        try:
            doc_content = await load_document(doc_url=doc_url)
            customized_content = await customize_doc(doc_type, doc_content, custom_instruction)
            pdf = await generate_pdf(doc_type, customized_content)
            pdf_url = await upload_pdf_to_s3(pdf, doc_type)
            result = {f"{doc_type}_url": pdf_url}
            await self.send_message(result)
        except Exception as e:
            logger.exception("Error customizing document")
            await self.send_error(str(e))
    
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