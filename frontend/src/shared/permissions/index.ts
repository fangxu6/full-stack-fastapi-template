import type { UserPublic } from "@/client"

type PermissionUser = Pick<UserPublic, "is_superuser"> | null | undefined

export function canAccessAdmin(user: PermissionUser): boolean {
  return Boolean(user?.is_superuser)
}
