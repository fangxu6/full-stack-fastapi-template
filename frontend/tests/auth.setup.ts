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
  await expect(page).toHaveURL("/")
  await page.context().storageState({ path: authFile })
})
