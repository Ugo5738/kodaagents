import jwt
from django.conf import settings
from django.views.generic import CreateView, ListView, View
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status, viewsets
from rest_framework.decorators import api_view
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import OrganizationCustomer, User
from accounts.pagination import CustomPageNumberPagination
from accounts.serializers import (
    ChangePasswordSerializer,
    RegisterSerializer,
    UserSerializer,
)

# LoginSerializer,


class RegisterAPIView(GenericAPIView):
    """
    API endpoint that allows users to be created.

    Expected payload:
    {
        "password": "password",
        "first_name": "John",
        "last_name": "Doe",
        "email": "johndoe@example.com",
        "profile": {
            "country": "NG"
        }
    }
    """

    serializer_class = RegisterSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.email_verified = False  # Set email_verified to False initially
            user.save()

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserView(APIView):
    def get(self, request):
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


class LogoutAPIView(APIView):
    def post(self, request):
        response = Response()
        response.delete_cookie("jwt")
        response.data = {"message": "success"}
        return response


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


class CurrentUserDetailView(APIView):
    """
    An endpoint to get the current logged in users' details.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data)


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


class UserListView(ListView):
    template_name = (
        "clarify/users.html"  # This should be changed to the appropriate page
    )
    queryset = User.objects.all()

    # If you need to pass additional context data to the template
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add extra context variables if needed
        return context


# DELETE THIS AS IT IS NOT NEEDED
class OrganizationCustomerListView(ListView):
    template_name = "clarify/users.html"
    queryset = OrganizationCustomer.objects.all()

    # If you need to pass additional context data to the template
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add extra context variables if needed
        return context
