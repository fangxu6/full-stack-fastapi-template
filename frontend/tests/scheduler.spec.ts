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

test("Scheduler previews an unsaved Cron and replaces stale results with inline errors", async ({
  page,
}) => {
  await page.clock.install({ time: new Date("2026-07-26T00:30:00.000Z") })
  await page.route(
    `${apiBaseUrl}/api/v1/scheduler/cron-preview?**`,
    async (route) => {
      const cronExpression = new URL(route.request().url()).searchParams.get(
        "cron_expression",
      )
      if (cronExpression === "0 8 * *") {
        await route.fulfill({
          contentType: "application/json",
          json: {
            detail: "cron expression must contain exactly five fields",
            request_id: "preview-invalid-cron",
          },
          status: 422,
        })
        return
      }
      const nextRunAts =
        cronExpression === "*/15 * * * *"
          ? [
              "2026-07-26T00:45:00.000Z",
              "2026-07-26T01:00:00.000Z",
              "2026-07-26T01:15:00.000Z",
              "2026-07-26T01:30:00.000Z",
              "2026-07-26T01:45:00.000Z",
            ]
          : [
              "2026-07-27T00:00:00.000Z",
              "2026-07-28T00:00:00.000Z",
              "2026-07-29T00:00:00.000Z",
              "2026-07-30T00:00:00.000Z",
              "2026-07-31T00:00:00.000Z",
            ]
      await route.fulfill({
        contentType: "application/json",
        json: {
          base_at: "2026-07-26T00:30:00.000Z",
          next_run_ats: nextRunAts,
          timezone: "Asia/Shanghai",
        },
      })
    },
  )

  await page.goto("/scheduler/jobs")
  await page.getByRole("button", { name: "新建任务" }).click()
  const dialog = page.getByRole("dialog", { name: "新建定时任务" })
  const cronInput = dialog.getByLabel("Cron")
  const expectedDailyTime = new Date("2026-07-27T00:00:00.000Z").toLocaleString(
    "zh-CN",
    { timeZone: "Asia/Shanghai" },
  )

  await cronInput.fill("0 8 * * *")
  await page.clock.fastForward(300)
  await expect(dialog.getByText("后续执行时点（Asia/Shanghai）")).toBeVisible()
  await expect(dialog.getByText(expectedDailyTime)).toBeVisible()

  await cronInput.fill("0 8 * *")
  await expect(dialog.getByText(expectedDailyTime)).toHaveCount(0)
  await page.clock.fastForward(300)
  await expect(
    dialog.getByText("cron expression must contain exactly five fields"),
  ).toBeVisible()

  await cronInput.fill("*/15 * * * *")
  await expect(
    dialog.getByText("cron expression must contain exactly five fields"),
  ).toHaveCount(0)
  await page.clock.fastForward(300)
  const expectedQuarterHourTime = new Date(
    "2026-07-26T00:45:00.000Z",
  ).toLocaleString("zh-CN", { timeZone: "Asia/Shanghai" })
  await expect(dialog.getByText(expectedQuarterHourTime)).toBeVisible()
})
