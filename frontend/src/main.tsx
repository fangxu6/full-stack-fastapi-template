import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query"
import { createRouter, RouterProvider } from "@tanstack/react-router"
import { StrictMode } from "react"
import ReactDOM from "react-dom/client"
import { AntdProvider } from "./app/providers/AntdProvider"
import {
  captureRateLimitResponse,
  queryRetryDelay,
  shouldRetryQuery,
} from "./app/query-retry"
import { ApiError, OpenAPI } from "./client"
import { ThemeProvider } from "./components/theme-provider"
import { Toaster } from "./components/ui/sonner"
import "./index.css"
import { routeTree } from "./routeTree.gen"

OpenAPI.BASE = import.meta.env.VITE_API_URL
OpenAPI.TOKEN = async () => {
  return localStorage.getItem("access_token") || ""
}
OpenAPI.interceptors.response.use(captureRateLimitResponse)

const handleApiError = (error: Error) => {
  const isInvalidSession =
    error instanceof ApiError &&
    (error.status === 401 ||
      (error.status === 403 &&
        error.body &&
        typeof error.body === "object" &&
        "detail" in error.body &&
        error.body.detail === "Could not validate credentials"))
  if (isInvalidSession) {
    localStorage.removeItem("access_token")
    window.location.href = "/login"
  }
}
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: shouldRetryQuery,
      retryDelay: queryRetryDelay,
    },
  },
  queryCache: new QueryCache({
    onError: handleApiError,
  }),
  mutationCache: new MutationCache({
    onError: handleApiError,
  }),
})

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
