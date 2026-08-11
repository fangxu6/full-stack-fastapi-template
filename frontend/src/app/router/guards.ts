import { redirect } from "@tanstack/react-router"

import {
  classifyPermissionQueryError,
  type MyPermissions,
  readMyPermissionsForRoute,
} from "@/app/permissions"
import { clearAuthState } from "@/app/query-client"
import { isLoggedIn } from "@/platform/auth/hooks/useAuth"
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

export function requirePermission(permission: PermissionCode) {
  return async ({
    location,
  }: {
    location: { pathname: string; searchStr: string }
  }) => {
    const returnTo = `${location.pathname}${location.searchStr}`
    let result: MyPermissions
    try {
      result = await readMyPermissionsForRoute()
    } catch (error) {
      const outcome = classifyPermissionQueryError(error)
      if (outcome === "login") {
        clearAuthState()
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
