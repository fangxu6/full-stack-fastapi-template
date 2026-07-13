import { createFileRoute } from "@tanstack/react-router"

import { InventoryRawPage } from "@/features/inventory/pages/InventoryRawPage"

export const Route = createFileRoute("/_layout/inventory/raw")({
  component: InventoryRawPage,
})
