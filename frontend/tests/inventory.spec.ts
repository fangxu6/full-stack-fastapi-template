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

async function selectOption(page: Page, label: string, option: string) {
  await page.getByRole("dialog").getByRole("combobox", { name: label }).click()
  await page.getByText(option, { exact: true }).last().click()
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
  await expect(page.getByRole("dialog", { name: "新建坯布入库" })).toBeVisible()
  await page.getByLabel("单号").fill(documentNumber)
  await selectOption(page, "加工单位", processingUnit)
  await page.getByLabel("品名").fill(itemName)
  await page.getByLabel("品号").fill(itemCode)
  await page.getByLabel("含毛量").fill("100% wool")
  await page.getByLabel("匹数").fill("5")
  await page
    .getByRole("dialog")
    .getByRole("button", { name: /保\s*存/ })
    .click()

  await expect(page.getByText("单据已保存")).toBeVisible()
  const receiptRow = page.getByRole("row").filter({ hasText: documentNumber })
  await expect(receiptRow).toBeVisible()

  await page.getByLabel("单号").fill(documentNumber)
  await expect(receiptRow).toBeVisible()

  await page.goto("/inventory/balances")
  const balanceRow = page.getByRole("row").filter({ hasText: itemCode })
  await expect(balanceRow).toContainText("5")
  await balanceRow.click()
  await expect(
    page.getByRole("dialog", { name: `${itemName} 关联台账` }),
  ).toBeVisible()
  await expect(page.getByText("RAW_RECEIPT")).toBeVisible()

  await page.goto("/inventory/raw")
  await receiptRow.getByRole("button", { name: "删除单据" }).click()
  await page.getByRole("button", { name: /确\s*定/ }).click()
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
  const balances = await readInventoryFixture<{
    data: InventoryBalancePublic[]
  }>(page, "/balances/finished")
  const balance = balances.data.find(
    (candidate) =>
      Number(candidate.rolls_balance) >= 0.5 &&
      Number(candidate.meters_balance) >= 12.5 &&
      candidate.color_code &&
      candidate.dye_lot_no,
  )
  if (!balance?.color_code || !balance.dye_lot_no) {
    throw new Error("The E2E database needs a finished inventory balance")
  }
  const processingUnits = await readInventoryFixture<{
    data: MasterUnitPublic[]
  }>(page, "/processing-units")
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
  await page.getByLabel("单号").fill(documentNumber)
  await selectOption(page, "加工单位", processingUnit.name)
  await selectOption(page, "收货单位", receivingUnitName)
  await page.getByLabel("品名").fill(balance.item_name)
  await page.getByLabel("含毛量").fill(balance.wool_content)
  await page.getByLabel("颜色/色号").fill(balance.color_code)
  await page.getByLabel("缸号").fill(balance.dye_lot_no)
  await page.getByLabel("匹数").fill("0.5")
  await page.getByLabel("米数").fill("12.5")
  await page
    .getByRole("dialog")
    .getByRole("button", { name: /保\s*存/ })
    .click()

  await expect(page.getByText("单据已保存")).toBeVisible()
  await expect(
    page.getByRole("row").filter({ hasText: documentNumber }),
  ).toBeVisible()

  await page.goto("/inventory/balances")
  await page.getByRole("tab", { name: "成品库存" }).click()
  const balanceRow = page
    .getByRole("row")
    .filter({ hasText: balance.item_name })
  await expect(balanceRow).toContainText(
    String(Number(balance.rolls_balance) - 0.5),
  )
})
