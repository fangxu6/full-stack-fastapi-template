from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm

from app import services
from app.api.deps import (
    CurrentUser,
    SystemAuditedWriteSessionDep,
    TokenDep,
    WriteSessionDep,
)
from app.modules.iam.dependencies import permission_required
from app.schemas.security import Message, NewPassword, Token
from app.schemas.user import UserPublic

router = APIRouter(tags=["login"])


@router.post("/login/access-token")
def login_access_token(
    session: WriteSessionDep, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    return services.auth.login_access_token(
        session=session, username=form_data.username, password=form_data.password
    )


@router.post("/login/logout", response_model=Message)
def logout(session: WriteSessionDep, token: TokenDep) -> Message:
    return services.auth.logout(session=session, token=token)


@router.post("/login/test-token", response_model=UserPublic)
def test_token(session: WriteSessionDep, current_user: CurrentUser) -> Any:
    """
    Test access token
    """
    return services.user.user_public(session=session, user=current_user)


@router.post("/password-recovery/{email}")
def recover_password(email: str, session: SystemAuditedWriteSessionDep) -> Message:
    """
    Password Recovery
    """
    return services.auth.recover_password(session=session, email=email)


@router.post("/reset-password/")
def reset_password(session: WriteSessionDep, body: NewPassword) -> Message:
    """
    Reset password
    """
    return services.auth.reset_password(session=session, body=body)


@router.post(
    "/password-recovery-html-content/{email}",
    dependencies=[Depends(permission_required("system.users.manage"))],
    response_class=HTMLResponse,
)
def recover_password_html_content(email: str, session: WriteSessionDep) -> Any:
    """
    HTML Content for Password Recovery
    """
    return services.auth.recover_password_html_content(session=session, email=email)
