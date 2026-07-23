import { redirect } from "@tanstack/react-router"

import { IamService } from "@/client"
import { isLoggedIn } from "@/hooks/useAuth"
import {
  hasPermission,
  isSafeInternalPath,
  type PermissionCode,
} from "@/shared/permissions"

export async function requireLogin() {
  if (!isLoggedIn()) {
    throw redirect({
      to: "/login",
    })
  }
}

type PermissionQueryErrorOutcome = "configuration" | "login" | "retry"
type MyPermissions = Awaited<ReturnType<typeof IamService.readMyPermissions>>

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

export function requirePermission(permission: PermissionCode) {
  return async ({
    location,
  }: {
    location: { pathname: string; searchStr: string }
  }) => {
    const returnTo = `${location.pathname}${location.searchStr}`
    let result: MyPermissions
    try {
      result = await IamService.readMyPermissions()
    } catch (error) {
      const outcome = classifyPermissionQueryError(error)
      if (outcome === "login") {
        localStorage.removeItem("access_token")
        throw redirect({ to: "/login" })
      }
      if (outcome === "configuration") {
        throw redirect({
          to: "/forbidden",
          search: {
            reason: "configuration",
            returnTo: isSafeInternalPath(returnTo) ? returnTo : "/",
          },
        })
      }
      throw redirect({
        to: "/forbidden",
        search: {
          reason: "retry",
          returnTo: isSafeInternalPath(returnTo) ? returnTo : "/",
        },
      })
    }
    if (!hasPermission(result.permissions, permission)) {
      throw redirect({
        to: "/forbidden",
        search: {
          reason: undefined,
          returnTo: isSafeInternalPath(returnTo) ? returnTo : "/",
        },
      })
    }
  }
}
