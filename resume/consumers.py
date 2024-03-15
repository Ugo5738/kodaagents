# resume/consumers.py

import json

from channels.generic.websocket import AsyncWebsocketConsumer


class ResumeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.resume_id = self.scope["url_route"]["kwargs"]["resume_id"]
        self.resume_group_name = f"resume_{self.resume_id}"

        # Join resume group
        await self.channel_layer.group_add(self.resume_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        # Leave resume group
        await self.channel_layer.group_discard(
            self.resume_group_name, self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json["type"]
            message = text_data_json["message"]

            if message_type == "customization":
                # Handle customization message
                pass
            elif message_type == "description":
                # Handle resume description
                pass
            elif message_type == "pdf_upload":
                # Handle resume PDF upload
                pass
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"error": "Invalid JSON"}))
        except KeyError:
            await self.send(text_data=json.dumps({"error": "Missing message key"}))
        except Exception as e:
            await self.send(text_data=json.dumps({"error": e}))

        # Send message to resume group
        await self.channel_layer.group_send(
            self.resume_group_name, {"type": "resume_message", "message": message}
        )

    # Receive message from resume group
    async def resume_message(self, event):
        message = event["message"]

        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": message}))
