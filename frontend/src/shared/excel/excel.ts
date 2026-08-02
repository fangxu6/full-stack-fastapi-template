import { ApiError, OpenAPI } from "@/client"
import type { ApiRequestOptions } from "@/client/core/ApiRequestOptions"

export const MAX_XLSX_BYTES = 10 * 1024 * 1024

type QueryValue = boolean | number | string | null | undefined

export type ExcelIssue = {
  worksheet: string | null
  row: number | null
  column: string | null
  field: string | null
  message: string
}

type ExcelValidationFailure = {
  message: string
  issues: ExcelIssue[]
}

type ExcelDownloadOptions = {
  filename: string
  query?: Record<string, QueryValue>
  url: string
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null
}

function isExcelIssue(value: unknown): value is ExcelIssue {
  return (
    isRecord(value) &&
    (typeof value.worksheet === "string" || value.worksheet === null) &&
    (typeof value.row === "number" || value.row === null) &&
    (typeof value.column === "string" || value.column === null) &&
    (typeof value.field === "string" || value.field === null) &&
    typeof value.message === "string"
  )
}

function queryString(query: Record<string, QueryValue> | undefined) {
  if (!query) return ""
  const search = new URLSearchParams()
  for (const [name, value] of Object.entries(query)) {
    if (value !== null && value !== undefined) {
      search.set(name, String(value))
    }
  }
  const rendered = search.toString()
  return rendered ? `?${rendered}` : ""
}

export function getDownloadFilename(value: string | null, fallback: string) {
  if (!value) return fallback
  const encoded = /filename\*=UTF-8''([^;]+)/i.exec(value)?.[1]
  if (encoded) {
    try {
      return decodeURIComponent(encoded)
    } catch {
      return fallback
    }
  }
  return /filename="?([^";]+)"?/i.exec(value)?.[1] ?? fallback
}

async function tokenFor(options: ApiRequestOptions<string>) {
  const token = OpenAPI.TOKEN
  return typeof token === "function" ? token(options) : token
}

export function validateXlsxFile(file: Pick<File, "name" | "size">) {
  if (!file.name.toLowerCase().endsWith(".xlsx")) {
    return "请选择 .xlsx 工作簿。"
  }
  if (file.size > MAX_XLSX_BYTES) {
    return "工作簿不能超过 10 MiB。"
  }
  return undefined
}

export function getExcelValidationFailure(
  error: unknown,
): ExcelValidationFailure | undefined {
  if (!(error instanceof ApiError) || error.status !== 422) return undefined
  if (!isRecord(error.body) || !isRecord(error.body.detail)) return undefined
  const { detail } = error.body
  if (typeof detail.message !== "string" || !Array.isArray(detail.issues)) {
    return undefined
  }
  const issues = detail.issues.filter(isExcelIssue)
  return issues.length === detail.issues.length
    ? { issues, message: detail.message }
    : undefined
}

export async function downloadXlsx({
  filename,
  query,
  url,
}: ExcelDownloadOptions) {
  const options: ApiRequestOptions<string> = { method: "GET", query, url }
  const token = await tokenFor(options)
  const response = await fetch(`${OpenAPI.BASE}${url}${queryString(query)}`, {
    credentials: OpenAPI.CREDENTIALS,
    headers: {
      Accept:
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
  if (!response.ok) {
    const contentType = response.headers.get("content-type") ?? ""
    const body = contentType.includes("application/json")
      ? await response.json()
      : await response.text()
    throw new ApiError(
      options,
      {
        body,
        ok: false,
        status: response.status,
        statusText: response.statusText,
        url: response.url,
      },
      response.statusText,
    )
  }
  const link = document.createElement("a")
  const objectUrl = URL.createObjectURL(await response.blob())
  link.download = getDownloadFilename(
    response.headers.get("content-disposition"),
    filename,
  )
  link.href = objectUrl
  link.click()
  URL.revokeObjectURL(objectUrl)
}
