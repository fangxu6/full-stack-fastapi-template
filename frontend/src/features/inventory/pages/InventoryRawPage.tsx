import { InventoryDocumentsPage } from "@/features/inventory/pages/InventoryDocumentsPage"

export function InventoryRawPage() {
  return (
    <InventoryDocumentsPage
      title="坯布台账"
      types={["RAW_RECEIPT", "RAW_RETURN"]}
    />
  )
}
