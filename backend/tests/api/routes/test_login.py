import jwt
from fastapi.testclient import TestClient
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlmodel import Session, select

from app.core import security
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.crud import create_user
from app.models import AuthSession, EmailOutbox, EmailOutboxKind, User
from app.schemas.user import UserCreate
from app.utils import generate_password_reset_token
from tests.utils.user import user_authentication_headers
from tests.utils.utils import random_email, random_lower_string


def test_get_access_token(client: TestClient) -> None:
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    tokens = r.json()
    assert r.status_code == 200
    assert "access_token" in tokens
    assert tokens["access_token"]


def test_get_access_token_incorrect_password(client: TestClient) -> None:
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": "incorrect",
    }
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    assert r.status_code == 400
    payload = r.json()
    assert payload["detail"] == "Incorrect email or password"
    assert payload["request_id"]


def test_system_actor_cannot_log_in_or_use_an_existing_token(
    client: TestClient, db: Session
) -> None:
    from app.core.audit import ensure_system_actor

    password = "system-actor-password"
    system_actor = ensure_system_actor(session=db)
    system_actor.hashed_password = get_password_hash(password)
    db.add(system_actor)
    db.commit()

    login = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": system_actor.email, "password": password},
    )
    assert login.status_code == 400
    assert login.json()["detail"] == "Incorrect email or password"

    token = jwt.encode(
        {"sub": str(system_actor.id)},
        settings.SECRET_KEY,
        algorithm=security.ALGORITHM,
    )
    token_response = client.post(
        f"{settings.API_V1_STR}/login/test-token",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert token_response.status_code == 401
    assert token_response.json()["detail"] == "Could not validate credentials"


def test_use_access_token(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/login/test-token",
        headers=superuser_token_headers,
    )
    result = r.json()
    assert r.status_code == 200
    assert "email" in result


def test_login_issues_session_bound_access_token(
    client: TestClient, db: Session
) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={
            "username": settings.FIRST_SUPERUSER,
            "password": settings.FIRST_SUPERUSER_PASSWORD,
        },
    )
    token = response.json()["access_token"]
    payload = jwt.decode(
        token,
        settings.ACCESS_TOKEN_SECRET_KEY,
        algorithms=[security.ALGORITHM],
        audience=settings.JWT_AUDIENCE,
        issuer=settings.JWT_ISSUER,
    )

    assert response.status_code == 200
    assert {
        "sub",
        "sid",
        "typ",
        "iss",
        "aud",
        "iat",
        "nbf",
        "exp",
    } <= payload.keys()
    auth_session = db.get(AuthSession, payload["sid"])
    assert auth_session is not None
    assert str(auth_session.user_id) == payload["sub"]


def test_logout_revokes_only_the_current_session(
    client: TestClient, db: Session
) -> None:
    email = random_email()
    password = random_lower_string()
    user = create_user(
        session=db,
        user_create=UserCreate(email=email, password=password, is_active=True),
    )
    db.commit()
    first = user_authentication_headers(client=client, email=email, password=password)
    second = user_authentication_headers(client=client, email=email, password=password)

    first_logout = client.post(f"{settings.API_V1_STR}/login/logout", headers=first)
    repeated_logout = client.post(f"{settings.API_V1_STR}/login/logout", headers=first)

    assert first_logout.status_code == 200
    assert repeated_logout.status_code == 200
    assert (
        client.post(
            f"{settings.API_V1_STR}/login/test-token", headers=first
        ).status_code
        == 401
    )
    assert (
        client.post(
            f"{settings.API_V1_STR}/login/test-token", headers=second
        ).status_code
        == 200
    )
    sessions = db.exec(select(AuthSession).where(AuthSession.user_id == user.id)).all()
    assert len(sessions) == 2
    assert sum(session.revoked_at is not None for session in sessions) == 1


