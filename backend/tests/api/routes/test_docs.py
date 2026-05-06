import shutil
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.services import docs


def _create_repo_local_rules_directory() -> Path:
    temp_root = docs.REPO_ROOT / "backend" / "tests" / "_tmp_rules"
    temp_root.mkdir(exist_ok=True)
    rules_directory = temp_root / f"rules-{uuid.uuid4().hex}"
    rules_directory.mkdir()
    return rules_directory


def test_read_rule_documents(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/docs/rules",
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    content = response.json()
    assert content["count"] >= 1
    assert len(content["data"]) == content["count"]
    assert all("slug" in item for item in content["data"])
    assert all("title" in item for item in content["data"])
    assert all(item["path"].startswith("docs/rules/") for item in content["data"])


def test_read_rule_documents_requires_auth(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/docs/rules")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_read_rule_document(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    list_response = client.get(
        f"{settings.API_V1_STR}/docs/rules",
        headers=superuser_token_headers,
    )
    slug = list_response.json()["data"][0]["slug"]

    response = client.get(
        f"{settings.API_V1_STR}/docs/rules/{slug}",
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    content = response.json()
    assert content["slug"] == slug
    assert content["path"].startswith("docs/rules/")
    assert content["content"]


def test_read_rule_document_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/docs/rules/not-a-real-rule",
        headers=superuser_token_headers,
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["detail"] == "Rule document not found"
    assert payload["request_id"]


def test_read_rule_document_rejects_path_traversal(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/docs/rules/../README",
        headers=superuser_token_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Not Found"


def test_read_rule_documents_returns_empty_list_for_missing_directory(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    monkeypatch,
) -> None:
    missing_directory = docs.REPO_ROOT / "docs" / "__missing_rules_test__"
    monkeypatch.setattr(docs, "RULES_DIRECTORY", missing_directory)

    response = client.get(
        f"{settings.API_V1_STR}/docs/rules",
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    assert response.json() == {"data": [], "count": 0}


def test_read_rule_documents_ignores_symlinked_markdown_files(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    monkeypatch,
) -> None:
    rules_directory = _create_repo_local_rules_directory()

    try:
        (rules_directory / "safe-rule.md").write_text(
            "# Safe Rule\n\nVisible content",
            encoding="utf-8",
        )

        symlink_path = rules_directory / "linked-secret.md"
        try:
            symlink_path.symlink_to(docs.REPO_ROOT / "README.md")
        except (NotImplementedError, OSError) as exc:
            pytest.skip(f"symlink creation is not supported in this environment: {exc}")

        monkeypatch.setattr(docs, "RULES_DIRECTORY", rules_directory)

        list_response = client.get(
            f"{settings.API_V1_STR}/docs/rules",
            headers=superuser_token_headers,
        )
        assert list_response.status_code == 200
        list_content = list_response.json()
        assert [item["slug"] for item in list_content["data"]] == ["safe-rule"]

        detail_response = client.get(
            f"{settings.API_V1_STR}/docs/rules/linked-secret",
            headers=superuser_token_headers,
        )
        assert detail_response.status_code == 404
        assert detail_response.json()["detail"] == "Rule document not found"
    finally:
        shutil.rmtree(rules_directory, ignore_errors=True)
