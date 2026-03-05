"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_asgi_app = get_asgi_application()

try:
    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.security.websocket import AllowedHostsOriginValidator
    from core.routing import websocket_urlpatterns
    from core.ws_auth import JwtQueryAuthMiddleware

    application = ProtocolTypeRouter(
        {
            "http": django_asgi_app,
            "websocket": AllowedHostsOriginValidator(
                JwtQueryAuthMiddleware(
                    URLRouter(websocket_urlpatterns)
                )
            ),
        }
    )
except ModuleNotFoundError as exc:
    # Fallback mode only when channels package is absent.
    if exc.name and exc.name.startswith("channels"):
        application = django_asgi_app
    else:
        raise
