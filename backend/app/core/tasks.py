from app.core.celery import celery_app
from app.core.config import settings
from app.utils import generate_test_email, send_email


def runtime_ping(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("runtime.ping value must be a string")
    if len(value) > 64:
        raise ValueError("runtime.ping value must be 64 characters or fewer")
    return value


def send_scheduled_test_email() -> None:
    email_to = str(settings.EMAIL_TEST_USER)
    email_data = generate_test_email(email_to=email_to)
    send_email(
        email_to=email_to,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )


celery_app.task(name="runtime.ping")(runtime_ping)
celery_app.task(name="runtime.send_test_email", ignore_result=True)(
    send_scheduled_test_email
)
