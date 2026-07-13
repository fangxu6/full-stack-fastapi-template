import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { App, Button, Popconfirm, Space, Table, Tabs, Tag, Tooltip } from "antd"
import type { ColumnsType } from "antd/es/table"
import { Edit3, Plus, RotateCcw, Trash2 } from "lucide-react"
import { useState } from "react"

import {
  type InventoryDocumentCreate,
  type InventoryDocumentPublic,
  InventoryService,
} from "@/client"
import { DocumentEditorModal } from "@/features/inventory/components/DocumentEditorModal"

type DocumentPageProps = {
  types: InventoryDocumentCreate["document_type"][]
  title: string
}

const documentLabels: Record<InventoryDocumentCreate["document_type"], string> =
  {
    FINISHED_RECEIPT: "成品入库",
    FINISHED_SHIPMENT: "成品出货",
    RAW_RECEIPT: "来料入库",
    RAW_RETURN: "坯布退走",
  }

export function InventoryDocumentsPage({ types, title }: DocumentPageProps) {
  const [activeType, setActiveType] = useState(types[0])
  const [editingDocument, setEditingDocument] =
    useState<InventoryDocumentPublic>()
  const [isEditorOpen, setEditorOpen] = useState(false)
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const documentsQuery = useQuery({
    queryFn: () =>
      InventoryService.readInventoryDocuments({
        documentType: activeType,
        includeDeleted: true,
      }),
    queryKey: ["inventory", "documents", activeType],
  })
  const invalidate = () =>
    void queryClient.invalidateQueries({ queryKey: ["inventory"] })
  const deleteMutation = useMutation({
    mutationFn: (documentId: string) =>
      InventoryService.deleteInventoryDocument({ documentId }),
    onError: () => message.error("删除失败，库存不足或数据已变更。"),
    onSuccess: () => {
      message.success("单据已软删除")
      invalidate()
    },
  })
  const restoreMutation = useMutation({
    mutationFn: (documentId: string) =>
      InventoryService.restoreInventoryDocument({ documentId }),
    onError: () => message.error("恢复失败，恢复后库存不能为负数。"),
    onSuccess: () => {
      message.success("单据已恢复")
      invalidate()
    },
  })

  const openEditor = (document?: InventoryDocumentPublic) => {
    setEditingDocument(document)
    setEditorOpen(true)
  }
  const columns: ColumnsType<InventoryDocumentPublic> = [
    { dataIndex: "business_date", title: "日期", width: 116 },
    { dataIndex: "document_number", title: "单号", width: 160 },
    {
      dataIndex: "lines",
      render: (lines: InventoryDocumentPublic["lines"]) =>
        `${lines.length} 条明细`,
      title: "明细",
      width: 90,
    },
    {
      dataIndex: "remarks",
      ellipsis: true,
      title: "备注",
    },
    {
      dataIndex: "deleted_at",
      render: (deletedAt: string | null) =>
        deletedAt ? (
          <Tag color="default">已删除</Tag>
        ) : (
          <Tag color="green">生效</Tag>
        ),
      title: "状态",
      width: 90,
    },
    {
      key: "actions",
      render: (_, document) =>
        document.deleted_at ? (
          <Tooltip title="恢复单据">
            <Button
              aria-label="恢复单据"
              icon={<RotateCcw size={16} />}
              loading={restoreMutation.isPending}
              onClick={() => restoreMutation.mutate(document.id)}
              type="text"
            />
          </Tooltip>
        ) : (
          <Space size={0}>
            <Tooltip title="编辑单据">
              <Button
                aria-label="编辑单据"
                icon={<Edit3 size={16} />}
                onClick={() => openEditor(document)}
                type="text"
              />
            </Tooltip>
            <Popconfirm
              description="删除后将从库存余额中排除，可随时恢复。"
              onConfirm={() => deleteMutation.mutate(document.id)}
              title="删除这张单据？"
            >
              <Tooltip title="删除单据">
                <Button
                  aria-label="删除单据"
                  danger
                  icon={<Trash2 size={16} />}
                  type="text"
                />
              </Tooltip>
            </Popconfirm>
          </Space>
        ),
      title: "操作",
      width: 110,
    },
  ]

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">{title}</h1>
          <p className="text-sm text-muted-foreground">
            单据保存后即时重算对应库存余额。
          </p>
        </div>
        <Button
          icon={<Plus size={16} />}
          onClick={() => openEditor()}
          type="primary"
        >
          新建{documentLabels[activeType]}
        </Button>
      </div>
      <Tabs
        activeKey={activeType}
        items={types.map((type) => ({
          key: type,
          label: documentLabels[type],
        }))}
        onChange={(nextType) => setActiveType(nextType as typeof activeType)}
      />
      <Table
        columns={columns}
        dataSource={documentsQuery.data?.data ?? []}
        loading={documentsQuery.isLoading}
        locale={{ emptyText: "暂无单据" }}
        pagination={{ pageSize: 20, showSizeChanger: false }}
        rowKey="id"
        scroll={{ x: 680 }}
        size="middle"
      />
      <DocumentEditorModal
        document={editingDocument}
        documentType={activeType}
        key={editingDocument?.id ?? activeType}
        onClose={() => setEditorOpen(false)}
        open={isEditorOpen}
      />
    </div>
  )
}
