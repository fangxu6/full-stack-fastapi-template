import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_ai_enabled_requires_internal_backend_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AI_ORCHESTRATOR_URL", raising=False)
    monkeypatch.delenv("AI_INTERNAL_SERVICE_TOKEN", raising=False)
    monkeypatch.delenv("AI_ACTOR_GRANT_SIGNING_KEY", raising=False)

    with pytest.raises(ValidationError, match="AI_ENABLED requires"):
        Settings(AI_ENABLED=True)
