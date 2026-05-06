import { useSuspenseQuery } from "@tanstack/react-query"
import { Search } from "lucide-react"
import { Suspense } from "react"

import { ItemsService } from "@/client"
import AddItemDialog from "@/features/items/components/AddItemDialog"
import { itemColumns } from "@/features/items/components/item-columns"
import { ItemsTableSkeleton } from "@/shared/components/feedback"
import { DataTable } from "@/shared/components/table"

function getItemsQueryOptions() {
  return {
    queryFn: () => ItemsService.readItems({ skip: 0, limit: 100 }),
    queryKey: ["items"],
  }
}

function ItemsTableContent() {
  const { data: items } = useSuspenseQuery(getItemsQueryOptions())

  if (items.data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <div className="mb-4 rounded-full bg-muted p-4">
          <Search className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">You don't have any items yet</h3>
        <p className="text-muted-foreground">Add a new item to get started</p>
      </div>
    )
  }

  return <DataTable columns={itemColumns} data={items.data} />
}

function ItemsTable() {
  return (
    <Suspense fallback={<ItemsTableSkeleton />}>
      <ItemsTableContent />
    </Suspense>
  )
}

export function ItemsPage() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Items</h1>
          <p className="text-muted-foreground">Create and manage your items</p>
        </div>
        <AddItemDialog />
      </div>
      <ItemsTable />
    </div>
  )
}