def test_access_token_rejects_missing_or_wrong_claims_without_new_sessions(
    client: TestClient, db: Session
) -> None:
    login = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={
            "username": settings.FIRST_SUPERUSER,
            "password": settings.FIRST_SUPERUSER_PASSWORD,
        },
    )
    assert login.status_code == 200
    valid_token = login.json()["access_token"]
    payload = jwt.decode(valid_token, options={"verify_signature": False})
    session_count = len(db.exec(select(AuthSession)).all())

    invalid_payloads = (
        {key: value for key, value in payload.items() if key != "sid"},
        payload | {"iss": "wrong-issuer"},
        payload | {"aud": "wrong-audience"},
        payload | {"typ": "password_reset"},
    )
    for invalid_payload in invalid_payloads:
        token = jwt.encode(
            invalid_payload,
            settings.ACCESS_TOKEN_SECRET_KEY,
            algorithm=security.ALGORITHM,
        )
        response = client.post(
            f"{settings.API_V1_STR}/login/test-token",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401

    assert len(db.exec(select(AuthSession)).all()) == session_count


def test_recovery_password(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    email = "test@example.com"
    r = client.post(
        f"{settings.API_V1_STR}/password-recovery/{email}",
        headers=normal_user_token_headers,
    )
    assert r.status_code == 200
    assert r.json() == {
        "message": "If that email is registered, we sent a password recovery link"
    }


def test_recovery_password_queues_an_outbox_row(
    client: TestClient, db: Session
) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/password-recovery/{settings.FIRST_SUPERUSER}"
    )

    assert response.status_code == 200
    db.expire_all()
    outbox = db.exec(
        select(EmailOutbox).where(EmailOutbox.recipient == settings.FIRST_SUPERUSER)
    ).one()
    assert outbox.kind is EmailOutboxKind.PASSWORD_RECOVERY
    assert outbox.subject is None
    assert outbox.html_content is None


def test_recovery_password_user_not_exits(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    email = "jVgQr@example.com"
    r = client.post(
        f"{settings.API_V1_STR}/password-recovery/{email}",
        headers=normal_user_token_headers,
    )
    # Should return 200 with generic message to prevent email enumeration attacks
    assert r.status_code == 200
    assert r.json() == {
        "message": "If that email is registered, we sent a password recovery link"
    }


def test_system_actor_password_recovery_is_non_enumerating_and_queues_nothing(
    client: TestClient, db: Session
) -> None:
    from app.core.audit import ensure_system_actor

    system_actor = ensure_system_actor(session=db)
    db.commit()
    response = client.post(
        f"{settings.API_V1_STR}/password-recovery/{system_actor.email}"
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "If that email is registered, we sent a password recovery link"
    }
    assert (
        db.exec(
            select(EmailOutbox).where(EmailOutbox.recipient == system_actor.email)
        ).first()
        is None
    )


def test_reset_password(client: TestClient, db: Session) -> None:
    email = random_email()
    password = random_lower_string()
    new_password = random_lower_string()

    user_create = UserCreate(
        email=email,
        full_name="Test User",
        password=password,
        is_active=True,
    )
    user = create_user(session=db, user_create=user_create)
    db.commit()
    token = generate_password_reset_token(
        user_id=user.id,
        purpose="password_reset",
        version=user.password_reset_version,
    )
    headers = user_authentication_headers(client=client, email=email, password=password)
    data = {"new_password": new_password, "token": token}

    r = client.post(
        f"{settings.API_V1_STR}/reset-password/",
        headers=headers,
        json=data,
    )

    assert r.status_code == 200
    assert r.json() == {"message": "Password updated successfully"}

    assert (
        client.post(
            f"{settings.API_V1_STR}/login/test-token", headers=headers
        ).status_code
        == 401
    )

    db.refresh(user)
    verified, _ = verify_password(new_password, user.hashed_password)
    assert verified

    reused = client.post(
        f"{settings.API_V1_STR}/reset-password/",
        headers=headers,
        json=data,
    )
    assert reused.status_code == 400
    assert reused.json()["detail"] == "Invalid token"


def test_reset_password_invalid_token(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    data = {"new_password": "changethis", "token": "invalid"}
    r = client.post(
        f"{settings.API_V1_STR}/reset-password/",
        headers=superuser_token_headers,
        json=data,
    )
    response = r.json()

    assert "detail" in response
    assert r.status_code == 400
    assert response["detail"] == "Invalid token"
    assert response["request_id"]


def test_system_actor_password_reset_and_html_preview_are_unavailable(
    client: TestClient, db: Session, superuser_token_headers: dict[str, str]
) -> None:
    from app.core.audit import ensure_system_actor

    system_actor = ensure_system_actor(session=db)
    original_hash = system_actor.hashed_password
    db.commit()
    token = generate_password_reset_token(
        user_id=system_actor.id,
        purpose="password_reset",
        version=system_actor.password_reset_version,
    )

    reset = client.post(
        f"{settings.API_V1_STR}/reset-password/",
        json={"new_password": "cannot-reset-system", "token": token},
    )
    html = client.post(
        f"{settings.API_V1_STR}/password-recovery-html-content/{system_actor.email}",
        headers=superuser_token_headers,
    )

    assert reset.status_code == 400
    assert reset.json()["detail"] == "Invalid token"
    assert html.status_code == 404
    assert (
        html.json()["detail"]
        == "The user with this username does not exist in the system."
    )
    db.refresh(system_actor)
    assert system_actor.hashed_password == original_hash


def test_use_access_token_invalid_token_returns_request_id(client: TestClient) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/login/test-token",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert r.status_code == 401
    payload = r.json()
    assert payload["detail"] == "Could not validate credentials"
    assert payload["request_id"]


def test_login_with_bcrypt_password_upgrades_to_argon2(
    client: TestClient, db: Session
) -> None:
    """Test that logging in with a bcrypt password hash upgrades it to argon2."""
    email = random_email()
    password = random_lower_string()

    # Create a bcrypt hash directly (simulating legacy password)
    bcrypt_hasher = BcryptHasher()
    bcrypt_hash = bcrypt_hasher.hash(password)
    assert bcrypt_hash.startswith("$2")  # bcrypt hashes start with $2

    user = User(email=email, hashed_password=bcrypt_hash, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.hashed_password.startswith("$2")

    login_data = {"username": email, "password": password}
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    assert r.status_code == 200
    tokens = r.json()
    assert "access_token" in tokens

    db.refresh(user)

    # Verify the hash was upgraded to argon2
    assert user.hashed_password.startswith("$argon2")

    verified, updated_hash = verify_password(password, user.hashed_password)
    assert verified
    # Should not need another update since it's already argon2
    assert updated_hash is None


def test_login_with_argon2_password_keeps_hash(client: TestClient, db: Session) -> None:
    """Test that logging in with an argon2 password hash does not update it."""
    email = random_email()
    password = random_lower_string()

    # Create an argon2 hash (current default)
    argon2_hash = get_password_hash(password)
    assert argon2_hash.startswith("$argon2")

    # Create user with argon2 hash
    user = User(email=email, hashed_password=argon2_hash, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    original_hash = user.hashed_password

    login_data = {"username": email, "password": password}
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    assert r.status_code == 200
    tokens = r.json()
    assert "access_token" in tokens

    db.refresh(user)

    assert user.hashed_password == original_hash
    assert user.hashed_password.startswith("$argon2")
