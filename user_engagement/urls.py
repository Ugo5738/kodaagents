from django.urls import path

from user_engagement import views

urlpatterns = [
    path("mailgun/inbound/", views.MailgunInboundEmailView.as_view(), name="mailgun_inbound"),
    path("feedback/", views.FeedbackAPIView.as_view(), name="feedback"),
    path("attachments/<int:attachment_id>/", views.serve_attachment, name="serve_attachment"),
]
