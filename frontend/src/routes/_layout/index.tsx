import { createFileRoute } from "@tanstack/react-router"

import { DashboardPage } from "@/platform/dashboard/pages/DashboardPage"

export const Route = createFileRoute("/_layout/")({
  component: DashboardPage,
  head: () => ({
    meta: [
      {
        title: "Dashboard - FastAPI Template",
      },
    ],
  }),
})
