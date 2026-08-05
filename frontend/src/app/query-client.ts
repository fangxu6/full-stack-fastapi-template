import { MutationCache, QueryCache, QueryClient } from "@tanstack/react-query"
import { queryRetryDelay, shouldRetryQuery } from "@/app/query-retry"
import { ApiError } from "@/client"

export const clearAuthState = () => {
  localStorage.removeItem("access_token")
  queryClient.removeQueries({ queryKey: ["currentUser"] })
  queryClient.removeQueries({ queryKey: ["iam", "permissions"] })
}

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
    clearAuthState()
    window.location.href = "/login"
  }
}

export const queryClient = new QueryClient({
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
