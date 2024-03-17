import os
import django
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from decouple import config
from django.core.asgi import get_asgi_application

# Set the default Django settings module for the 'asgi' application.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", config("DJANGO_SETTINGS_MODULE"))

# Setup Django before loading the application.
django.setup()

# Import the WebSocket routing definitions from each app after Django has been set up.
from assistant.routing import websocket_urlpatterns as assistant_websocket_urlpatterns
from resume.routing import websocket_urlpatterns as resume_websocket_urlpatterns

# Combine all the WebSocket URL patterns.
websocket_urlpatterns = assistant_websocket_urlpatterns + resume_websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": get_asgi_application(),  # Define the ASGI application to use for HTTP protocols.
    "websocket": AuthMiddlewareStack(  # Define the ASGI application to use for WebSocket protocols.
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
