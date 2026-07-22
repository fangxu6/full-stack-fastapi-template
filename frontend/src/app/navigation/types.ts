import type { LucideIcon } from "lucide-react"
import type { PermissionCode } from "@/shared/permissions"

export type AppNavigationItem = {
  icon: LucideIcon
  title: string
  path: string
  permission?: PermissionCode
}
