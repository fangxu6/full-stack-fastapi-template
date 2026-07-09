import { createFileRoute } from "@tanstack/react-router"
import { z } from "zod"

import { RulesPage } from "@/platform/docs"

const searchSchema = z.object({
  slug: z.string().optional(),
})

export const Route = createFileRoute("/_layout/rules")({
  component: RulesRoute,
  validateSearch: searchSchema,
  head: () => ({
    meta: [
      {
        title: "Rules - FastAPI Template",
      },
    ],
  }),
})

function RulesRoute() {
  const { slug } = Route.useSearch()
  return <RulesPage slug={slug} />
}
