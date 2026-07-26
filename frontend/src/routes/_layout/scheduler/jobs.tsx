import { createFileRoute } from "@tanstack/react-router"

import { requirePermission } from "@/app/router/guards"
import { SchedulerJobsPage } from "@/features/scheduler/pages/SchedulerJobsPage"

export const Route = createFileRoute("/_layout/scheduler/jobs")({
  beforeLoad: requirePermission("scheduler.jobs.read"),
  component: SchedulerJobsPage,
})
