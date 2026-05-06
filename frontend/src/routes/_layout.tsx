import { createFileRoute } from "@tanstack/react-router"

import { AppLayout } from "@/app/layout/AppLayout"
import { requireLogin } from "@/app/router/guards"

export const Route = createFileRoute("/_layout")({
  component: AppLayout,
  beforeLoad: requireLogin,
})
