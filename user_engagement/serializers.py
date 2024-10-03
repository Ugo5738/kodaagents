from rest_framework import serializers

from user_engagement.models import Feedback


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ["subject", "body"]
