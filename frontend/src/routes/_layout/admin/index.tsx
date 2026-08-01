import { createFileRoute } from "@tanstack/react-router"

import { requirePermission } from "@/app/router/guards"
import { AdminUsersPage } from "@/platform/system/pages/AdminUsersPage"

export const Route = createFileRoute("/_layout/admin/")({
  beforeLoad: requirePermission("system.users.read"),
  component: AdminUsersPage,
})
