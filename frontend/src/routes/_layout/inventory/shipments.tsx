import { createFileRoute } from "@tanstack/react-router"
import { requirePermission } from "@/app/router/guards"
import { InventoryShipmentsPage } from "@/features/inventory/pages/InventoryShipmentsPage"

export const Route = createFileRoute("/_layout/inventory/shipments")({
  component: InventoryShipmentsPage,
  beforeLoad: requirePermission("inventory.documents.read"),
})
