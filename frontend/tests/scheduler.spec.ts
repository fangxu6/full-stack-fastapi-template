import { expect, type Page, test } from "@playwright/test"

const apiBaseUrl =
  process.env.PLAYWRIGHT_E2E_API_URL ??
  process.env.VITE_API_URL ??
  "http://localhost:8000"

async function authenticatedHeaders(page: Page) {
  const token = await page.evaluate(() => localStorage.getItem("access_token"))
  expect(token).toBeTruthy()
  return { Authorization: `Bearer ${token}` }
}

test("Scheduler backfill uses Shanghai local wall-clock time for its maximum", async ({
  page,
}) => {
  await page.clock.install({ time: new Date("2026-07-26T00:30:00.000Z") })
  await page.goto("/")
  const name = `E2E scheduler ${Date.now()}`
  const create = await page.request.post(
    `${apiBaseUrl}/api/v1/scheduler/jobs`,
    {
      data: {
        class_path:
          "app.modules.inventory.scheduled_tasks.InventoryDailyReportRetryTask",
        config: {},
        cron_expression: "* * * * *",
        name,
      },
      headers: await authenticatedHeaders(page),
    },
  )
  expect(create.ok(), await create.text()).toBeTruthy()

  await page.goto("/scheduler/jobs")
  const row = page.getByRole("row").filter({ hasText: name })
  await expect(row).toBeVisible()
  await row.getByRole("button", { name: "补发任务" }).click()
  const dialog = page.getByRole("dialog", { name: "补发任务" })
  const input = dialog.locator('input[type="datetime-local"]')
  await expect(input).toHaveAttribute("max", "2026-07-26T08:30")
  await input.fill("2026-07-26T08:29")

  const response = page.waitForResponse(
    (candidate) =>
      candidate.request().method() === "POST" &&
      /\/api\/v1\/scheduler\/jobs\/\d+\/backfill$/.test(
        new URL(candidate.url()).pathname,
      ),
  )
  await dialog.getByRole("button", { name: "OK", exact: true }).click()
  const request = await response
  expect(request.ok(), await request.text()).toBeTruthy()
  expect(request.request().postDataJSON()).toEqual({
    planned_at: "2026-07-26T00:29:00.000Z",
  })
})
