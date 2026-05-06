import { createFileRoute } from "@tanstack/react-router"

import { requireSuperuser } from "@/app/router/guards"
import { AdminUsersPage } from "@/platform/system/pages/AdminUsersPage"

export const Route = createFileRoute("/_layout/admin")({
  component: AdminUsersPage,
  beforeLoad: requireSuperuser,
  head: () => ({
    meta: [
      {
        title: "Admin - FastAPI Template",
      },
    ],
  }),
})
