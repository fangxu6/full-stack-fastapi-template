from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from jwt.types import Options
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from app.core.config import settings
from app.schemas.security import AccessTokenPayload, PasswordTokenPayload

password_hash = PasswordHash(
    (
        Argon2Hasher(),
        BcryptHasher(),
    )
)


ALGORITHM = "HS256"


JWT_REQUIRED_CLAIMS = ("sub", "sid", "typ", "iss", "aud", "iat", "nbf", "exp")
PASSWORD_JWT_REQUIRED_CLAIMS = (
    "sub",
    "typ",
    "iss",
    "aud",
    "iat",
    "nbf",
    "exp",
    "version",
)


def _decode(
    token: str,
    *,
    secret: str,
    required_claims: tuple[str, ...],
    verify_exp: bool = True,
) -> dict[str, Any]:
    options: Options = {
        "require": list(required_claims),
        "verify_exp": verify_exp,
        "verify_iat": True,
        "verify_nbf": True,
    }
    return jwt.decode(
        token,
        secret,
        algorithms=[ALGORITHM],
        audience=settings.JWT_AUDIENCE,
        issuer=settings.JWT_ISSUER,
        options=options,
    )


def create_access_token(
    *, subject: str | Any, session_id: str | Any, expires_delta: timedelta
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(subject),
        "sid": str(session_id),
        "typ": "access",
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": now,
        "nbf": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.ACCESS_TOKEN_SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(
    token: str, *, allow_expired: bool = False
) -> AccessTokenPayload:
    payload = _decode(
        token,
        secret=settings.ACCESS_TOKEN_SECRET_KEY,
        required_claims=JWT_REQUIRED_CLAIMS,
        verify_exp=not allow_expired,
    )
    return AccessTokenPayload.model_validate(payload)


def create_password_token(
    *,
    subject: str | Any,
    purpose: Literal["password_reset", "password_setup"],
    version: int,
    expires_delta: timedelta,
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(subject),
        "typ": purpose,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": now,
        "nbf": now,
        "exp": now + expires_delta,
        "version": version,
    }
    return jwt.encode(payload, settings.PASSWORD_TOKEN_SECRET_KEY, algorithm=ALGORITHM)


def decode_password_token(token: str) -> PasswordTokenPayload:
    payload = _decode(
        token,
        secret=settings.PASSWORD_TOKEN_SECRET_KEY,
        required_claims=PASSWORD_JWT_REQUIRED_CLAIMS,
    )
    return PasswordTokenPayload.model_validate(payload)


def verify_password(
    plain_password: str, hashed_password: str
) -> tuple[bool, str | None]:
    return password_hash.verify_and_update(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)
