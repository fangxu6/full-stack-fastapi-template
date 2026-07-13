import { Briefcase, FileText, Home, PackageSearch, Users } from "lucide-react"
import type { AppNavigationItem } from "@/app/navigation/types"
import type { UserPublic } from "@/client"
import { canAccessAdmin } from "@/shared/permissions"

export const baseMenuItems: AppNavigationItem[] = [
  { icon: Home, title: "Dashboard", path: "/" },
  { icon: FileText, title: "Rules", path: "/rules" },
  { icon: Briefcase, title: "Items", path: "/items" },
  { icon: PackageSearch, title: "库存管理", path: "/inventory/raw" },
]

export const adminMenuItem: AppNavigationItem = {
  icon: Users,
  title: "Admin",
  path: "/admin",
}

export function getMenuItemsForUser(
  user?: UserPublic | null,
): AppNavigationItem[] {
  return canAccessAdmin(user)
    ? [...baseMenuItems, adminMenuItem]
    : baseMenuItems
}
