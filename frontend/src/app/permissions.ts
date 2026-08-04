import { queryOptions } from "@tanstack/react-query"

import { queryClient } from "@/app/query-client"
import { IamService } from "@/client"

const MY_PERMISSIONS_QUERY_KEY = ["iam", "permissions"] as const

export const myPermissionsQueryOptions = queryOptions({
  queryKey: MY_PERMISSIONS_QUERY_KEY,
  queryFn: IamService.readMyPermissions,
  staleTime: 30_000,
})

export type MyPermissions = Awaited<
  ReturnType<typeof IamService.readMyPermissions>
>
export type PermissionQueryErrorOutcome = "configuration" | "login" | "retry"

function getErrorStatus(error: unknown): number | undefined {
  if (typeof error !== "object" || error === null || !("status" in error)) {
    return undefined
  }
  return typeof error.status === "number" ? error.status : undefined
}

export function classifyPermissionQueryError(
  error: unknown,
): PermissionQueryErrorOutcome {
  const status = getErrorStatus(error)
  if (status === 401) return "login"
  if (status === 403) return "configuration"
  return "retry"
}

export function readMyPermissionsForRoute(): Promise<MyPermissions> {
  return queryClient.fetchQuery({
    ...myPermissionsQueryOptions,
    staleTime: 0,
  })
}
