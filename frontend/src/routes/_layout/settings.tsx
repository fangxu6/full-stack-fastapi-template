import { createFileRoute } from "@tanstack/react-router"

import { UserSettingsPage } from "@/platform/auth/pages/UserSettingsPage"

export const Route = createFileRoute("/_layout/settings")({
  component: UserSettingsPage,
  head: () => ({
    meta: [
      {
        title: "Settings - FastAPI Template",
      },
    ],
  }),
})
