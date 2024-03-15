from django.urls import path

from resume import consumers

websocket_urlpatterns = [
    path("ws/resume/<resume_id>/", consumers.ResumeConsumer.as_asgi()),
]
