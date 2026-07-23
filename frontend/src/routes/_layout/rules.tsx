import { createFileRoute } from "@tanstack/react-router"
import { z } from "zod"

import { RulesPage } from "@/platform/docs"

const searchSchema = z.object({
  slug: z.string().optional(),
})

export const Route = createFileRoute("/_layout/rules")({
  component: RulesPage,
  validateSearch: searchSchema,
  head: () => ({
    meta: [
      {
        title: "Rules - FastAPI Template",
      },
    ],
  }),
})
