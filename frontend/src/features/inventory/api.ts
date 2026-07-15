import {
  type InventoryBalancesPublic,
  type InventoryDocumentsPublic,
  type InventoryDocumentType,
  type InventoryLedgerEntriesPublic,
  type InventoryLedgerKind,
  type MasterUnitsPublic,
  OpenAPI,
} from "@/client"
import { request } from "@/client/core/request"

type QueryValue = boolean | number | string | null | undefined

type OffsetParams = {
  limit: number
  skip: number
}

type InventoryBalancesPage = InventoryBalancesPublic & { count: number }

function readInventoryPage<T>(url: string, query: Record<string, QueryValue>) {
  return request<T>(OpenAPI, {
    errors: { 422: "Validation Error" },
    method: "GET",
    query,
    url,
  })
}

export function readProcessingUnitsPage(params: OffsetParams) {
  return readInventoryPage<MasterUnitsPublic>(
    "/api/v1/inventory/processing-units",
    params,
  )
}

export function readReceivingUnitsPage(params: OffsetParams) {
  return readInventoryPage<MasterUnitsPublic>(
    "/api/v1/inventory/receiving-units",
    params,
  )
}

export function readInventoryDocumentsPage(
  params: OffsetParams & {
    businessDateFrom?: string
    businessDateTo?: string
    documentNumber?: string
    documentType?: InventoryDocumentType
    includeDeleted?: boolean
    processingUnitId?: string
    receivingUnitId?: string
  },
) {
  return readInventoryPage<InventoryDocumentsPublic>(
    "/api/v1/inventory/documents",
    {
      business_date_from: params.businessDateFrom,
      business_date_to: params.businessDateTo,
      document_number: params.documentNumber,
      document_type: params.documentType,
      include_deleted: params.includeDeleted,
      limit: params.limit,
      processing_unit_id: params.processingUnitId,
      receiving_unit_id: params.receivingUnitId,
      skip: params.skip,
    },
  )
}

export function readRawBalancesPage(
  params: OffsetParams & {
    itemName?: string
    processingUnitId?: string
  },
) {
  return readInventoryPage<InventoryBalancesPage>(
    "/api/v1/inventory/balances/raw",
    {
      item_name: params.itemName,
      limit: params.limit,
      processing_unit_id: params.processingUnitId,
      skip: params.skip,
    },
  )
}

export function readFinishedBalancesPage(
  params: OffsetParams & {
    itemName?: string
    processingUnitId?: string
  },
) {
  return readInventoryPage<InventoryBalancesPage>(
    "/api/v1/inventory/balances/finished",
    {
      item_name: params.itemName,
      limit: params.limit,
      processing_unit_id: params.processingUnitId,
      skip: params.skip,
    },
  )
}

export function readInventoryLedgerPage(
  params: OffsetParams & {
    colorCode?: string
    dyeLotNo?: string
    itemCode?: string
    itemName: string
    ledgerKind: InventoryLedgerKind
    processingUnitId: string
    woolContent: string
  },
) {
  return readInventoryPage<InventoryLedgerEntriesPublic>(
    "/api/v1/inventory/ledger",
    {
      color_code: params.colorCode,
      dye_lot_no: params.dyeLotNo,
      item_code: params.itemCode,
      item_name: params.itemName,
      ledger_kind: params.ledgerKind,
      limit: params.limit,
      processing_unit_id: params.processingUnitId,
      skip: params.skip,
      wool_content: params.woolContent,
    },
  )
}
