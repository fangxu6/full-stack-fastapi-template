import { useSuspenseQuery } from "@tanstack/react-query"
import { Suspense } from "react"

import { type UserPublic, UsersService } from "@/client"
import useAuth from "@/hooks/useAuth"
import AddUserDialog from "@/platform/system/components/users/AddUserDialog"
import {
  userColumns,
  type UserTableData,
} from "@/platform/system/components/users/user-columns"
import { UsersTableSkeleton } from "@/shared/components/feedback"
import { DataTable } from "@/shared/components/table"

function getUsersQueryOptions() {
  return {
    queryFn: () => UsersService.readUsers({ skip: 0, limit: 100 }),
    queryKey: ["users"],
  }
}

function UsersTableContent() {
  const { user: currentUser } = useAuth()
  const { data: users } = useSuspenseQuery(getUsersQueryOptions())

  const tableData: UserTableData[] = users.data.map((user: UserPublic) => ({
    ...user,
    isCurrentUser: currentUser?.id === user.id,
  }))

  return <DataTable columns={userColumns} data={tableData} />
}

function UsersTable() {
  return (
    <Suspense fallback={<UsersTableSkeleton />}>
      <UsersTableContent />
    </Suspense>
  )
}

export function AdminUsersPage() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Users</h1>
          <p className="text-muted-foreground">
            Manage user accounts and permissions
          </p>
        </div>
        <AddUserDialog />
      </div>
      <UsersTable />
    </div>
  )
}
