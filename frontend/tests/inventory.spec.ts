import { expect, type Page, test } from "@playwright/test"
import type { InventoryBalancePublic, MasterUnitPublic } from "../src/client"

const apiBaseUrl =
  process.env.PLAYWRIGHT_E2E_API_URL ??
  process.env.VITE_API_URL ??
  "http://localhost:8000"

function uniqueValue(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

async function authenticatedHeaders(page: Page) {
  const token = await page.evaluate(() => localStorage.getItem("access_token"))
  expect(token).toBeTruthy()
  return { Authorization: `Bearer ${token}` }
}

async function createInventoryFixture(
  page: Page,
  path: string,
  payload: Record<string, unknown>,
) {
  const response = await page.request.post(
    `${apiBaseUrl}/api/v1/inventory${path}`,
    {
      data: payload,
      headers: await authenticatedHeaders(page),
    },
  )
  expect(response.ok(), await response.text()).toBeTruthy()
  return await response.json()
}

async function readInventoryFixture<T>(page: Page, path: string): Promise<T> {
  const response = await page.request.get(
    `${apiBaseUrl}/api/v1/inventory${path}`,
    {
      headers: await authenticatedHeaders(page),
    },
  )
  expect(response.ok(), await response.text()).toBeTruthy()
  return (await response.json()) as T
}

async function findBalance(
  page: Page,
  ledgerKind: "finished" | "raw",
  predicate: (balance: InventoryBalancePublic) => boolean,
) {
  const pageSize = 100
  for (let skip = 0; ; skip += pageSize) {
    const balances = await readInventoryFixture<{
      count: number
      data: InventoryBalancePublic[]
    }>(page, `/balances/${ledgerKind}?limit=${pageSize}&skip=${skip}`)
    const balance = balances.data.find(predicate)
    if (balance) {
      return { balance, pageNumber: skip / pageSize + 1 }
    }
    if (skip + balances.data.length >= balances.count) break
  }
  throw new Error(`The E2E database needs a ${ledgerKind} inventory balance`)
}

async function selectOption(page: Page, label: string, option: string) {
  const combobox = page
    .getByRole("dialog")
    .getByRole("combobox", { name: label })
  await combobox.click()
  await combobox.fill(option)
  await page.getByText(option, { exact: true }).last().click()
}

function isProcessingUnitSearchRequest(
  url: string,
  name: string,
  isActive: boolean | undefined,
) {
  const requestUrl = new URL(url)
  return (
    requestUrl.pathname === "/api/v1/inventory/processing-units" &&
    requestUrl.searchParams.get("limit") === "20" &&
    requestUrl.searchParams.get("name") === name &&
    requestUrl.searchParams.get("skip") === "0" &&
    (isActive === undefined
      ? !requestUrl.searchParams.has("is_active")
      : requestUrl.searchParams.get("is_active") === String(isActive))
  )
}

test("Inventory master data, raw receipt, balance trace, and restore work together", async ({
  page,
}) => {
  const processingUnit = uniqueValue("E2E加工厂")
  const documentNumber = uniqueValue("E2E-R")
  const itemName = uniqueValue("E2E坯布")
  const itemCode = uniqueValue("E2E-CODE")

  await page.goto("/inventory/masters")
  await page.getByRole("button", { name: "新建加工单位" }).click()
  await page
    .getByRole("dialog")
    .getByRole("textbox", { name: /名称/ })
    .fill(processingUnit)
  await page
    .getByRole("dialog")
    .getByRole("button", { name: /保\s*存/ })
    .click()
  await expect(page.getByText("主数据已保存")).toBeVisible()
  await expect(
    page.getByRole("row").filter({ hasText: processingUnit }),
  ).toBeVisible()

  await page.goto("/inventory/raw")
  await expect(page.getByRole("heading", { name: "坯布台账" })).toBeVisible()
  await page.getByRole("button", { name: "新建来料入库" }).click()
  const receiptDialog = page.getByRole("dialog", { name: "新建坯布入库" })
  await expect(receiptDialog).toBeVisible()
  await receiptDialog.getByLabel("单号").fill(documentNumber)
  await selectOption(page, "加工单位", processingUnit)
  await receiptDialog.getByLabel("品名").fill(itemName)
  await receiptDialog.getByLabel("品号").fill(itemCode)
  await receiptDialog.getByLabel("含毛量").fill("100% wool")
  await receiptDialog.getByLabel("匹数").fill("5")
  await receiptDialog.getByRole("button", { name: /保\s*存/ }).click()

  await expect(page.getByText("单据已保存")).toBeVisible()
  const receiptRow = page.getByRole("row").filter({ hasText: documentNumber })
  await expect(receiptRow).toBeVisible()

  await page
    .getByRole("textbox", { name: /单号 : \* 单号/ })
    .fill(documentNumber)
  await expect(receiptRow).toBeVisible()

  await page.goto("/inventory/balances")
  const rawBalance = await findBalance(
    page,
    "raw",
    (balance) => balance.item_code === itemCode,
  )
  const pageSizeSelect = page.getByRole("combobox", { name: "Page Size" })
  await pageSizeSelect.click()
  await page.getByText("100 / page", { exact: true }).click()
  if (rawBalance.pageNumber > 1) {
    const pageInput = page.getByRole("textbox", { name: "Page" })
    await pageInput.fill(String(rawBalance.pageNumber))
    await pageInput.press("Enter")
  }
  const balanceRow = page.getByRole("row").filter({ hasText: itemCode })
  await expect(balanceRow).toContainText("5")
  await balanceRow.click()
  await expect(
    page.getByRole("dialog", { name: `${itemName} 关联台账` }),
  ).toBeVisible()
  await expect(page.getByText("RAW_RECEIPT")).toBeVisible()

  await page.goto("/inventory/raw")
  await receiptRow.getByRole("button", { name: "删除单据" }).click()
  await page.getByRole("button", { name: "OK", exact: true }).click()
  await expect(page.getByText("单据已软删除")).toBeVisible()
  await receiptRow.getByRole("button", { name: "恢复单据" }).click()
  await expect(page.getByText("单据已恢复")).toBeVisible()
})

test("Finished shipment page deducts the pre-existing finished balance", async ({
  page,
}) => {
  const receivingUnitName = uniqueValue("E2E收货单位")
  const documentNumber = uniqueValue("E2E-S")

  await page.goto("/")
  const finishedBalance = await findBalance(
    page,
    "finished",
    (candidate) =>
      Number(candidate.rolls_balance) >= 0.5 &&
      Number(candidate.meters_balance) >= 12.5 &&
      candidate.color_code !== null &&
      candidate.dye_lot_no !== null &&
      candidate.dye_lot_no !== "未分缸" &&
      candidate.wool_content !== "未填写含毛量",
  )
  const { balance } = finishedBalance
  if (!balance?.color_code || !balance.dye_lot_no) {
    throw new Error("The E2E database needs a finished inventory balance")
  }
  const processingUnits = await readInventoryFixture<{
    data: MasterUnitPublic[]
  }>(page, "/processing-units?limit=100&skip=0")
  const processingUnit = processingUnits.data.find(
    (unit) => unit.id === balance.processing_unit_id,
  )
  if (!processingUnit) {
    throw new Error("The finished balance processing unit is missing")
  }
  const receivingUnit = await createInventoryFixture(page, "/receiving-units", {
    name: receivingUnitName,
  })
  expect(receivingUnit.id).toBeTruthy()

  await page.goto("/inventory/shipments")
  await page.getByRole("button", { name: "新建成品出货" }).click()
  const shipmentDialog = page.getByRole("dialog", { name: "新建成品出货" })
  await shipmentDialog.getByLabel("单号").fill(documentNumber)
  await selectOption(page, "加工单位", processingUnit.name)
  await selectOption(page, "收货单位", receivingUnitName)
  await shipmentDialog.getByLabel("品名").fill(balance.item_name)
  await shipmentDialog.getByLabel("含毛量").fill(balance.wool_content)
  await shipmentDialog.getByLabel("颜色/色号").fill(balance.color_code)
  await shipmentDialog.getByLabel("缸号").fill(balance.dye_lot_no)
  await shipmentDialog.getByLabel("匹数").fill("0.5")
  await shipmentDialog.getByLabel("米数").fill("12.5")
  await shipmentDialog.getByRole("button", { name: /保\s*存/ }).click()

  await expect(page.getByText("单据已保存")).toBeVisible()
  await expect(
    page.getByRole("row").filter({ hasText: documentNumber }),
  ).toBeVisible()

  await page.goto("/inventory/balances")
  await page.getByRole("tab", { name: "成品库存" }).click()
  const finishedPageSizeSelect = page.getByRole("combobox", {
    name: "Page Size",
  })
  await finishedPageSizeSelect.click()
  await page.getByText("100 / page", { exact: true }).click()
  if (finishedBalance.pageNumber > 1) {
    const pageInput = page.getByRole("textbox", { name: "Page" })
    await pageInput.fill(String(finishedBalance.pageNumber))
    await pageInput.press("Enter")
  }
  const balanceRow = page
    .getByRole("row")
    .filter({ hasText: balance.item_name })
    .filter({ hasText: balance.wool_content })
    .filter({ hasText: balance.color_code })
    .filter({ hasText: balance.dye_lot_no })
  await expect(balanceRow).toHaveCount(1)
  await expect(balanceRow).toContainText(
    String(Number(balance.rolls_balance) - 0.5),
  )
})

test("Remote processing-unit search selects a unit beyond the initial 100 results", async ({
  page,
}) => {
  const processingUnitName = uniqueValue("E2E-remote-processing-unit")
  const noisePrefix = uniqueValue("E2E-newer-processing-unit")

  await page.goto("/inventory/raw")
  await expect(page.getByRole("heading", { name: "坯布台账" })).toBeVisible()

  await createInventoryFixture(page, "/processing-units", {
    name: processingUnitName,
  })
  for (let index = 0; index < 100; index += 1) {
    await createInventoryFixture(page, "/processing-units", {
      name: `${noisePrefix}-${index}`,
    })
  }

  const initialProcessingUnitPage = await readInventoryFixture<{
    data: MasterUnitPublic[]
  }>(page, "/processing-units?limit=100&skip=0")
  expect(
    initialProcessingUnitPage.data.some(
      (unit) => unit.name === processingUnitName,
    ),
  ).toBeFalsy()

  const filterSelect = page.getByRole("combobox", { name: "加工单位" })
  await expect(filterSelect).toHaveCount(1)
  const filterSearchResponse = page.waitForResponse(
    (response) =>
      response.request().method() === "GET" &&
      isProcessingUnitSearchRequest(
        response.url(),
        processingUnitName,
        undefined,
      ),
  )
  await filterSelect.click()
  await filterSelect.fill(processingUnitName)
  expect((await filterSearchResponse).ok()).toBeTruthy()

  const filterOption = page.getByRole("option", {
    exact: true,
    name: processingUnitName,
  })
  await expect(filterOption).toHaveCount(1)
  await filterOption.click()
  await expect(filterSelect).toHaveValue(processingUnitName)

  await page.getByRole("button", { name: "新建来料入库" }).click()
  const receiptDialog = page.getByRole("dialog", { name: "新建坯布入库" })
  await expect(receiptDialog).toBeVisible()
  const editorSelect = receiptDialog.getByRole("combobox", {
    name: "加工单位",
  })
  await expect(editorSelect).toHaveCount(1)
  const editorSearchResponse = page.waitForResponse(
    (response) =>
      response.request().method() === "GET" &&
      isProcessingUnitSearchRequest(response.url(), processingUnitName, true),
  )
  await editorSelect.click()
  await editorSelect.fill(processingUnitName)
  expect((await editorSearchResponse).ok()).toBeTruthy()

  const editorOption = page.getByRole("option", {
    exact: true,
    name: processingUnitName,
  })
  await expect(editorOption).toHaveCount(1)
  await editorOption.click()
  await expect(editorSelect).toHaveValue(processingUnitName)
})

test("Inventory document pages provide scoped Excel actions and issue feedback", async ({
  page,
}) => {
  await page.goto("/inventory/raw")
  await expect(page.getByRole("button", { name: "下载模板" })).toBeVisible()
  await expect(page.getByRole("button", { name: "导入 Excel" })).toBeVisible()
  await expect(page.getByRole("button", { name: "导出台账" })).toBeVisible()

  const templateDownload = page.waitForEvent("download")
  await page.getByRole("button", { name: "下载模板" }).click()
  expect((await templateDownload).suggestedFilename()).toBe(
    "inventory-document-template.xlsx",
  )

  await page.getByRole("textbox", { name: "单号 :" }).fill("XLSX-E2E")
  const exportRequest = page.waitForRequest((request) => {
    if (request.method() !== "GET") return false
    const url = new URL(request.url())
    return (
      url.pathname === "/api/v1/inventory/excel/ledger" &&
      url.searchParams.get("document_number") === "XLSX-E2E" &&
      url.searchParams.get("ledger_kind") === "RAW"
    )
  })
  const ledgerDownload = page.waitForEvent("download")
  await page.getByRole("button", { name: "导出台账" }).click()
  expect((await exportRequest).method()).toBe("GET")
  expect((await ledgerDownload).suggestedFilename()).toBe(
    "inventory-ledger-raw.xlsx",
  )

  let importRequests = 0
  await page.route("**/api/v1/inventory/excel/imports/documents*", (route) => {
    importRequests += 1
    return route.fulfill({
      body: JSON.stringify({
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
        request_id: "excel-e2e-request",
      }),
      contentType: "application/json",
      status: 422,
    })
  })
  await page.getByRole("button", { name: "导入 Excel" }).click()
  const importDialog = page.getByRole("dialog", { name: "导入坯布台账" })
  const fileInput = importDialog.locator('input[type="file"]')
  await fileInput.setInputFiles({
    buffer: Buffer.from("workbook"),
    mimeType:
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    name: "valid.xlsx",
  })
  await fileInput.setInputFiles({
    buffer: Buffer.from("not-a-workbook"),
    mimeType: "text/csv",
    name: "invalid.csv",
  })
  await importDialog.getByRole("button", { name: /导\s*入/ }).click()
  await expect(page.getByText("请选择要导入的工作簿。")).toBeVisible()
  expect(importRequests).toBe(0)

  await fileInput.setInputFiles({
    buffer: Buffer.from("not-a-workbook"),
    mimeType:
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    name: "invalid.xlsx",
  })
  await importDialog.getByRole("button", { name: /导\s*入/ }).click()
  await expect.poll(() => importRequests).toBe(1)
  await expect(importDialog.getByText("Excel validation failed")).toBeVisible()
  await expect(
    importDialog.getByRole("cell", {
      name: "Document type is not allowed for this import",
    }),
  ).toBeVisible()

  await page.goto("/inventory/shipments")
  await expect(page.getByRole("button", { name: "下载模板" })).toBeVisible()
  await expect(page.getByRole("button", { name: "导入 Excel" })).toBeVisible()
  await expect(page.getByRole("button", { name: "导出台账" })).toBeVisible()
})
