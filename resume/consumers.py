import json

from channels.generic.websocket import AsyncWebsocketConsumer

from koda.config.logging_config import configure_logger
from resume.utils.util_funcs import create_docs, customize_doc

logger = configure_logger(__name__)


class ResumeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope["url_route"]["kwargs"]["resume_id"]
        self.resume_group_name = f"resume_{self.user_id}"

        # Join resume group
        await self.channel_layer.group_add(self.resume_group_name, self.channel_name)

        logger.info("=========================== CONNECTED ===========================")
        await self.accept()

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
        logger.info(
            "=========================== MESSAGE RECIEVED ==========================="
        )

        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get("type")
            message = text_data_json.get("message")
            resume_content = text_data_json.get("resume_content")
            job_post_content = text_data_json.get("job_post_content")

            if message_type == "customization":
                custom_instruction = text_data_json.get("custom_instruction")
                cover_letter_content = text_data_json.get("cover_letter_content")

                if resume_content:
                    doc_content = resume_content
                    doc_type = "resume"
                elif cover_letter_content:
                    doc_content = cover_letter_content
                    doc_type = "cover letter"

                customize_doc(
                    doc_type=doc_type,
                    doc_content=doc_content,
                    custom_instruction=custom_instruction,
                )

            elif message_type == "creation":
                res = await create_docs(
                    resume_content=resume_content, job_post_content=job_post_content
                )

                # Send message to resume group
                await self.channel_layer.group_send(
                    self.resume_group_name,
                    {"type": "resume_message", "message": res},
                )

            elif message_type == "pdf_upload":
                # Handle resume PDF upload
                pass
        except json.JSONDecodeError as e:
            logger.info(
                "=========================== JSON ERROR DETECTED ==========================="
            )
            logger.info(e)
            logger.info(
                "=========================== JSON ERROR DISPLAYED ABOVE ==========================="
            )
            await self.send(text_data=json.dumps({"error": "Invalid JSON"}))
        except KeyError as e:
            logger.info(
                "=========================== KEY ERROR DETECTED ==========================="
            )
            logger.info(e)
            logger.info(
                "=========================== KEY ERROR DISPLAYED ABOVE ==========================="
            )
            await self.send(text_data=json.dumps({"error": "Missing message key"}))
        except Exception as e:
            logger.info(
                "=========================== GENERAL ERROR DETECTED ==========================="
            )
            logger.info(e)
            logger.info(
                "=========================== GENERAL ERROR DISPLAYED ABOVE ==========================="
            )
            await self.send(text_data=json.dumps({"error": e}))

    # Receive message from resume group
    async def resume_message(self, event):
        message = event["message"]

        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": message}))
