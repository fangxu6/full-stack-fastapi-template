import { EllipsisVertical } from "lucide-react"
import { useState } from "react"

import type { ItemPublic } from "@/client"
import DeleteItemMenuItem from "@/features/items/components/DeleteItemMenuItem"
import EditItemMenuItem from "@/features/items/components/EditItemMenuItem"
import { Button } from "@/shared/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/shared/components/ui/dropdown-menu"

interface ItemActionsMenuProps {
  item: ItemPublic
}

export function ItemActionsMenu({ item }: ItemActionsMenuProps) {
  const [open, setOpen] = useState(false)

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          <EllipsisVertical />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <EditItemMenuItem item={item} onSuccess={() => setOpen(false)} />
        <DeleteItemMenuItem id={item.id} onSuccess={() => setOpen(false)} />
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
