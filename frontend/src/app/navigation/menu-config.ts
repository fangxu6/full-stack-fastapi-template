import {
  Briefcase,
  ClipboardList,
  FileText,
  Home,
  PackageSearch,
  Settings2,
  Truck,
  Users,
} from "lucide-react"
import type { AppNavigationItem } from "@/app/navigation/types"
import type { UserPublic } from "@/client"
import { canAccessAdmin } from "@/shared/permissions"

export const baseMenuItems: AppNavigationItem[] = [
  { icon: Home, title: "Dashboard", path: "/" },
  { icon: FileText, title: "Rules", path: "/rules" },
  { icon: Briefcase, title: "Items", path: "/items" },
  { icon: Settings2, title: "主数据", path: "/inventory/masters" },
  { icon: PackageSearch, title: "坯布台账", path: "/inventory/raw" },
  { icon: Truck, title: "成品出货", path: "/inventory/shipments" },
  { icon: ClipboardList, title: "库存余额", path: "/inventory/balances" },
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
