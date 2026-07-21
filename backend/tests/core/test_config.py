import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_ai_enabled_requires_internal_backend_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AI_ORCHESTRATOR_URL", raising=False)
    monkeypatch.delenv("AI_ORCHESTRATOR_SERVICE_TOKEN", raising=False)
    monkeypatch.delenv("AI_INTERNAL_SERVICE_TOKEN", raising=False)
    monkeypatch.delenv("AI_ACTOR_GRANT_SIGNING_KEY", raising=False)

    with pytest.raises(ValidationError, match="AI_ENABLED requires"):
        Settings(
            _env_file=None,
            AI_ENABLED=True,
            FIRST_SUPERUSER="test@example.com",
            FIRST_SUPERUSER_PASSWORD="test-password",
            POSTGRES_SERVER="localhost",
            POSTGRES_USER="test",
            PROJECT_NAME="test",
        )
