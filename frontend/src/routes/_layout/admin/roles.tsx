import { createFileRoute } from "@tanstack/react-router"

import { requirePermission } from "@/app/router/guards"
import { AdminRolesPage } from "@/platform/system/pages/AdminRolesPage"

export const Route = createFileRoute("/_layout/admin/roles")({
  beforeLoad: requirePermission("iam.roles.read"),
  component: AdminRolesPage,
})
