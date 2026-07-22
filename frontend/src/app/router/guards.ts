import { redirect } from "@tanstack/react-router"

import { ApiError, IamService } from "@/client"
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

export function requirePermission(permission: PermissionCode) {
  return async ({
    location,
  }: {
    location: { pathname: string; searchStr: string }
  }) => {
    try {
      const result = await IamService.readMyPermissions()
      if (!hasPermission(result.permissions, permission)) {
        const returnTo = `${location.pathname}${location.searchStr}`
        throw redirect({
          to: "/forbidden",
          search: { returnTo: isSafeInternalPath(returnTo) ? returnTo : "/" },
        })
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        throw redirect({ to: "/login" })
      }
      throw error
    }
  }
}
