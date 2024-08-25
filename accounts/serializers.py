from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from accounts import models


class OrganizationProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.OrganizationProfile
        # fields = '__all__'
        fields = ["name", "country"]  # added to registration form


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    country = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = models.User
        fields = ['email', 'password', 'country', 'first_name', 'last_name']
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
        }

    def create(self, validated_data):
        country = validated_data.pop('country', None)
        user = models.User.objects.create_user(**validated_data)
        if country:
            models.OrganizationProfile.objects.create(user=user, country=country)
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        # Update last_login time
        self.user.last_login = timezone.now()
        self.user.save(update_fields=['last_login'])

        # Record login history
        models.LoginHistory.objects.create(
            user=self.user,
            ip_address=self.context['request'].META.get('REMOTE_ADDR'),
            user_agent=self.context['request'].META.get('HTTP_USER_AGENT')
        )

        return data


class LoginHistorySerializer(serializers.ModelSerializer):
    session_duration = serializers.SerializerMethodField()

    class Meta:
        model = models.LoginHistory
        fields = ['login_time', 'logout_time', 'ip_address', 'user_agent', 'session_duration']

    def get_session_duration(self, obj):
        if obj.session_duration:
            return str(obj.session_duration)
        return None


class UserTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.UserTier
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    user_role = serializers.CharField(source="get_user_role", read_only=True)
    country = serializers.CharField(source='organization_profile.country', read_only=True)
    region = serializers.CharField(source='organization_profile.city', read_only=True)  # Using city as region

    class Meta:
        model = models.User
        fields = ['email', 'full_name', 'user_role', 'country', 'region']


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for password change endpoint.
    """

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class ResetPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
