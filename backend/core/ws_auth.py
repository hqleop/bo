from __future__ import annotations

from urllib.parse import parse_qs
from http.cookies import SimpleCookie

from channels.db import database_sync_to_async
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication


@database_sync_to_async
def _get_user_for_token(raw_token: str):
    authenticator = JWTAuthentication()
    validated = authenticator.get_validated_token(raw_token)
    return authenticator.get_user(validated)


class JwtQueryAuthMiddleware:
    """
    WebSocket auth middleware using SimpleJWT access token from one of:
    1) Authorization header: Bearer <access_token>
    2) Cookie: access_token=<access_token>
    3) Query string (legacy, optional): ?token=<access_token>
    """

    def __init__(self, inner):
        self.inner = inner

    @staticmethod
    def _extract_query_token(scope) -> str | None:
        query_string = scope.get("query_string", b"").decode("utf-8")
        return (parse_qs(query_string).get("token") or [None])[0]

    @staticmethod
    def _extract_bearer_token(scope) -> str | None:
        for key, value in scope.get("headers", []):
            if key == b"authorization":
                raw = value.decode("utf-8").strip()
                if raw.lower().startswith("bearer "):
                    return raw[7:].strip() or None
        return None

    @staticmethod
    def _extract_cookie_token(scope) -> str | None:
        for key, value in scope.get("headers", []):
            if key != b"cookie":
                continue
            cookie = SimpleCookie()
            cookie.load(value.decode("utf-8", errors="ignore"))
            morsel = cookie.get("access_token")
            if morsel and morsel.value:
                return morsel.value
        return None

    async def __call__(self, scope, receive, send):
        scope["user"] = AnonymousUser()
        try:
            token = self._extract_bearer_token(scope) or self._extract_cookie_token(scope)
            if not token and getattr(settings, "WS_ALLOW_QUERY_TOKEN", False):
                token = self._extract_query_token(scope)
            if token:
                scope["user"] = await _get_user_for_token(token)
        except Exception:
            scope["user"] = AnonymousUser()
        return await self.inner(scope, receive, send)
