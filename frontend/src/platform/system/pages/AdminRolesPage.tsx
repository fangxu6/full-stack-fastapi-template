import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Button, Checkbox, Input, Modal, Space, Switch, Table, Tag } from "antd"
import { Pencil, Plus, Trash2 } from "lucide-react"
import { useMemo, useState } from "react"

import { IamService, type PermissionPublic, type RolePublic } from "@/client"

type RoleDraft = {
  code: string
  name: string
  description: string
  permissionCodes: string[]
}

const governancePrefixes = ["system.users.", "iam.roles."]
const prerequisites: Record<string, string[]> = {
  "inventory.masters.manage": ["inventory.masters.read"],
  "inventory.documents.manage": ["inventory.documents.read"],
}

function isGovernancePermission(code: string) {
  return governancePrefixes.some((prefix) => code.startsWith(prefix))
}

function withPrerequisites(permissionCodes: string[]) {
  return Array.from(
    new Set(
      permissionCodes.flatMap((code) => [code, ...(prerequisites[code] ?? [])]),
    ),
  )
}

export function AdminRolesPage() {
  const queryClient = useQueryClient()
  const rolesQuery = useQuery({
    queryKey: ["iam", "roles"],
    queryFn: IamService.readRoles,
  })
  const catalogQuery = useQuery({
    queryKey: ["iam", "catalog"],
    queryFn: IamService.readPermissionCatalog,
  })
  const [editingRole, setEditingRole] = useState<RolePublic>()
  const [draft, setDraft] = useState<RoleDraft>()

  const invalidate = () =>
    void queryClient.invalidateQueries({ queryKey: ["iam"] })
  const saveMutation = useMutation({
    mutationFn: async (nextDraft: RoleDraft) => {
      const permissionCodes = withPrerequisites(nextDraft.permissionCodes)
      if (editingRole) {
        await IamService.updateRole({
          roleId: editingRole.id,
          requestBody: {
            name: nextDraft.name,
            description: nextDraft.description || null,
          },
        })
        return IamService.replaceRolePermissions({
          roleId: editingRole.id,
          requestBody: { permission_codes: permissionCodes },
        })
      }
      return IamService.createRole({
        requestBody: {
          code: nextDraft.code,
          name: nextDraft.name,
          description: nextDraft.description || null,
          permission_codes: permissionCodes,
        },
      })
    },
    onSuccess: () => {
      setDraft(undefined)
      setEditingRole(undefined)
      invalidate()
    },
  })
  const stateMutation = useMutation({
    mutationFn: ({ roleId, isActive }: { roleId: number; isActive: boolean }) =>
      IamService.updateRole({ roleId, requestBody: { is_active: isActive } }),
    onSuccess: invalidate,
  })
  const deleteMutation = useMutation({
    mutationFn: (roleId: number) => IamService.deleteRole({ roleId }),
    onSuccess: invalidate,
  })
  const catalogByGroup = useMemo(() => {
    const groups = new Map<string, PermissionPublic[]>()
    for (const permission of catalogQuery.data?.data ?? []) {
      const current = groups.get(permission.group_name) ?? []
      current.push(permission)
      groups.set(permission.group_name, current)
    }
    return groups
  }, [catalogQuery.data])

  const openCreate = () => {
    setEditingRole(undefined)
    setDraft({ code: "", name: "", description: "", permissionCodes: [] })
  }
  const openEdit = (role: RolePublic) => {
    setEditingRole(role)
    setDraft({
      code: role.code,
      name: role.name,
      description: role.description ?? "",
      permissionCodes: role.permission_codes,
    })
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">角色管理</h1>
          <p className="text-sm text-muted-foreground">
            角色停用后会立即停止贡献权限，现有分配会被保留。
          </p>
        </div>
        <Button icon={<Plus size={16} />} onClick={openCreate} type="primary">
          新建自定义角色
        </Button>
      </div>
      <Table<RolePublic>
        columns={[
          { dataIndex: "name", title: "角色" },
          { dataIndex: "code", title: "代码" },
          {
            dataIndex: "permission_codes",
            title: "权限",
            render: (codes: string[]) => <span>{codes.length} 项</span>,
          },
          {
            dataIndex: "is_builtin",
            title: "类型",
            render: (builtin: boolean) => (
              <Tag color={builtin ? "blue" : "default"}>
                {builtin ? "内置" : "自定义"}
              </Tag>
            ),
          },
          {
            dataIndex: "is_active",
            title: "状态",
            render: (active: boolean, role) =>
              role.is_builtin ? (
                <Tag color="green">启用</Tag>
              ) : (
                <Switch
                  checked={active}
                  loading={stateMutation.isPending}
                  onChange={(isActive) =>
                    stateMutation.mutate({ roleId: role.id, isActive })
                  }
                />
              ),
          },
          {
            title: "操作",
            render: (_, role) =>
              role.is_builtin ? (
                <span className="text-muted-foreground">仅查看</span>
              ) : (
                <Space>
                  <Button
                    aria-label="编辑角色"
                    icon={<Pencil size={16} />}
                    onClick={() => openEdit(role)}
                    type="text"
                  />
                  <Button
                    aria-label="删除角色"
                    danger
                    disabled={role.is_active}
                    icon={<Trash2 size={16} />}
                    loading={deleteMutation.isPending}
                    onClick={() => deleteMutation.mutate(role.id)}
                    type="text"
                  />
                </Space>
              ),
          },
        ]}
        dataSource={rolesQuery.data?.data ?? []}
        loading={rolesQuery.isLoading}
        pagination={false}
        rowKey="id"
      />
      <Modal
        destroyOnHidden
        footer={null}
        onCancel={() => {
          setDraft(undefined)
          setEditingRole(undefined)
        }}
        open={Boolean(draft)}
        title={editingRole ? `编辑角色: ${editingRole.name}` : "新建自定义角色"}
      >
        {draft ? (
          <div className="flex flex-col gap-4">
            <Input
              disabled={Boolean(editingRole)}
              onChange={(event) =>
                setDraft({ ...draft, code: event.target.value })
              }
              placeholder="代码，例如 inventory_auditor"
              value={draft.code}
            />
            <Input
              onChange={(event) =>
                setDraft({ ...draft, name: event.target.value })
              }
              placeholder="角色名称"
              value={draft.name}
            />
            <Input.TextArea
              onChange={(event) =>
                setDraft({ ...draft, description: event.target.value })
              }
              placeholder="角色说明"
              value={draft.description}
            />
            {Array.from(catalogByGroup.entries()).map(
              ([group, permissions]) => (
                <div key={group}>
                  <div className="mb-2 text-sm font-medium">{group}</div>
                  <div className="flex flex-col gap-2">
                    {permissions.map((permission) => {
                      const disabled = isGovernancePermission(permission.code)
                      return (
                        <Checkbox
                          checked={draft.permissionCodes.includes(
                            permission.code,
                          )}
                          disabled={disabled}
                          key={permission.id}
                          onChange={(event) =>
                            setDraft({
                              ...draft,
                              permissionCodes: event.target.checked
                                ? withPrerequisites([
                                    ...draft.permissionCodes,
                                    permission.code,
                                  ])
                                : draft.permissionCodes.filter(
                                    (code) => code !== permission.code,
                                  ),
                            })
                          }
                        >
                          {permission.label}
                          {disabled
                            ? " (Built-in Platform Administrator only)"
                            : ""}
                        </Checkbox>
                      )
                    })}
                  </div>
                </div>
              ),
            )}
            <div className="flex justify-end">
              <Space>
                <Button
                  onClick={() => {
                    setDraft(undefined)
                    setEditingRole(undefined)
                  }}
                >
                  取消
                </Button>
                <Button
                  disabled={!draft.name || (!editingRole && !draft.code)}
                  loading={saveMutation.isPending}
                  onClick={() => saveMutation.mutate(draft)}
                  type="primary"
                >
                  保存
                </Button>
              </Space>
            </div>
          </div>
        ) : null}
      </Modal>
    </div>
  )
}
