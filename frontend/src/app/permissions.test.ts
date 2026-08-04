import { describe, expect, test } from "bun:test"

import { myPermissionsQueryOptions } from "./permissions"

describe("permission query access", () => {
  test("shares the permission cache contract with a bounded UI freshness window", () => {
    expect([...myPermissionsQueryOptions.queryKey]).toEqual([
      "iam",
      "permissions",
    ])
    expect(myPermissionsQueryOptions.staleTime).toBe(30_000)
    expect(myPermissionsQueryOptions.queryFn).toBeFunction()
  })
})
