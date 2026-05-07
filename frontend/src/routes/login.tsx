import { createFileRoute, redirect } from "@tanstack/react-router"

import { isLoggedIn } from "@/hooks/useAuth"
import { LoginPage } from "@/platform/auth/pages/LoginPage"

export const Route = createFileRoute("/login")({
  component: LoginPage,
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
        title: "Log In - FastAPI Template",
      },
    ],
  }),
})
