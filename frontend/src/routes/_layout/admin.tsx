import { createFileRoute } from "@tanstack/react-router"

import { requirePermission } from "@/app/router/guards"
import { AdminUsersPage } from "@/platform/system/pages/AdminUsersPage"

export const Route = createFileRoute("/_layout/admin")({
  component: AdminUsersPage,
  beforeLoad: requirePermission("system.users.read"),
  head: () => ({
    meta: [
      {
        title: "Admin - FastAPI Template",
      },
    ],
  }),
})
