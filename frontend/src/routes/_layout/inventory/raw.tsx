import { createFileRoute } from "@tanstack/react-router"
import { requirePermission } from "@/app/router/guards"
import { InventoryRawPage } from "@/features/inventory/pages/InventoryRawPage"

export const Route = createFileRoute("/_layout/inventory/raw")({
  component: InventoryRawPage,
  beforeLoad: requirePermission("inventory.documents.read"),
})
