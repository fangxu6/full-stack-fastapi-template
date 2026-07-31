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
  const jobId = (await create.json()).id as number

  await page.route(`${apiBaseUrl}/api/v1/scheduler/jobs?**`, async (route) => {
    const response = await route.fetch()
    const jobs = await response.json()
    await route.fulfill({
      response,
      json: {
        ...jobs,
        data: jobs.data.map((job: { id: number }) =>
          job.id === jobId ? { ...job, can_backfill: true } : job,
        ),
      },
    })
  })
  await page.route(
    `${apiBaseUrl}/api/v1/scheduler/jobs/${jobId}/backfill`,
    async (route) => {
      expect(route.request().postDataJSON()).toEqual({
        planned_at: "2026-07-26T00:29:00.000Z",
      })
      await route.fulfill({ contentType: "application/json", json: {} })
    },
  )

  await page.goto("/scheduler/jobs")
  const row = page.getByRole("row").filter({ hasText: name })
  await expect(row).toBeVisible()
  await row.getByRole("button", { name: "补发任务" }).click()
  const dialog = page.getByRole("dialog", { name: "补发任务" })
  const input = dialog.locator('input[type="datetime-local"]')
  await expect(input).toHaveAttribute("max", "2026-07-26T08:30")
  await input.fill("2026-07-26T08:29")
  await dialog.getByRole("button", { name: "OK", exact: true }).click()
})
