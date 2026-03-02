from __future__ import annotations

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication


@database_sync_to_async
def _get_user_for_token(raw_token: str):
    authenticator = JWTAuthentication()
    validated = authenticator.get_validated_token(raw_token)
    return authenticator.get_user(validated)


class JwtQueryAuthMiddleware:
    """
    WebSocket auth middleware using SimpleJWT access token from query string:
    ws://.../ws/tenders/{kind}/{id}/?token=<access_token>
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        scope["user"] = AnonymousUser()
        try:
            query_string = scope.get("query_string", b"").decode("utf-8")
            token = (parse_qs(query_string).get("token") or [None])[0]
            if token:
                scope["user"] = await _get_user_for_token(token)
        except Exception:
            scope["user"] = AnonymousUser()
        return await self.inner(scope, receive, send)
