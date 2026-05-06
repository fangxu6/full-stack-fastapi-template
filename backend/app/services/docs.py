from pathlib import Path

from app.core.exceptions import RuleDocumentNotFoundError
from app.schemas.docs import RuleDocumentPublic, RuleDocumentsPublic, RuleDocumentSummary

REPO_ROOT = Path(__file__).resolve().parents[3]
RULES_DIRECTORY = REPO_ROOT / "docs" / "rules"


def _get_resolved_rules_directory() -> Path | None:
    if not RULES_DIRECTORY.exists():
        return None

    return RULES_DIRECTORY.resolve(strict=True)


def _is_allowed_rule_file(*, file_path: Path, rules_directory: Path) -> bool:
    if file_path.suffix != ".md" or file_path.is_symlink():
        return False

    try:
        resolved_file_path = file_path.resolve(strict=True)
        resolved_file_path.relative_to(rules_directory)
    except (FileNotFoundError, ValueError):
        return False

    return resolved_file_path.is_file()


def _extract_title(file_path: Path, slug: str) -> str:
    with file_path.open(encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped.removeprefix("# ").strip()
    return slug


def _build_rule_document_summary(file_path: Path) -> RuleDocumentSummary:
    slug = file_path.stem
    title = _extract_title(file_path=file_path, slug=slug)
    relative_path = file_path.relative_to(REPO_ROOT).as_posix()
    return RuleDocumentSummary(slug=slug, title=title, path=relative_path)


def _get_rule_documents_index() -> dict[str, Path]:
    rules_directory = _get_resolved_rules_directory()
    if rules_directory is None:
        return {}

    return {
        file_path.stem: file_path
        for file_path in sorted(RULES_DIRECTORY.glob("*.md"))
        if _is_allowed_rule_file(
            file_path=file_path,
            rules_directory=rules_directory,
        )
    }


def read_rule_documents() -> RuleDocumentsPublic:
    documents = [
        _build_rule_document_summary(file_path=file_path)
        for file_path in _get_rule_documents_index().values()
    ]
    return RuleDocumentsPublic(data=documents, count=len(documents))


def read_rule_document(*, slug: str) -> RuleDocumentPublic:
    rules_directory = _get_resolved_rules_directory()
    file_path = _get_rule_documents_index().get(slug)
    if rules_directory is None or file_path is None:
        raise RuleDocumentNotFoundError()

    if not _is_allowed_rule_file(file_path=file_path, rules_directory=rules_directory):
        raise RuleDocumentNotFoundError()

    summary = _build_rule_document_summary(file_path=file_path)
    content = file_path.read_text(encoding="utf-8")
    return RuleDocumentPublic(**summary.model_dump(), content=content)
