from sqlmodel import SQLModel


class RuleDocumentSummary(SQLModel):
    slug: str
    title: str
    path: str


class RuleDocumentsPublic(SQLModel):
    data: list[RuleDocumentSummary]
    count: int


class RuleDocumentPublic(RuleDocumentSummary):
    content: str
