import { createFileRoute } from "@tanstack/react-router"

import { InventoryBalancesPage } from "@/features/inventory/pages/InventoryBalancesPage"

export const Route = createFileRoute("/_layout/inventory/balances")({
  component: InventoryBalancesPage,
})
