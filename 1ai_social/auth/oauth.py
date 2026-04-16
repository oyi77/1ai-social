"""OAuth 2.0 integration for Google and GitHub login.

Provides secure OAuth authentication with:
- Google OAuth (OpenID Connect)
- GitHub OAuth
- State parameter for CSRF protection
- Encrypted token storage
- Automatic user creation on first login
"""

import os
import secrets
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from sqlalchemy import create_engine, select, update, delete
from sqlalchemy.orm import sessionmaker, Session

from ..secrets import get_secret, get_required_secret
from ..encryption import encrypt_token, decrypt_token
from ..db_models import Base

logger = logging.getLogger(__name__)


class OAuthProvider:
    GOOGLE = "google"
    GITHUB = "github"


class OAuthError(Exception):
    pass


class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"

    from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey

    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), nullable=False)
    tenant_id = Column(String(255), nullable=False)
    provider = Column(String(50), nullable=False)
    provider_account_id = Column(String(255), nullable=False)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"


_state_store: Dict[str, Dict[str, Any]] = {}


def _generate_state() -> str:
    return secrets.token_urlsafe(32)


def _store_state(state: str, provider: str, redirect_uri: str) -> None:
    _state_store[state] = {
        "provider": provider,
        "redirect_uri": redirect_uri,
        "created_at": datetime.now(timezone.utc),
    }


def _verify_state(state: str, provider: str) -> bool:
    if state not in _state_store:
        return False

    stored = _state_store[state]
    if stored["provider"] != provider:
        return False

    age = datetime.now(timezone.utc) - stored["created_at"]
    if age > timedelta(minutes=10):
        del _state_store[state]
        return False

    del _state_store[state]
    return True


def get_oauth_url(provider: str, redirect_uri: str) -> str:
    state = _generate_state()
    _store_state(state, provider, redirect_uri)

    if provider == OAuthProvider.GOOGLE:
        client_id = get_required_secret("GOOGLE_CLIENT_ID")
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    elif provider == OAuthProvider.GITHUB:
        client_id = get_required_secret("GITHUB_CLIENT_ID")
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "read:user user:email",
            "state": state,
        }
        return f"{GITHUB_AUTH_URL}?{urlencode(params)}"

    else:
        raise OAuthError(f"Unsupported provider: {provider}")


async def handle_callback(
    provider: str, code: str, state: str, redirect_uri: str
) -> Dict[str, Any]:
    if not _verify_state(state, provider):
        raise OAuthError("Invalid or expired state parameter")

    if provider == OAuthProvider.GOOGLE:
        return await _handle_google_callback(code, redirect_uri)
    elif provider == OAuthProvider.GITHUB:
        return await _handle_github_callback(code, redirect_uri)
    else:
        raise OAuthError(f"Unsupported provider: {provider}")


async def _handle_google_callback(code: str, redirect_uri: str) -> Dict[str, Any]:
    client_id = get_required_secret("GOOGLE_CLIENT_ID")
    client_secret = get_required_secret("GOOGLE_CLIENT_SECRET")

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )

        if token_response.status_code != 200:
            raise OAuthError(f"Token exchange failed: {token_response.text}")

        token_data = token_response.json()
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)

        user_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if user_response.status_code != 200:
            raise OAuthError(f"Failed to fetch user info: {user_response.text}")

        user_data = user_response.json()

        return {
            "provider": OAuthProvider.GOOGLE,
            "provider_account_id": user_data["id"],
            "email": user_data["email"],
            "name": user_data.get("name"),
            "picture": user_data.get("picture"),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=expires_in),
        }


async def _handle_github_callback(code: str, redirect_uri: str) -> Dict[str, Any]:
    client_id = get_required_secret("GITHUB_CLIENT_ID")
    client_secret = get_required_secret("GITHUB_CLIENT_SECRET")

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
        )

        if token_response.status_code != 200:
            raise OAuthError(f"Token exchange failed: {token_response.text}")

        token_data = token_response.json()
        access_token = token_data["access_token"]

        user_response = await client.get(
            GITHUB_USER_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )

        if user_response.status_code != 200:
            raise OAuthError(f"Failed to fetch user info: {user_response.text}")

        user_data = user_response.json()

        return {
            "provider": OAuthProvider.GITHUB,
            "provider_account_id": str(user_data["id"]),
            "email": user_data.get("email"),
            "name": user_data.get("name") or user_data["login"],
            "username": user_data["login"],
            "picture": user_data.get("avatar_url"),
            "access_token": access_token,
            "refresh_token": None,
            "expires_at": None,
        }


def _get_db_session() -> Session:
    database_url = get_required_secret("DATABASE_URL")
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def link_account(user_id: str, tenant_id: str, account_data: Dict[str, Any]) -> None:
    db = _get_db_session()
    try:
        encrypted_access_token = encrypt_token(account_data["access_token"])
        encrypted_refresh_token = (
            encrypt_token(account_data["refresh_token"])
            if account_data.get("refresh_token")
            else None
        )

        existing = db.execute(
            select(OAuthAccount).where(
                OAuthAccount.provider == account_data["provider"],
                OAuthAccount.provider_account_id == account_data["provider_account_id"],
            )
        ).scalar_one_or_none()

        if existing:
            db.execute(
                update(OAuthAccount)
                .where(OAuthAccount.id == existing.id)
                .values(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    access_token=encrypted_access_token,
                    refresh_token=encrypted_refresh_token,
                    expires_at=account_data.get("expires_at"),
                    updated_at=datetime.now(timezone.utc),
                )
            )
        else:
            oauth_account = OAuthAccount(
                user_id=user_id,
                tenant_id=tenant_id,
                provider=account_data["provider"],
                provider_account_id=account_data["provider_account_id"],
                access_token=encrypted_access_token,
                refresh_token=encrypted_refresh_token,
                expires_at=account_data.get("expires_at"),
            )
            db.add(oauth_account)

        db.commit()
        logger.info(f"Linked {account_data['provider']} account for user {user_id}")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to link account: {e}")
        raise OAuthError(f"Failed to link account: {e}")
    finally:
        db.close()


def unlink_account(user_id: str, provider: str) -> None:
    db = _get_db_session()
    try:
        db.execute(
            delete(OAuthAccount).where(
                OAuthAccount.user_id == user_id,
                OAuthAccount.provider == provider,
            )
        )
        db.commit()
        logger.info(f"Unlinked {provider} account for user {user_id}")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to unlink account: {e}")
        raise OAuthError(f"Failed to unlink account: {e}")
    finally:
        db.close()
