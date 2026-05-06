import { Briefcase, FileText, Home, Users } from "lucide-react";

import type { UserPublic } from "@/client";
import type { AppNavigationItem } from "@/app/navigation/types";
import { canAccessAdmin } from "@/shared/permissions";

export const baseMenuItems: AppNavigationItem[] = [
  { icon: Home, title: "Dashboard", path: "/" },
  { icon: FileText, title: "Rules", path: "/rules" },
  { icon: Briefcase, title: "Items", path: "/items" },
];

export const adminMenuItem: AppNavigationItem = {
  icon: Users,
  title: "Admin",
  path: "/admin",
};

export function getMenuItemsForUser(
  user?: UserPublic | null,
): AppNavigationItem[] {
  return canAccessAdmin(user) ? [...baseMenuItems, adminMenuItem] : baseMenuItems;
}
