import { createFileRoute } from "@tanstack/react-router"
import { requirePermission } from "@/app/router/guards"
import { InventoryBalancesPage } from "@/features/inventory/pages/InventoryBalancesPage"

export const Route = createFileRoute("/_layout/inventory/balances")({
  component: InventoryBalancesPage,
  beforeLoad: requirePermission("inventory.balances.read"),
})
