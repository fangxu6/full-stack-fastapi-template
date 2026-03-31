from typing import Any

from fastapi import APIRouter

from app import services
from app.api.deps import CurrentUser
from app.models import RuleDocumentPublic, RuleDocumentsPublic

router = APIRouter(prefix="/docs", tags=["docs"])


@router.get("/rules", response_model=RuleDocumentsPublic)
def read_rule_documents(current_user: CurrentUser) -> Any:
    """
    Retrieve whitelisted rule documents.
    """
    return services.docs.read_rule_documents()


@router.get("/rules/{slug}", response_model=RuleDocumentPublic)
def read_rule_document(slug: str, current_user: CurrentUser) -> Any:
    """
    Get a single rule document by slug.
    """
    return services.docs.read_rule_document(slug=slug)
