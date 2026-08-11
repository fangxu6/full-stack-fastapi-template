import { createFileRoute, redirect } from "@tanstack/react-router"
import { isLoggedIn } from "@/platform/auth/hooks/useAuth"
import { SignUpPage } from "@/platform/auth/pages/SignUpPage"

export const Route = createFileRoute("/signup")({
  component: SignUpPage,
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
        title: "Sign Up - FastAPI Template",
      },
    ],
  }),
})
