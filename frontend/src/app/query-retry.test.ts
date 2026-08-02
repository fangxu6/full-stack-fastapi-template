import { describe, expect, test } from "bun:test"
import type { AxiosResponse } from "axios"

import { ApiError } from "@/client"
import {
  captureRateLimitResponse,
  queryRetryDelay,
  RateLimitError,
  shouldRetryQuery,
} from "./query-retry"

function apiError(method: ApiError["request"]["method"], status: number) {
  return new ApiError(
    { method, url: "/test" },
    {
      body: null,
      ok: false,
      status,
      statusText: "Request failed",
      url: "/test",
    },
    "Request failed",
  )
}

function response(method: string, retryAfter?: string): AxiosResponse {
  return {
    config: { method },
    data: null,
    headers: retryAfter ? { "retry-after": retryAfter } : {},
    status: 429,
    statusText: "Too Many Requests",
  } as AxiosResponse
}

describe("query retry policy", () => {
  test("retries transient read failures at most twice", () => {
    for (const status of [408, 429, 500, 503]) {
      for (const method of ["GET", "HEAD", "OPTIONS"] as const) {
        expect(shouldRetryQuery(0, apiError(method, status))).toBe(true)
      }
    }
    expect(shouldRetryQuery(2, apiError("GET", 503))).toBe(false)
    expect(shouldRetryQuery(0, apiError("GET", 400))).toBe(false)
    expect(shouldRetryQuery(0, apiError("GET", 422))).toBe(false)
  })

  test("fails closed for write, unknown, and cancelled requests", () => {
    for (const method of ["POST", "PUT", "PATCH", "DELETE"] as const) {
      expect(shouldRetryQuery(0, apiError(method, 503))).toBe(false)
    }
    const networkError = Object.assign(new Error("Network error"), {
      config: { method: "get" },
      isAxiosError: true,
    })
    const cancelledError = Object.assign(new Error("Request aborted"), {
      code: "ERR_CANCELED",
      config: { method: "get" },
      isAxiosError: true,
    })
    expect(shouldRetryQuery(0, networkError)).toBe(true)
    expect(shouldRetryQuery(0, cancelledError)).toBe(false)
    expect(
      shouldRetryQuery(
        0,
        Object.assign(new Error("Network error"), { isAxiosError: true }),
      ),
    ).toBe(false)
  })

  test("honors bounded Retry-After values", () => {
    const retryAfter = new RateLimitError(response("get", "5"))
    const retryDate = new RateLimitError(
      response("get", new Date(5_000).toUTCString()),
    )
    expect(queryRetryDelay(0, retryAfter, 0)).toBe(5_000)
    expect(queryRetryDelay(0, retryDate, 0)).toBe(5_000)
    for (const header of [undefined, "invalid", "31"]) {
      expect(
        queryRetryDelay(0, new RateLimitError(response("get", header)), 0),
      ).toBe(1_000)
    }
    expect(
      queryRetryDelay(
        0,
        new RateLimitError(response("get", new Date(-1_000).toUTCString())),
        0,
      ),
    ).toBe(1_000)
    expect(() => captureRateLimitResponse(response("get", "5"))).toThrow(
      RateLimitError,
    )
  })
})
