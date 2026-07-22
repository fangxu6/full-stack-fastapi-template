import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { ArrowLeft, Home } from "lucide-react"

import { Button } from "@/components/ui/button"
import { isSafeInternalPath } from "@/shared/permissions"

export const Route = createFileRoute("/_layout/forbidden")({
  component: ForbiddenPage,
  validateSearch: (search: Record<string, unknown>) => ({
    returnTo: isSafeInternalPath(search.returnTo) ? search.returnTo : "/",
  }),
})

function ForbiddenPage() {
  const navigate = useNavigate()
  const { returnTo } = Route.useSearch()

  return (
    <div className="mx-auto flex min-h-[55vh] max-w-xl flex-col justify-center gap-5">
      <div>
        <h1 className="text-2xl font-semibold">无权访问</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          此账号尚未被授予访问该页面所需的角色或权限。
        </p>
      </div>
      <div className="flex flex-wrap gap-3">
        <Button onClick={() => navigate({ to: returnTo })} variant="outline">
          <ArrowLeft className="size-4" />
          返回上一页
        </Button>
        <Button onClick={() => navigate({ to: "/" })}>
          <Home className="size-4" />
          返回首页
        </Button>
      </div>
    </div>
  )
}
