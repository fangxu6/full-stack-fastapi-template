import { createFileRoute } from "@tanstack/react-router"

import { InventoryMastersPage } from "@/features/inventory/pages/InventoryMastersPage"

export const Route = createFileRoute("/_layout/inventory/masters")({
  component: InventoryMastersPage,
})
