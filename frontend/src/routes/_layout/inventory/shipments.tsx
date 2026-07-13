import { createFileRoute } from "@tanstack/react-router"

import { InventoryShipmentsPage } from "@/features/inventory/pages/InventoryShipmentsPage"

export const Route = createFileRoute("/_layout/inventory/shipments")({
  component: InventoryShipmentsPage,
})
