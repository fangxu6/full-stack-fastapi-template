import { useNavigate, useSearch } from "@tanstack/react-router"
import { ArrowLeft, Home, RefreshCw, ShieldAlert, WifiOff } from "lucide-react"

import { Button } from "@/shared/components/ui/button"

const feedbackByReason = {
  configuration: {
    description: "当前账号的权限配置无法完成校验，请联系系统管理员后重试。",
    icon: ShieldAlert,
    retryLabel: "重新校验",
    title: "权限配置异常",
  },
  retry: {
    description: "服务暂时不可用或网络连接中断，请稍后重试。",
    icon: WifiOff,
    retryLabel: "重试",
    title: "暂时无法校验权限",
  },
} as const

type FeedbackReason = keyof typeof feedbackByReason

function isFeedbackReason(value: unknown): value is FeedbackReason {
  return value === "configuration" || value === "retry"
}

export function ForbiddenPage() {
  const navigate = useNavigate()
  const { reason, returnTo } = useSearch({ from: "/_layout/forbidden" })
  const feedback = isFeedbackReason(reason)
    ? feedbackByReason[reason]
    : undefined
  const Icon = feedback?.icon

  return (
    <div className="mx-auto flex min-h-[55vh] max-w-xl flex-col justify-center gap-5">
      <div className={feedback ? "flex items-start gap-3" : undefined}>
        {Icon ? (
          <Icon
            aria-hidden="true"
            className="mt-1 size-6 text-muted-foreground"
          />
        ) : null}
        <div>
          <h1 className="text-2xl font-semibold">
            {feedback?.title ?? "无权访问"}
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {feedback?.description ??
              "此账号尚未被授予访问该页面所需的角色或权限。"}
          </p>
        </div>
      </div>
      <div className="flex flex-wrap gap-3">
        <Button
          onClick={() => navigate({ to: returnTo })}
          variant={feedback ? "default" : "outline"}
        >
          {feedback ? (
            <RefreshCw className="size-4" />
          ) : (
            <ArrowLeft className="size-4" />
          )}
          {feedback?.retryLabel ?? "返回上一页"}
        </Button>
        <Button
          onClick={() => navigate({ to: "/" })}
          variant={feedback ? "outline" : "default"}
        >
          <Home className="size-4" />
          返回首页
        </Button>
      </div>
    </div>
  )
}
