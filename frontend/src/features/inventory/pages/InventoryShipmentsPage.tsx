import { InventoryDocumentsPage } from "@/features/inventory/pages/InventoryDocumentsPage"

export function InventoryShipmentsPage() {
  return (
    <InventoryDocumentsPage
      ledgerKind="FINISHED"
      title="成品出货"
      types={["FINISHED_SHIPMENT"]}
    />
  )
}
