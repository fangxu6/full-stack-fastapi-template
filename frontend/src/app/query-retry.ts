import type { AxiosResponse } from "axios"
import { isAxiosError } from "axios"

import { ApiError } from "@/client"

const RETRY_DELAYS_MS = [1_000, 2_000]
const MAX_RETRY_AFTER_MS = 30_000

function isReadMethod(method: unknown) {
  return (
    typeof method === "string" &&
    ["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase())
  )
}

function retryAfterFromResponse(response: AxiosResponse) {
  const value = response.headers["retry-after"]
  return typeof value === "string" ? value : undefined
}

export class RateLimitError extends Error {
  readonly method: string | undefined
  readonly retryAfter: string | undefined

  constructor(response: AxiosResponse) {
    super(response.statusText || "Too Many Requests")
    this.name = "RateLimitError"
    this.method = response.config.method
    this.retryAfter = retryAfterFromResponse(response)
  }
}

export function captureRateLimitResponse(response: AxiosResponse) {
  if (response.status === 429) throw new RateLimitError(response)
  return response
}

function requestMethod(error: unknown) {
  if (error instanceof ApiError) return error.request.method
  if (error instanceof RateLimitError) return error.method
  if (isAxiosError(error)) return error.config?.method
  return undefined
}

function responseStatus(error: unknown) {
  if (error instanceof ApiError) return error.status
  if (error instanceof RateLimitError) return 429
  if (isAxiosError(error)) return error.response?.status
  return undefined
}

function isCancelled(error: unknown) {
  return (
    error instanceof Error &&
    (error.name === "AbortError" ||
      error.name === "CancelError" ||
      error.name === "CanceledError" ||
      (isAxiosError(error) && error.code === "ERR_CANCELED"))
  )
}

function retryAfterDelay(value: string | undefined, now: number) {
  if (!value) return undefined
  if (/^\d+$/.test(value)) {
    const delay = Number(value) * 1_000
    return delay <= MAX_RETRY_AFTER_MS ? delay : undefined
  }
  const retryAt = Date.parse(value)
  const delay = retryAt - now
  return Number.isNaN(retryAt) || delay < 0 || delay > MAX_RETRY_AFTER_MS
    ? undefined
    : delay
}

function retryAfterHeader(error: unknown) {
  if (error instanceof RateLimitError) return error.retryAfter
  if (isAxiosError(error) && error.response) {
    return retryAfterFromResponse(error.response)
  }
  return undefined
}

export function shouldRetryQuery(failureCount: number, error: unknown) {
  if (
    failureCount >= RETRY_DELAYS_MS.length ||
    isCancelled(error) ||
    !isReadMethod(requestMethod(error))
  ) {
    return false
  }
  const status = responseStatus(error)
  if (status === undefined) return isAxiosError(error) && !error.response
  return status === 408 || status === 429 || (status >= 500 && status < 600)
}

export function queryRetryDelay(
  retryAttempt: number,
  error: unknown,
  now = Date.now(),
) {
  return (
    retryAfterDelay(retryAfterHeader(error), now) ??
    RETRY_DELAYS_MS[retryAttempt] ??
    RETRY_DELAYS_MS[RETRY_DELAYS_MS.length - 1]
  )
}
