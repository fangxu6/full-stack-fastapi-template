import { describe, expect, test } from "bun:test"
import { ApiError } from "@/client"
import {
  getDownloadFilename,
  getExcelValidationFailure,
  MAX_XLSX_BYTES,
  validateXlsxFile,
} from "./excel"

describe("Excel browser boundaries", () => {
  test("accepts a bounded xlsx file and rejects unsupported files", () => {
    expect(
      validateXlsxFile({ name: "inventory.xlsx", size: MAX_XLSX_BYTES }),
    ).toBeUndefined()
    expect(validateXlsxFile({ name: "inventory.csv", size: 1 })).toBe(
      "请选择 .xlsx 工作簿。",
    )
    expect(
      validateXlsxFile({ name: "inventory.xlsx", size: MAX_XLSX_BYTES + 1 }),
    ).toBe("工作簿不能超过 10 MiB。")
  })

  test("extracts the structured Excel issues from the application error envelope", () => {
    const error = new ApiError(
      { method: "POST", url: "/excel/imports/documents" },
      {
        body: {
          detail: {
            issues: [
              {
                column: "单据类型",
                field: "document_type",
                message: "Document type is not allowed for this import",
                row: 2,
                worksheet: "单据导入",
              },
            ],
            message: "Excel validation failed",
          },
          request_id: "request-id",
        },
        ok: false,
        status: 422,
        statusText: "Unprocessable Content",
        url: "/excel/imports/documents",
      },
      "Validation Error",
    )

    expect(getExcelValidationFailure(error)).toEqual({
      issues: [
        {
          column: "单据类型",
          field: "document_type",
          message: "Document type is not allowed for this import",
          row: 2,
          worksheet: "单据导入",
        },
      ],
      message: "Excel validation failed",
    })
  })

  test("uses the server filename when valid and falls back when absent", () => {
    expect(
      getDownloadFilename(
        'attachment; filename="ledger.xlsx"',
        "fallback.xlsx",
      ),
    ).toBe("ledger.xlsx")
    expect(getDownloadFilename(null, "fallback.xlsx")).toBe("fallback.xlsx")
  })
})
