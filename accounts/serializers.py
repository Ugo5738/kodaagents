from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers

from accounts import models


class OrganizationProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.OrganizationProfile
        # fields = '__all__'
        fields = ["name", "country"]  # added to registration form


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(max_length=128, min_length=6, write_only=True)
    organization_profile = OrganizationProfileSerializer(write_only=True)

    class Meta:
        model = models.User
        # fields = '__all__'
        exclude = ["groups", "user_permissions"]

    def create(self, validated_data):
        profile_data = validated_data.pop("organization_profile")
        user = models.User.objects.create_user(**validated_data)
        models.OrganizationProfile.objects.create(user=user, **profile_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    user_role = serializers.CharField(source="get_user_role", read_only=True)

    class Meta:
        model = models.User
        # fields = '__all__'
        exclude = ["password", "phone_verified", "groups", "user_permissions"]


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for password change endpoint.
    """

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class ResetPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
