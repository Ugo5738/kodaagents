import os

import django
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from decouple import config
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", config("DJANGO_SETTINGS_MODULE"))

# Setup Django before loading the application.
django.setup()

# Import the routing after Django has been set up.
import assistant.routing

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),  # Define the ASGI application to use for HTTP protocols.
        "websocket": AuthMiddlewareStack(  # Define the ASGI application to use for WebSocket protocols.
            URLRouter(
                assistant.routing.websocket_urlpatterns  # Use the WebSocket URL routing defined in assistant.routing.
            )
        ),
    }
)
