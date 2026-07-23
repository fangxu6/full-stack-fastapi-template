import { createFileRoute } from "@tanstack/react-router"

import { ForbiddenPage } from "@/app/router/ForbiddenPage"
import { isSafeInternalPath } from "@/shared/permissions"

export const Route = createFileRoute("/_layout/forbidden")({
  component: ForbiddenPage,
  validateSearch: (search: Record<string, unknown>) => ({
    reason:
      search.reason === "configuration" || search.reason === "retry"
        ? search.reason
        : undefined,
    returnTo: isSafeInternalPath(search.returnTo) ? search.returnTo : "/",
  }),
})
