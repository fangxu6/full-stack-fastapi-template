import { createFileRoute } from "@tanstack/react-router"

import { ItemsPage } from "@/features/items/pages/ItemsPage"

export const Route = createFileRoute("/_layout/items")({
  component: ItemsPage,
  head: () => ({
    meta: [
      {
        title: "Items - FastAPI Template",
      },
    ],
  }),
})
