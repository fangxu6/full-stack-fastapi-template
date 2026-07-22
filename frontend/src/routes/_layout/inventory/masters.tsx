import { createFileRoute } from "@tanstack/react-router"
import { requirePermission } from "@/app/router/guards"
import { InventoryMastersPage } from "@/features/inventory/pages/InventoryMastersPage"

export const Route = createFileRoute("/_layout/inventory/masters")({
  component: InventoryMastersPage,
  beforeLoad: requirePermission("inventory.masters.read"),
})
