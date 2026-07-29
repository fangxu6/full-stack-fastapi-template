from fastapi import APIRouter, Depends
from pydantic.networks import EmailStr

from app.api.deps import AuditedWriteSessionDep, get_current_active_superuser
from app.schemas.security import Message
from app.services.email_outbox import queue_rendered_email
from app.utils import generate_test_email

router = APIRouter(prefix="/utils", tags=["utils"])


@router.post(
    "/test-email/",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=202,
)
def test_email(
    email_to: EmailStr,
    session: AuditedWriteSessionDep,
) -> Message:
    """
    Test emails.
    """
    email_data = generate_test_email(email_to=email_to)
    queue_rendered_email(
        session=session,
        recipient=str(email_to),
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    return Message(message="Test email queued")


@router.get("/health-check/")
async def health_check() -> bool:
    return True
