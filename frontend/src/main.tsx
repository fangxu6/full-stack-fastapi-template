import { QueryClientProvider } from "@tanstack/react-query"
import { createRouter, RouterProvider } from "@tanstack/react-router"
import { StrictMode } from "react"
import ReactDOM from "react-dom/client"
import { ThemeProvider } from "@/shared/components/theme/ThemeProvider"
import { Toaster } from "@/shared/components/ui/sonner"
import { AntdProvider } from "./app/providers/AntdProvider"
import { queryClient } from "./app/query-client"
import { captureRateLimitResponse } from "./app/query-retry"
import { OpenAPI } from "./client"
import "./index.css"
import { routeTree } from "./routeTree.gen"

OpenAPI.BASE = import.meta.env.VITE_API_URL
OpenAPI.TOKEN = async () => {
  return localStorage.getItem("access_token") || ""
}
OpenAPI.interceptors.response.use(captureRateLimitResponse)

const router = createRouter({ routeTree })
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
      <AntdProvider>
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
          <Toaster richColors closeButton />
        </QueryClientProvider>
      </AntdProvider>
    </ThemeProvider>
  </StrictMode>,
)
