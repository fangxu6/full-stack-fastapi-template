import { expect, test as setup } from "@playwright/test"
import { firstSuperuser, firstSuperuserPassword } from "./config.ts"

const authFile = "playwright/.auth/user.json"

setup("authenticate", async ({ page }) => {
  await page.goto("/login")
  await page.getByTestId("email-input").fill(firstSuperuser)
  await page.getByTestId("password-input").fill(firstSuperuserPassword)
  const loginResponse = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      response.url().endsWith("/api/v1/login/access-token"),
  )
  await page.getByRole("button", { name: "Log In" }).click()
  const response = await loginResponse
  expect(response.ok(), await response.text()).toBeTruthy()
  const token = await page.evaluate(() => localStorage.getItem("access_token"))
  expect(token).toBeTruthy()
  const apiBaseUrl = process.env.VITE_API_URL ?? "http://localhost:8000"
  const headers = { Authorization: `Bearer ${token}` }
  const currentUserResponse = await page.request.get(
    `${apiBaseUrl}/api/v1/users/me`,
    { headers },
  )
  expect(
    currentUserResponse.ok(),
    await currentUserResponse.text(),
  ).toBeTruthy()
  const currentUser = (await currentUserResponse.json()) as {
    id: string
    roles?: Array<{ id: number }>
  }
  const rolesResponse = await page.request.get(
    `${apiBaseUrl}/api/v1/iam/roles`,
    {
      headers,
    },
  )
  expect(rolesResponse.ok(), await rolesResponse.text()).toBeTruthy()
  const roles = (await rolesResponse.json()) as {
    data: Array<{ id: number; code: string; permission_codes: string[] }>
  }
  const permissionCatalogResponse = await page.request.get(
    `${apiBaseUrl}/api/v1/iam/permissions`,
    { headers },
  )
  expect(
    permissionCatalogResponse.ok(),
    await permissionCatalogResponse.text(),
  ).toBeTruthy()
  const permissionCatalog = (await permissionCatalogResponse.json()) as {
    data: Array<{ code: string }>
  }
  const permissionCodes = new Set(
    permissionCatalog.data.map((permission) => permission.code),
  )
  const schedulerPermissionsAvailable =
    permissionCodes.has("scheduler.jobs.read") &&
    permissionCodes.has("scheduler.jobs.manage")
  let schedulerRole = roles.data.find((role) => role.code === "e2e_scheduler")
  if (schedulerPermissionsAvailable && !schedulerRole) {
    const createRoleResponse = await page.request.post(
      `${apiBaseUrl}/api/v1/iam/roles`,
      {
        data: {
          code: "e2e_scheduler",
          name: "E2E Scheduler",
          permission_codes: ["scheduler.jobs.read", "scheduler.jobs.manage"],
        },
        headers,
      },
    )
    expect(
      createRoleResponse.ok(),
      await createRoleResponse.text(),
    ).toBeTruthy()
    schedulerRole = (await createRoleResponse.json()) as typeof schedulerRole
  }
  if (schedulerPermissionsAvailable && !schedulerRole) {
    throw new Error("E2E scheduler role was not created")
  }
  if (
    schedulerPermissionsAvailable &&
    schedulerRole &&
    (!schedulerRole.permission_codes.includes("scheduler.jobs.manage") ||
      !schedulerRole.permission_codes.includes("scheduler.jobs.read"))
  ) {
    const updatePermissionsResponse = await page.request.put(
      `${apiBaseUrl}/api/v1/iam/roles/${schedulerRole.id}/permissions`,
      {
        data: {
          permission_codes: [
            ...new Set([
              ...schedulerRole.permission_codes,
              "scheduler.jobs.read",
              "scheduler.jobs.manage",
            ]),
          ],
        },
        headers,
      },
    )
    expect(
      updatePermissionsResponse.ok(),
      await updatePermissionsResponse.text(),
    ).toBeTruthy()
  }
  if (schedulerPermissionsAvailable && schedulerRole) {
    const roleIds = new Set((currentUser.roles ?? []).map((role) => role.id))
    roleIds.add(schedulerRole.id)
    const replaceRolesResponse = await page.request.put(
      `${apiBaseUrl}/api/v1/iam/users/${currentUser.id}/roles`,
      { data: { role_ids: [...roleIds] }, headers },
    )
    expect(
      replaceRolesResponse.ok(),
      await replaceRolesResponse.text(),
    ).toBeTruthy()
  }
  const permissionsResponse = await page.request.get(
    `${apiBaseUrl}/api/v1/iam/me/permissions`,
    { headers },
  )
  expect(
    permissionsResponse.ok(),
    await permissionsResponse.text(),
  ).toBeTruthy()
  const permissions = (await permissionsResponse.json()) as {
    permissions?: string[]
  }
  if (schedulerPermissionsAvailable) {
    expect(permissions.permissions).toContain("scheduler.jobs.manage")
  }
  await expect(page).toHaveURL("/")
  await page.context().storageState({ path: authFile })
})
