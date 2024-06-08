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
        logger.info(
            "=========================== DISCONNECTED ==========================="
        )

        # Leave resume group
        await self.channel_layer.group_discard(
            self.resume_group_name, self.channel_name
        )

    # Receive message from WebSocket
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
                resume_file_path = default_storage.path(self.session_data['resume_file_key'])
                job_details = self.session_data['job_details']
            
            if message_type == "file_upload":
                await self.send(text_data=json.dumps({"message": "Ready to receive file data"}))
            
            # if message_type == "customization":
            #     custom_instruction = text_data_json.get("custom_instruction")
            #     resume_content = text_data_json.get("resume_content")
            #     cover_letter_content = text_data_json.get("cover_letter_content")

            #     if resume_content:
            #         doc_content = resume_content
            #         doc_type = "resume"
            #     elif cover_letter_content:
            #         doc_content = cover_letter_content
            #         doc_type = "cover letter"

            #     customized_content = customize_doc(
            #         doc_type=doc_type,
            #         doc_content=doc_content,
            #         custom_instruction=custom_instruction,
            #     )

            #     id = uuid4()
            #     customized_resume_s3_key = f"media/resume/customized_resume/{id}.pdf"
            #     customized_resume_pdf = generate_resume_pdf(customized_content, filename=f"Customized Resume.pdf")

            #     upload_directly_to_s3(customized_resume_pdf, settings.AWS_STORAGE_BUCKET_NAME, customized_resume_s3_key)

            #     resume_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{customized_resume_s3_key}"
                
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
            logger.info(e)
            await self.send(text_data=json.dumps({"error": str(e)}))

    async def receive_bytes(self, bytes_data):
        try:
            # Assume the first message contains file metadata
            text_data_json = json.loads(bytes_data.decode('utf-8'))
            file_extension = text_data_json.get("file_extension")
            job_post_content = text_data_json.get("job_post_content")

            # Receive the actual file content
            file_data = await self.receive()

            # Save the file content to a temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
            temp_file.write(file_data)
            temp_file.close()

            public_url = f"file://{temp_file.name}"

            # Load the document content
            if file_extension == ".pdf":
                loader = OnlinePDFLoader(public_url)
            else:
                loader = TextLoader(public_url)
            data = loader.load()

            # Split the text for analysis
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
            texts = text_splitter.split_documents(data)

            doc_list = [t.page_content for t in texts]
            doc_content = "   ".join(doc_list)

            os.remove(temp_file.name)  # Remove the temporary file after processing

            # Process the document content (e.g., improve and optimize)
            if job_post_content:
                rez_pdf_url, cl_pdf_url = await get_doc_urls(doc_content, job_post_content)
                result = {"resume_url": rez_pdf_url, "cover_letter_url": cl_pdf_url}
            else:
                rez_pdf_url, cl_pdf_url = await get_doc_urls(doc_content)
                result = {"resume_url": rez_pdf_url, "cover_letter_url": cl_pdf_url}

            # Send message to resume group
            await self.channel_layer.group_send(
                self.resume_group_name,
                {"type": "resume_message", "message": result},
            )

        except Exception as e:
            logger.info("=========================== GENERAL ERROR DETECTED ===========================")
            logger.info(e)
            await self.send(text_data=json.dumps({"error": str(e)}))

    # Receive message from resume group
    async def resume_message(self, event):
        message = event["message"]

        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": message}))
