import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status

from app.api.deps import AuditedWriteSessionDep, CurrentUser, SessionDep
from app.core.excel import (
    MAX_XLSX_BYTES,
    ExcelIssue,
    ExcelValidationError,
    create_xlsx,
)
from app.models.inventory import InventoryDocumentType, InventoryLedgerKind
from app.modules.iam.dependencies import permission_required
from app.modules.inventory import importer, service
from app.schemas.inventory import (
    InventoryBalancesPublic,
    InventoryDocumentCreate,
    InventoryDocumentExcelRow,
    InventoryDocumentPublic,
    InventoryDocumentsPublic,
    InventoryExcelImportPublic,
    InventoryLedgerEntriesPublic,
    InventoryLedgerExcelRow,
    InventorySuggestionsPublic,
    LegacyInventoryExcelImportPublic,
    MasterUnitCreate,
    MasterUnitPublic,
    MasterUnitsPublic,
    MasterUnitUpdate,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


async def _read_xlsx_upload(upload: UploadFile) -> bytes:
    filename = upload.filename or ""
    if not filename.casefold().endswith(".xlsx"):
        raise ExcelValidationError(
            [
                ExcelIssue(
                    worksheet=None,
                    row=None,
                    column=None,
                    field=None,
                    message="Only .xlsx workbooks are supported",
                )
            ]
        )
    content = bytearray()
    while chunk := await upload.read(1024 * 1024):
        content.extend(chunk)
        if len(content) > MAX_XLSX_BYTES:
            raise ExcelValidationError(
                [
                    ExcelIssue(
                        worksheet=None,
                        row=None,
                        column=None,
                        field=None,
                        message=f"Workbook exceeds the {MAX_XLSX_BYTES} byte limit",
                    )
                ]
            )
    return bytes(content)


def _xlsx_response(content: bytes, *, filename: str) -> Response:
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/excel/templates/documents",
    dependencies=[Depends(permission_required("inventory.documents.manage"))],
)
def download_document_template(current_user: CurrentUser) -> Response:
    del current_user
    output = create_xlsx(
        [],
        model_type=InventoryDocumentExcelRow,
        worksheet_name=importer.DOCUMENT_WORKSHEET_NAME,
    )
    return _xlsx_response(
        output.getvalue(), filename="inventory-document-template.xlsx"
    )


@router.post(
    "/excel/imports/documents",
    dependencies=[Depends(permission_required("inventory.documents.manage"))],
    response_model=InventoryExcelImportPublic,
    status_code=status.HTTP_201_CREATED,
)
async def import_documents_from_excel(
    *,
    session: AuditedWriteSessionDep,
    _current_user: CurrentUser,
    workbook: UploadFile = File(...),
) -> InventoryExcelImportPublic:
    return importer.import_document_workbook(
        session=session,
        content=await _read_xlsx_upload(workbook),
    )


@router.post(
    "/excel/imports/legacy",
    dependencies=[Depends(permission_required("inventory.documents.manage"))],
    response_model=LegacyInventoryExcelImportPublic,
    status_code=status.HTTP_201_CREATED,
)
async def import_legacy_workbooks_from_excel(
    *,
    session: AuditedWriteSessionDep,
    _current_user: CurrentUser,
    raw_workbook: UploadFile = File(...),
    finished_workbook: UploadFile = File(...),
) -> LegacyInventoryExcelImportPublic:
    raw_content = await _read_xlsx_upload(raw_workbook)
    finished_content = await _read_xlsx_upload(finished_workbook)
    return importer.import_legacy_workbooks(
        session=session,
        raw_content=raw_content,
        raw_filename=raw_workbook.filename or "raw.xlsx",
        finished_content=finished_content,
        finished_filename=finished_workbook.filename or "finished.xlsx",
    )


