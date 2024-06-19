import json
import os
import tempfile
from uuid import uuid4

from channels.generic.websocket import AsyncWebsocketConsumer
from langchain_community.document_loaders import OnlinePDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

from koda.config.logging_config import configure_logger
from resume.utils.util_funcs import improve_resume_with_analysis, customize_doc, get_doc_urls

from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

import docx

logger = configure_logger(__name__)

class ResumeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope["url_route"]["kwargs"]["resume_id"]
        self.resume_group_name = f"resume_{self.user_id}"

        # Join resume group
        await self.channel_layer.group_add(self.resume_group_name, self.channel_name)

        logger.info("=========================== CONNECTED ===========================")
        await self.accept()
        self.session_data = {}

    async def disconnect(self, close_code):
        logger.info("=========================== DISCONNECTED ===========================")

        # Leave resume group
        await self.channel_layer.group_discard(self.resume_group_name, self.channel_name)

    async def receive(self, text_data):
        logger.info("=========================== MESSAGE RECEIVED ===========================")

        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get("type")
            job_post_content = text_data_json.get("job_post_content")

            if message_type == 'resume_uploaded':
                self.session_data['resume_file_key'] = text_data_json['file_key']
            elif message_type == 'jobDetails':
                self.session_data['job_details'] = text_data_json['details']

            if 'resume_file_key' in self.session_data and 'job_details' in self.session_data:
                resume_file_key = self.session_data['resume_file_key']
                job_details = self.session_data['job_details']

                # Open the file using default_storage
                with default_storage.open(resume_file_key, 'rb') as resume_file:
                    temp_file_path = f"/tmp/{uuid4()}.pdf"
                    with open(temp_file_path, 'wb') as temp_file:
                        temp_file.write(resume_file.read())

                # Determine file extension
                file_extension = os.path.splitext(resume_file_key)[1]

                # Load the document content based on file type
                if file_extension == ".pdf":
                    loader = OnlinePDFLoader(temp_file_path)
                elif file_extension == ".docx":
                    doc = docx.Document(temp_file_path)
                    doc_content = "\n".join([para.text for para in doc.paragraphs])
                    loader = TextLoader(doc_content)
                else:
                    with open(temp_file_path, 'r', encoding='utf-8') as temp_file:
                        loader = TextLoader(temp_file.read())

                data = loader.load()

                # Split the text for analysis
                text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
                texts = text_splitter.split_documents(data)

                doc_list = [t.page_content for t in texts]
                doc_content = "   ".join(doc_list)

                # Process the document content (e.g., improve and optimize)
                rez_pdf_url, cl_pdf_url = await get_doc_urls(doc_content, job_details)
                result = {"resume_url": rez_pdf_url, "cover_letter_url": cl_pdf_url}
                print(result)
                # Send message to resume group
                await self.channel_layer.group_send(
                    self.resume_group_name,
                    {"type": "resume_message", "message": result},
                )

        except json.JSONDecodeError as e:
            logger.info("=========================== JSON ERROR DETECTED ===========================")
            logger.info(e)
            await self.send(text_data=json.dumps({"error": "Invalid JSON"}))
        except KeyError as e:
            logger.info("=========================== KEY ERROR DETECTED ===========================")
            logger.info(e)
            await self.send(text_data=json.dumps({"error": "Missing message key"}))
        except Exception as e:
            logger.info("=========================== GENERAL ERROR DETECTED ===========================")
            logger.info(f"Error: {e}")
            logger.info(f"File Extension: {file_extension}")
            logger.info(f"File Path: {temp_file_path}")
            await self.send(text_data=json.dumps({"error": str(e)}))

    async def resume_message(self, event):
        message = event["message"]

        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": message}))
