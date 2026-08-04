import { describe, expect, test } from "bun:test"

import { classifyPermissionQueryError } from "@/app/permissions"

describe("classifyPermissionQueryError", () => {
  test("classifies 401 as a login redirect", () => {
    expect(classifyPermissionQueryError({ status: 401 })).toBe("login")
  })

  test("classifies 403 as an authenticated configuration error", () => {
    expect(classifyPermissionQueryError({ status: 403 })).toBe("configuration")
  })

  test("classifies 5xx responses as retryable", () => {
    expect(classifyPermissionQueryError({ status: 500 })).toBe("retry")
  })

  test("classifies network failures as retryable", () => {
    expect(classifyPermissionQueryError(new TypeError("Network error"))).toBe(
      "retry",
    )
  })
})
