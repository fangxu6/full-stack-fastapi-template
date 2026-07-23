import { expect, type Page, test } from "@playwright/test"

test.use({ storageState: { cookies: [], origins: [] } })

const protectedPath = "/inventory/balances"
const permissionsPath = "**/api/v1/iam/me/permissions"

async function prepareProtectedNavigation(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem("access_token", "permission-guard-test-token")
  })
}

async function expectForbiddenReason(
  page: Page,
  reason: "configuration" | "retry",
) {
  await expect(page).toHaveURL(/\/forbidden/)
  const url = new URL(page.url())
  expect(url.searchParams.get("reason")).toBe(reason)
  expect(url.searchParams.get("returnTo")).toBe(protectedPath)
}

test("own-permissions 401 redirects to login", async ({ page }) => {
  await prepareProtectedNavigation(page)
  await page.route(permissionsPath, (route) => route.fulfill({ status: 401 }))

  await page.goto(protectedPath)

  await expect(page).toHaveURL(/\/login$/)
})

test("own-permissions 403 shows the configuration error state", async ({
  page,
}) => {
  await prepareProtectedNavigation(page)
  await page.route(permissionsPath, (route) => route.fulfill({ status: 403 }))

  await page.goto(protectedPath)

  await expectForbiddenReason(page, "configuration")
  await expect(
    page.getByRole("heading", { name: "权限配置异常" }),
  ).toBeVisible()
})

test("own-permissions 5xx shows the retryable error state", async ({
  page,
}) => {
  await prepareProtectedNavigation(page)
  await page.route(permissionsPath, (route) => route.fulfill({ status: 500 }))

  await page.goto(protectedPath)

  await expectForbiddenReason(page, "retry")
  await expect(
    page.getByRole("heading", { name: "暂时无法校验权限" }),
  ).toBeVisible()
})

test("network failures show the retryable error state", async ({ page }) => {
  await prepareProtectedNavigation(page)
  await page.route(permissionsPath, (route) => route.abort())

  await page.goto(protectedPath)

  await expectForbiddenReason(page, "retry")
  await expect(
    page.getByRole("heading", { name: "暂时无法校验权限" }),
  ).toBeVisible()
})

test("retry returns to the protected page", async ({ page }) => {
  await prepareProtectedNavigation(page)
  let permissionChecks = 0
  await page.route(permissionsPath, (route) => {
    permissionChecks += 1
    return route.fulfill(
      permissionChecks === 1
        ? { status: 500 }
        : {
            body: JSON.stringify({
              permissions: ["inventory.balances.read"],
              roles: [],
            }),
            contentType: "application/json",
            status: 200,
          },
    )
  })

  await page.goto(protectedPath)

  await expectForbiddenReason(page, "retry")
  await page.getByRole("button", { name: "重试" }).click()
  await expect(page).toHaveURL(new RegExp(`${protectedPath}$`))
})

test("a successful response without permission shows forbidden", async ({
  page,
}) => {
  await prepareProtectedNavigation(page)
  await page.route(permissionsPath, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ permissions: [], roles: [] }),
      status: 200,
    }),
  )

  await page.goto(protectedPath)

  await expect(page).toHaveURL(/\/forbidden/)
  expect(new URL(page.url()).searchParams.get("reason")).toBeNull()
  await expect(page.getByRole("heading", { name: "无权访问" })).toBeVisible()
})
