export type PermissionCode =
  | "system.users.read"
  | "system.users.manage"
  | "iam.roles.read"
  | "iam.roles.manage"
  | "inventory.masters.read"
  | "inventory.masters.manage"
  | "inventory.documents.read"
  | "inventory.documents.manage"
  | "inventory.balances.read"
  | "inventory.ledger.read"
  | "scheduler.jobs.read"
  | "scheduler.jobs.manage"

export function hasPermission(
  permissions: readonly string[] | undefined,
  permission: PermissionCode,
): boolean {
  return Boolean(permissions?.includes(permission))
}

export function isSafeInternalPath(value: unknown): value is string {
  return (
    typeof value === "string" &&
    value.startsWith("/") &&
    !value.startsWith("//")
  )
}
