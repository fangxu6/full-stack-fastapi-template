import { EllipsisVertical } from "lucide-react"
import { useState } from "react"

import type { UserPublic } from "@/client"
import useAuth from "@/platform/auth/hooks/useAuth"
import DeleteUserMenuItem from "@/platform/system/components/users/DeleteUserMenuItem"
import EditUserMenuItem from "@/platform/system/components/users/EditUserMenuItem"
import { Button } from "@/shared/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/shared/components/ui/dropdown-menu"

interface UserActionsMenuProps {
  user: UserPublic
}

export function UserActionsMenu({ user }: UserActionsMenuProps) {
  const [open, setOpen] = useState(false)
  const { user: currentUser } = useAuth()

  if (user.id === currentUser?.id) {
    return null
  }

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          <EllipsisVertical />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <EditUserMenuItem user={user} onSuccess={() => setOpen(false)} />
        <DeleteUserMenuItem id={user.id} onSuccess={() => setOpen(false)} />
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
