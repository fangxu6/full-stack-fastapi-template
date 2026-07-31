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

test("Scheduler hides backfill for tasks that cannot replay a historical time", async ({
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
  await expect(row.getByRole("button", { name: "立即执行" })).toBeVisible()
  await expect(row.getByRole("button", { name: "补发任务" })).toHaveCount(0)
})
