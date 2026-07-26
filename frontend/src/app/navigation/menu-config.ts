import {
  Briefcase,
  CalendarClock,
  ClipboardList,
  FileText,
  Home,
  PackageSearch,
  Settings2,
  ShieldCheck,
  Truck,
  Users,
} from "lucide-react"
import type { AppNavigationItem } from "@/app/navigation/types"
import { hasPermission } from "@/shared/permissions"

export const baseMenuItems: AppNavigationItem[] = [
  { icon: Home, title: "Dashboard", path: "/" },
  { icon: FileText, title: "Rules", path: "/rules" },
  { icon: Briefcase, title: "Items", path: "/items" },
  {
    icon: Settings2,
    title: "主数据",
    path: "/inventory/masters",
    permission: "inventory.masters.read",
  },
  {
    icon: PackageSearch,
    title: "坯布台账",
    path: "/inventory/raw",
    permission: "inventory.documents.read",
  },
  {
    icon: Truck,
    title: "成品出货",
    path: "/inventory/shipments",
    permission: "inventory.documents.read",
  },
  {
    icon: ClipboardList,
    title: "库存余额",
    path: "/inventory/balances",
    permission: "inventory.balances.read",
  },
  {
    icon: CalendarClock,
    title: "定时任务",
    path: "/scheduler/jobs",
    permission: "scheduler.jobs.read",
  },
]

export const adminMenuItem: AppNavigationItem = {
  icon: Users,
  title: "用户管理",
  path: "/admin",
  permission: "system.users.read",
}

export const rolesMenuItem: AppNavigationItem = {
  icon: ShieldCheck,
  title: "角色管理",
  path: "/admin/roles",
  permission: "iam.roles.read",
}

export function getMenuItemsForUser(
  permissions?: readonly string[],
): AppNavigationItem[] {
  return [...baseMenuItems, adminMenuItem, rolesMenuItem].filter(
    (item) => !item.permission || hasPermission(permissions, item.permission),
  )
}