@router.get(
    "/excel/ledger",
    dependencies=[Depends(permission_required("inventory.ledger.read"))],
)
def export_inventory_ledger(
    session: SessionDep,
    current_user: CurrentUser,
    ledger_kind: InventoryLedgerKind,
    processing_unit_id: uuid.UUID | None = None,
    business_date_from: date | None = None,
    business_date_to: date | None = None,
) -> Response:
    del current_user
    output = create_xlsx(
        service.list_ledger_excel_rows(
            session=session,
            ledger_kind=ledger_kind,
            processing_unit_id=processing_unit_id,
            business_date_from=business_date_from,
            business_date_to=business_date_to,
        ),
        model_type=InventoryLedgerExcelRow,
        worksheet_name="库存台账",
    )
    return _xlsx_response(
        output.getvalue(), filename=f"inventory-ledger-{ledger_kind}.xlsx"
    )


@router.get(
    "/processing-units",
    dependencies=[Depends(permission_required("inventory.masters.read"))],
    response_model=MasterUnitsPublic,
)
def read_processing_units(
    session: SessionDep,
    current_user: CurrentUser,
    name: str | None = Query(default=None, max_length=255),
    is_active: bool | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> Any:
    del current_user
    return service.list_processing_units(
        session=session,
        name=name,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/processing-units",
    dependencies=[Depends(permission_required("inventory.masters.manage"))],
    response_model=MasterUnitPublic,
)
def create_processing_unit(
    *,
    session: AuditedWriteSessionDep,
    _current_user: CurrentUser,
    unit_in: MasterUnitCreate,
) -> Any:
    return service.create_processing_unit(session=session, unit_in=unit_in)


@router.put(
    "/processing-units/{unit_id}",
    dependencies=[Depends(permission_required("inventory.masters.manage"))],
    response_model=MasterUnitPublic,
)
def update_processing_unit(
    *,
    session: AuditedWriteSessionDep,
    _current_user: CurrentUser,
    unit_id: uuid.UUID,
    unit_in: MasterUnitUpdate,
) -> Any:
    return service.update_processing_unit(
        session=session,
        unit_id=unit_id,
        unit_in=unit_in,
    )


@router.get(
    "/receiving-units",
    dependencies=[Depends(permission_required("inventory.masters.read"))],
    response_model=MasterUnitsPublic,
)
def read_receiving_units(
    session: SessionDep,
    current_user: CurrentUser,
    name: str | None = Query(default=None, max_length=255),
    is_active: bool | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> Any:
    del current_user
    return service.list_receiving_units(
        session=session,
        name=name,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/receiving-units",
    dependencies=[Depends(permission_required("inventory.masters.manage"))],
    response_model=MasterUnitPublic,
)
def create_receiving_unit(
    *,
    session: AuditedWriteSessionDep,
    _current_user: CurrentUser,
    unit_in: MasterUnitCreate,
) -> Any:
    return service.create_receiving_unit(session=session, unit_in=unit_in)


@router.put(
    "/receiving-units/{unit_id}",
    dependencies=[Depends(permission_required("inventory.masters.manage"))],
    response_model=MasterUnitPublic,
)
def update_receiving_unit(
    *,
    session: AuditedWriteSessionDep,
    _current_user: CurrentUser,
    unit_id: uuid.UUID,
    unit_in: MasterUnitUpdate,
) -> Any:
    return service.update_receiving_unit(
        session=session,
        unit_id=unit_id,
        unit_in=unit_in,
    )


@router.post(
    "/documents",
    dependencies=[Depends(permission_required("inventory.documents.manage"))],
    response_model=InventoryDocumentPublic,
)
def create_inventory_document(
    *,
    session: AuditedWriteSessionDep,
    _current_user: CurrentUser,
    document_in: InventoryDocumentCreate,
) -> Any:
    return service.create_document(session=session, document_in=document_in)


@router.get(
    "/documents",
    dependencies=[Depends(permission_required("inventory.documents.read"))],
    response_model=InventoryDocumentsPublic,
)
def read_inventory_documents(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    document_type: InventoryDocumentType | None = None,
    business_date_from: date | None = None,
    business_date_to: date | None = None,
    processing_unit_id: uuid.UUID | None = None,
    receiving_unit_id: uuid.UUID | None = None,
    document_number: str | None = None,
    include_deleted: bool = False,
) -> Any:
    del current_user
    return service.list_documents(
        session=session,
        skip=skip,
        limit=limit,
        document_type=document_type,
        business_date_from=business_date_from,
        business_date_to=business_date_to,
        processing_unit_id=processing_unit_id,
        receiving_unit_id=receiving_unit_id,
        document_number=document_number,
        include_deleted=include_deleted,
    )


@router.get(
    "/documents/{document_id}",
    dependencies=[Depends(permission_required("inventory.documents.read"))],
    response_model=InventoryDocumentPublic,
)
def read_inventory_document(
    document_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> Any:
    del current_user
    return service.get_document(session=session, document_id=document_id)


@router.put(
    "/documents/{document_id}",
    dependencies=[Depends(permission_required("inventory.documents.manage"))],
    response_model=InventoryDocumentPublic,
)
def update_inventory_document(
    *,
    session: AuditedWriteSessionDep,
    _current_user: CurrentUser,
    document_id: uuid.UUID,
    document_in: InventoryDocumentCreate,
) -> Any:
    return service.update_document(
        session=session,
        document_id=document_id,
        document_in=document_in,
    )


@router.delete(
    "/documents/{document_id}",
    dependencies=[Depends(permission_required("inventory.documents.manage"))],
)
def delete_inventory_document(
    document_id: uuid.UUID, session: AuditedWriteSessionDep, _current_user: CurrentUser
) -> dict[str, str]:
    service.delete_document(session=session, document_id=document_id)
    return {"message": "Inventory document deleted"}


@router.post(
    "/documents/{document_id}/restore",
    dependencies=[Depends(permission_required("inventory.documents.manage"))],
)
def restore_inventory_document(
    document_id: uuid.UUID, session: AuditedWriteSessionDep, _current_user: CurrentUser
) -> dict[str, str]:
    service.restore_document(session=session, document_id=document_id)
    return {"message": "Inventory document restored"}


@router.get(
    "/balances/raw",
    dependencies=[Depends(permission_required("inventory.balances.read"))],
    response_model=InventoryBalancesPublic,
)
def read_raw_balances(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    processing_unit_id: uuid.UUID | None = None,
    item_name: str | None = None,
) -> Any:
    del current_user
    return service.list_balances(
        session=session,
        ledger_kind=InventoryLedgerKind.RAW,
        skip=skip,
        limit=limit,
        processing_unit_id=processing_unit_id,
        item_name=item_name,
    )


@router.get(
    "/balances/finished",
    dependencies=[Depends(permission_required("inventory.balances.read"))],
    response_model=InventoryBalancesPublic,
)
def read_finished_balances(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    processing_unit_id: uuid.UUID | None = None,
    item_name: str | None = None,
) -> Any:
    del current_user
    return service.list_balances(
        session=session,
        ledger_kind=InventoryLedgerKind.FINISHED,
        skip=skip,
        limit=limit,
        processing_unit_id=processing_unit_id,
        item_name=item_name,
    )


@router.get(
    "/ledger",
    dependencies=[Depends(permission_required("inventory.ledger.read"))],
    response_model=InventoryLedgerEntriesPublic,
)
def read_inventory_ledger(
    session: SessionDep,
    current_user: CurrentUser,
    ledger_kind: InventoryLedgerKind,
    processing_unit_id: uuid.UUID,
    item_name: str,
    wool_content: str,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    item_code: str | None = None,
    color_code: str | None = None,
    dye_lot_no: str | None = None,
) -> Any:
    del current_user
    return service.list_ledger_entries(
        session=session,
        ledger_kind=ledger_kind,
        processing_unit_id=processing_unit_id,
        item_name=item_name,
        wool_content=wool_content,
        skip=skip,
        limit=limit,
        item_code=item_code,
        color_code=color_code,
        dye_lot_no=dye_lot_no,
    )


@router.get(
    "/suggestions",
    dependencies=[Depends(permission_required("inventory.documents.read"))],
    response_model=InventorySuggestionsPublic,
)
def read_inventory_suggestions(
    session: SessionDep,
    current_user: CurrentUser,
    ledger_kind: InventoryLedgerKind,
    field: Annotated[
        str,
        Query(pattern="^(item_name|item_code|wool_content|color_code|dye_lot_no)$"),
    ],
    query: str | None = None,
) -> Any:
    del current_user
    return service.list_suggestions(
        session=session, ledger_kind=ledger_kind, field=field, query=query
    )
