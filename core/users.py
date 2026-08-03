import os
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers
from fastapi.responses import RedirectResponse
from fastapi_users.authentication import (
    AuthenticationBackend,
    CookieTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from httpx_oauth.clients.google import GoogleOAuth2

from core.config import settings
from core.database import get_session
from core.orm import User, OAuthAccount

SECRET = settings.USER_SECRET


_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


class OAuthNotAllowedError(Exception):
    """Raised when an authenticated Google account isn't on ALLOWED_EMAILS."""


def _is_email_allowed(email: str) -> bool:
    """Reads ALLOWED_EMAILS fresh from .env on every call instead of the
    cached `settings` singleton, so editing the allowlist takes effect on the
    next login attempt -- no process restart needed. Falls back to the
    process environment if .env isn't present (e.g. vars injected directly
    into the container instead of a mounted file -- that path still needs a
    restart to pick up changes)."""
    raw = dotenv_values(_ENV_PATH).get("ALLOWED_EMAILS") or os.environ.get("ALLOWED_EMAILS", "")
    allowed = {e.strip().lower() for e in raw.split(",") if e.strip()}
    if not allowed:
        return True
    return email.strip().lower() in allowed


class CustomGoogleOAuth2(GoogleOAuth2):
    async def get_id_email(self, token: str):
        try:
            return await super().get_id_email(token)
        except Exception as e:
            if hasattr(e, "response"):
                print(f"Google API Error Response: {e.response.text}")
            raise e


google_oauth_client = CustomGoogleOAuth2(
    settings.GOOGLE_CLIENT_ID,
    settings.GOOGLE_CLIENT_SECRET,
)


class UserManager(BaseUserManager[User, str]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    def parse_id(self, value: Any) -> str:
        return str(value)

    async def oauth_callback(
        self,
        oauth_name: str,
        access_token: str,
        account_id: str,
        account_email: str,
        expires_at: int | None = None,
        refresh_token: str | None = None,
        request: Request | None = None,
        *,
        associate_by_email: bool = False,
        is_verified_by_default: bool = False,
    ):
        if not _is_email_allowed(account_email):
            print(f"OAuth callback rejected: {account_email} is not on the allowlist")
            raise OAuthNotAllowedError(account_email)

        print(f"OAuth callback started for {account_email}")
        try:
            result = await super().oauth_callback(
                oauth_name,
                access_token,
                account_id,
                account_email,
                expires_at,
                refresh_token,
                request,
                associate_by_email=associate_by_email,
                is_verified_by_default=is_verified_by_default,
            )

            # If the user doesn't have a name, extract it from the email
            if not result.name and result.email:
                extracted_name = result.email.split("@")[0]
                print(f"Extracting name '{extracted_name}' from email '{result.email}'")
                result = await self.user_db.update(result, {"name": extracted_name})

            print(f"OAuth callback success for user: {result.id}")
            return result
        except Exception as e:
            print(f"OAuth callback error: {type(e).__name__}: {str(e)}")
            raise e


async def get_user_db(session=Depends(get_session)):
    yield SQLAlchemyUserDatabase(session, User, OAuthAccount)


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


cookie_transport = CookieTransport(
    cookie_max_age=3600,
    cookie_name="hackerearth_auth",
    cookie_secure=settings.ENVIRONMENT == "production",
    cookie_samesite="none" if settings.ENVIRONMENT == "production" else "lax",
)


class RedirectCookieTransport(CookieTransport):
    """CookieTransport that redirects to a URL after login (for OAuth flows)."""

    def __init__(self, redirect_url: str, **kwargs):
        super().__init__(**kwargs)
        self.redirect_url = redirect_url

    async def get_login_response(self, token: str) -> RedirectResponse:
        response = RedirectResponse(self.redirect_url, status_code=302)
        return self._set_login_cookie(response, token)


oauth_cookie_transport = RedirectCookieTransport(
    redirect_url=settings.FRONTEND_URL,
    cookie_max_age=3600,
    cookie_name="hackerearth_auth",
    cookie_secure=settings.ENVIRONMENT == "production",
    cookie_samesite="none" if settings.ENVIRONMENT == "production" else "lax",
)


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)


auth_backend = AuthenticationBackend(
    name="cookie",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

oauth_auth_backend = AuthenticationBackend(
    name="oauth-cookie",
    transport=oauth_cookie_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, str](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)
current_active_user_optional = fastapi_users.current_user(optional=True, active=True)