import jwt
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from django.conf import settings
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django_filters.rest_framework import DjangoFilterBackend
from google.auth.transport import requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from rest_framework import filters, generics, status, viewsets
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.views import TokenObtainPairView

from accounts import serializers
from accounts.models import GoogleToken, LoginHistory, User, UserTier
from accounts.pagination import CustomPageNumberPagination
from accounts.serializers import (
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    UserSerializer,
)
from helpers.email_utils import send_verification_email
from koda.config.logging_config import configure_logger
from payment.models import Subscription

logger = configure_logger(__name__)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class GetCSRFToken(APIView):
    def get(self, request):
        return JsonResponse({"success": "CSRF cookie set"})


class RegisterAPIView(GenericAPIView):
    """
    API endpoint that allows users to be created.

    Expected payload:
    {
        "password": "password",
        "first_name": "John",
        "last_name": "Doe",
        "email": "johndoe@example.com",
        "country": "NG"
    }
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = RegisterSerializer

    def post(self, request: Request) -> Response:
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            # Fetch the "free" tier
            tier = UserTier.objects.get(name=UserTier.FREE)

            user = serializer.save()
            user.email_verified = False  # Set email_verified to False initially
            user.email_verification_token = get_random_string(64)
            user.tier = tier  # Assign the "free" tier to the user
            user.save()

            # Send verification email
            verification_link = (
                f"{settings.FRONTEND_BASE_URL}/verify-email/{user.email_verification_token}"
            )
            email_response = send_verification_email(user.email, verification_link)

            if email_response.status_code == 200:
                return Response(
                    {
                        "message": "User registered successfully. Please check your email to verify your account.",
                        "user_id": user.id,
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {
                        "message": "User registered successfully, but there was an issue sending the verification email. Please try again later.",
                        "user_id": user.id,
                    },
                    status=status.HTTP_201_CREATED,
                )
        else:
            print("Data not valid")
            errors = {}
            for field, field_errors in serializer.errors.items():
                errors[field] = field_errors[0]  # Take the first error message for each field

            if "email" in errors and "unique" in errors["email"].lower():
                errors["email"] = "A user with this email already exists."

            if "password" in errors:
                if "too short" in errors["password"].lower():
                    errors["password"] = (
                        "Password is too short. It must be at least 8 characters long."
                    )
                elif "too common" in errors["password"].lower():
                    errors["password"] = (
                        "This password is too common. Please choose a more unique password."
                    )
                elif "entirely numeric" in errors["password"].lower():
                    errors["password"] = "Password cannot be entirely numeric."

            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)


class VerifyEmailView(APIView):
    def get(self, request, token):
        try:
            user = User.objects.get(email_verification_token=token)
            user.email_verified = True
            # user.email_verification_token = ''
            user.save()
            return Response({"message": "Email verified successfully"}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"message": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)


class ResendVerificationEmailView(APIView):
    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
            if user.email_verified:
                return Response(
                    {"message": "Email is already verified"}, status=status.HTTP_400_BAD_REQUEST
                )

            user.email_verification_token = get_random_string(64)
            user.save()

            verification_link = (
                f"{settings.FRONTEND_BASE_URL}/verify-email/{user.email_verification_token}"
            )
            email_response = send_verification_email(user.email, verification_link)

            if email_response.status_code == 200:
                return Response(
                    {"message": "Verification email resent successfully"}, status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"message": "Failed to resend verification email"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        except User.DoesNotExist:
            return Response(
                {"error": "User with this email does not exist"}, status=status.HTTP_404_NOT_FOUND
            )


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class GoogleAuthView(APIView):
    def post(self, request):
        logger.info("Received Google Auth request")
        credential = request.data.get("credential")
        try:
            # Specify the CLIENT_ID of the app that accesses the backend:
            idinfo = id_token.verify_oauth2_token(
                credential, requests.Request(), settings.GOOGLE_CLIENT_ID
            )

            # ID token is valid. Get the user's Google Account ID from the decoded token.
            userid = idinfo["sub"]
            email = idinfo["email"]
            name = idinfo.get("name", "")

            # Check if this Google account already exists
            user = User.objects.filter(email=email).first()

            if user is None:
                logger.info(f"Creating new user for email: {email}")
                tier = UserTier.objects.get(name=UserTier.FREE)
                user = User.objects.create_user(
                    email=email,
                    username=(
                        name.split()[0] if name else ""
                    ),  # We might want to generate a unique username
                    first_name=name.split()[0] if name else "",
                    last_name=" ".join(name.split()[1:]) if name else "",
                    email_verified=True,
                    tier=tier,  # Assign the "free" tier to the new user
                )
                user.auth_provider = "google"
                user.set_unusable_password()
                user.save()
                logger.info(f"New user created: {user.id}")
            else:
                logger.info(f"Existing user found: {user.id}")

                user.auth_provider = "google"
                user.save()

                # Check if the user has a tier assigned
                if user.tier is None:
                    # Fetch the "free" tier and assign it to the user
                    tier = UserTier.objects.get(name=UserTier.FREE)
                    user.tier = tier
                    user.save()

            # Update last_login time
            user.last_login = timezone.now()
            user.save(update_fields=["last_login"])

            # Record login history
            LoginHistory.objects.create(
                user=user,
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT"),
            )

            # Update the session hash
            update_session_auth_hash(request, user)

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            return Response(
                {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": {
                        "email": user.email,
                        "name": user.get_full_name(),
                    },
                }
            )
        except PermissionDenied as e:
            logger.error(f"Permission Denied: {str(e)}")
            return Response(
                {"error": "Permission denied", "details": str(e)}, status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return Response(
                {"error": "An unexpected error occurred", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserTierViewSet(viewsets.ModelViewSet):
    queryset = UserTier.objects.all()
    serializer_class = serializers.UserTierSerializer
    permission_classes = [IsAdminUser]  # Only admins can manage tiers


class UserPaymentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        subscription = Subscription.objects.filter(
            user=user, status__in=["active", "trialing"], canceled_at__isnull=True
        ).first()
        next_billing_date = subscription.current_period_end if subscription else None

        return Response(
            {
                "tier": user.tier.name if user.tier else "No active subscription",
                "download_count": user.download_count,
                "creation_count": user.creation_count,
                "customization_count": user.customization_count,
                "remaining_uses": {
                    "download": user.get_remaining_uses("download"),
                    "creation": user.get_remaining_uses("creation"),
                    "customization": user.get_remaining_uses("customization"),
                },
                "needs_payment": user.needs_payment(),
                "next_billing_date": next_billing_date,
            }
        )


class UpdateDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        user.download_count += 1
        user.save()

        if not user.is_paid and user.download_count > user.free_usage_limit:
            return Response({"error": "Usage limit reached"}, status=status.HTTP_403_FORBIDDEN)

        return Response({"success": True, "download_count": user.download_count})


class ResetUsageCountsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        # Decrement counts if they're greater than 0
        if user.creation_count > 0:
            user.creation_count -= 1
        if user.customization_count > 0:
            user.customization_count -= 1

        user.save()

        return Response(
            {
                "success": True,
                "creation_count": user.creation_count,
                "customization_count": user.customization_count,
            }
        )


class LoginView(APIView):
    def post(self, request: Request) -> Response:
        email = request.data.get("email")
        password = request.data.get("password")

        if not email:
            return Response(
                {"errors": {"email": ["Email is required"]}}, status=status.HTTP_400_BAD_REQUEST
            )
        if not password:
            return Response(
                {"errors": {"password": ["Password is required"]}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(email=email, password=password)

        if user is not None:
            if not user.email_verified:
                return Response(
                    {"errors": {"email": ["Please verify your email before logging in"]}},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            )

        user_exists = User.objects.filter(email=email).exists()
        if user_exists:
            return Response(
                {"errors": {"password": ["Invalid password"]}}, status=status.HTTP_401_UNAUTHORIZED
            )
        else:
            return Response(
                {"errors": {"email": ["No account found with this email"]}},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh_token")
            if not refresh_token:
                return Response(
                    {"error": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST
                )

            token = RefreshToken(refresh_token)
            token.blacklist()

            # Record logout time
            last_login = LoginHistory.objects.filter(
                user=request.user, logout_time__isnull=True
            ).first()
            if last_login:
                last_login.logout_time = timezone.now()
                last_login.save()

            return Response(status=status.HTTP_205_RESET_CONTENT)
        except TokenError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print("This is the error", e)
            return Response(
                {"error": "An unexpected error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = settings.FRONTEND_BASE_URL
    client_class = OAuth2Client


def google_auth(request):
    # # Use this if you have a client_secret.json file
    # flow = Flow.from_client_secrets_file(
    #     'path/to/your/client_secret.json',
    #     scopes=['https://www.googleapis.com/auth/gmail.send'],
    #     redirect_uri='urn:ietf:wg:oauth:2.0:oob')

    # If you don't have the file, use this instead:
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                # "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=["https://www.googleapis.com/auth/gmail.send", "openid", "profile", "email"],
    )
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI

    authorization_url, _ = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent"
    )
    return redirect(authorization_url)


def google_callback(request):
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=["https://www.googleapis.com/auth/gmail.send", "openid", "profile", "email"],
    )
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI

    flow.fetch_token(code=request.GET.get("code"))

    credentials = flow.credentials

    # admin_user = User.objects.get(username='admin')
    userinfo_client = build("oauth2", "v2", credentials=credentials)
    user_info = userinfo_client.userinfo().get().execute()

    user, created = User.objects.get_or_create(email=user_info["email"])
    if created:
        user.first_name = user_info.get("given_name", "")
        user.last_name = user_info.get("family_name", "")
        user.email_verified = True  # User is verified through Google
        user.save()

    # Convert credentials.expiry to an aware datetime
    if credentials.expiry.tzinfo is None:
        aware_expiry = timezone.make_aware(credentials.expiry)
    else:
        aware_expiry = credentials.expiry

    google_token, _ = GoogleToken.objects.update_or_create(
        user=user,
        defaults={
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "expires_at": max(aware_expiry, timezone.now()),
            "email": user_info["email"],
            "scopes": ",".join(credentials.scopes),
        },
    )

    # Log the user in
    login(request, user)

    return redirect(settings.FRONTEND_BASE_URL)


class CurrentUserDetailView(APIView):
    """
    An endpoint to get the current logged in users' details.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(generics.UpdateAPIView):
    """
    An endpoint for changing password.
    """

    serializer_class = ChangePasswordSerializer
    model = User
    permission_classes = (IsAuthenticated,)

    def get_object(self, queryset=None):
        return self.request.user

    def update(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            # Check old password
            if not self.object.check_password(serializer.data.get("old_password")):
                return Response(
                    {"old_password": ["Wrong password."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # set_password also hashes the password that the user will get
            self.object.set_password(serializer.data.get("new_password"))
            self.object.save()

            response = {
                "status": "success",
                "code": status.HTTP_200_OK,
                "message": "Password updated successfully",
            }

            return Response(response)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if user.check_password(serializer.data.get("old_password")):
                user.set_password(serializer.data.get("new_password"))
                user.save()
                return Response(
                    {"message": "Password changed successfully."}, status=status.HTTP_200_OK
                )
            return Response(
                {"error": "Incorrect old password."}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        user.delete()
        return Response({"message": "Account deleted successfully."}, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed, edited and searched.
    """

    queryset = User.objects.exclude(is_superuser=True)
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    lookup_field = "id"
    filterset_fields = ["id", "username", "email"]
    search_fields = ["id", "username", "email"]
    ordering_fields = ["id", "username", "email"]


class UserView(APIView):
    def get(self, request: Request) -> Response:
        token = request.COOKIES.get("jwt")

        if not token:
            raise AuthenticationFailed("Unauthenticated")

        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Authentication Expired")

        user = User.objects.filter(id=payload["id"]).first()
        serializer = UserSerializer(user)
        return Response(serializer.data)
