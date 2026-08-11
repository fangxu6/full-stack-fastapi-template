import { createFileRoute, redirect } from "@tanstack/react-router"

import { isLoggedIn } from "@/platform/auth/hooks/useAuth"
import { RecoverPasswordPage } from "@/platform/auth/pages/RecoverPasswordPage"

export const Route = createFileRoute("/recover-password")({
  component: RecoverPasswordPage,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({
        to: "/",
      })
    }
  },
  head: () => ({
    meta: [
      {
        title: "Recover Password - FastAPI Template",
      },
    ],
  }),
})
