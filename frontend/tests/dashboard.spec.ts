import { expect, test } from "@playwright/test"

test("authenticated user can view the dashboard at the root route", async ({
  page,
}) => {
  await page.goto("/")

  await expect(page).toHaveURL(/\/$/)
  await expect(page.getByRole("heading", { name: /Hi,/ })).toBeVisible()
})
