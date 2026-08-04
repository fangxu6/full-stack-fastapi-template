import { createFileRoute } from "@tanstack/react-router"
import { z } from "zod"

import { requirePermission } from "@/app/router/guards"
import { InventoryCorrectionsPage } from "@/features/inventory/pages/InventoryCorrectionsPage"

const searchSchema = z.object({
  documentId: z.string().uuid().optional(),
})

export const Route = createFileRoute("/_layout/inventory/corrections")({
  beforeLoad: requirePermission("inventory.documents.read"),
  component: InventoryCorrectionsPage,
  validateSearch: searchSchema,
})
