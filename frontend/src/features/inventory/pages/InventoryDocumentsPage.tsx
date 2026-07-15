import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query"
import {
  App,
  Button,
  DatePicker,
  Form,
  Input,
  Popconfirm,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Tooltip,
} from "antd"
import type { ColumnsType, TableProps } from "antd/es/table"
import type { Dayjs } from "dayjs"
import { Edit3, Plus, RotateCcw, Trash2 } from "lucide-react"
import { useState } from "react"

import {
  type InventoryDocumentCreate,
  type InventoryDocumentPublic,
  InventoryService,
} from "@/client"
import {
  readInventoryDocumentsPage,
  readProcessingUnitsPage,
  readReceivingUnitsPage,
} from "@/features/inventory/api"
import { DocumentEditorModal } from "@/features/inventory/components/DocumentEditorModal"
import {
  DEFAULT_PAGE_SIZE,
  PAGE_SIZE_OPTIONS,
  toOffset,
} from "@/features/inventory/pagination"

type DocumentPageProps = {
  types: InventoryDocumentCreate["document_type"][]
  title: string
}

type DocumentFilters = {
  business_dates?: [Dayjs, Dayjs]
  document_number?: string
  processing_unit_id?: string
  receiving_unit_id?: string
}

const documentLabels: Record<InventoryDocumentCreate["document_type"], string> =
  {
    FINISHED_RECEIPT: "成品入库",
    FINISHED_SHIPMENT: "成品出货",
    RAW_RECEIPT: "来料入库",
    RAW_RETURN: "坯布退走",
  }

const MAX_VISIBLE_LINES = 3

function compactValue(value: string | null | undefined) {
  return value?.trim() || "-"
}

function renderLineDetails(
  line: InventoryDocumentPublic["lines"][number],
  documentType: InventoryDocumentPublic["document_type"],
) {
  const fields =
    documentType === "FINISHED_SHIPMENT"
      ? [
          ["颜色", compactValue(line.color_code)],
          ["缸号", compactValue(line.dye_lot_no)],
          ["匹数", line.quantity_rolls],
          ["米数", compactValue(line.quantity_meters)],
        ]
      : [
          ["品号", compactValue(line.item_code)],
          ["含毛量", compactValue(line.wool_content)],
          ["匹数", line.quantity_rolls],
        ]

  return (
    <div className="flex min-w-0 flex-col gap-0.5" key={line.id}>
      <div className="truncate font-medium">{compactValue(line.item_name)}</div>
      <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
        {fields.map(([label, value]) => (
          <span key={label}>
            {label}: {value}
          </span>
        ))}
      </div>
    </div>
  )
}

function renderLinesSummary(
  document: InventoryDocumentPublic,
  lines: InventoryDocumentPublic["lines"],
) {
  const visibleLines = lines.slice(0, MAX_VISIBLE_LINES)
  const remainingCount = lines.length - visibleLines.length

  return (
    <div className="flex max-w-[440px] flex-col gap-2">
      {visibleLines.map((line) =>
        renderLineDetails(line, document.document_type),
      )}
      {remainingCount > 0 ? (
        <div className="text-xs text-muted-foreground">
          另 {remainingCount} 条明细
        </div>
      ) : null}
    </div>
  )
}

export function InventoryDocumentsPage({ types, title }: DocumentPageProps) {
  const [activeType, setActiveType] = useState(types[0])
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)
  const [editingDocument, setEditingDocument] =
    useState<InventoryDocumentPublic>()
  const [isEditorOpen, setEditorOpen] = useState(false)
  const [filters, setFilters] = useState<DocumentFilters>({})
  const [filterForm] = Form.useForm<DocumentFilters>()
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const documentsQuery = useQuery({
    queryFn: () =>
      readInventoryDocumentsPage({
        businessDateFrom: filters.business_dates?.[0]?.format("YYYY-MM-DD"),
        businessDateTo: filters.business_dates?.[1]?.format("YYYY-MM-DD"),
        documentType: activeType,
        documentNumber: filters.document_number?.trim() || undefined,
        includeDeleted: true,
        limit: pageSize,
        processingUnitId: filters.processing_unit_id,
        receivingUnitId: filters.receiving_unit_id,
        skip: toOffset(page, pageSize),
      }),
    queryKey: [
      "inventory",
      "documents",
      activeType,
      filters,
      { page, pageSize },
    ],
    placeholderData: keepPreviousData,
  })
  const processingUnitsQuery = useQuery({
    queryFn: () => readProcessingUnitsPage({ limit: 100, skip: 0 }),
    queryKey: ["inventory-processing-units"],
  })
  const receivingUnitsQuery = useQuery({
    enabled: activeType === "FINISHED_SHIPMENT",
    queryFn: () => readReceivingUnitsPage({ limit: 100, skip: 0 }),
    queryKey: ["inventory-receiving-units"],
  })
  const invalidate = () =>
    void queryClient.invalidateQueries({ queryKey: ["inventory"] })
  const deleteMutation = useMutation({
    mutationFn: (documentId: string) =>
      InventoryService.deleteInventoryDocument({ documentId }),
    onError: () => message.error("删除失败，库存不足或数据已变更。"),
    onSuccess: () => {
      message.success("单据已软删除")
      setPage(1)
      invalidate()
    },
  })
  const restoreMutation = useMutation({
    mutationFn: (documentId: string) =>
      InventoryService.restoreInventoryDocument({ documentId }),
    onError: () => message.error("恢复失败，恢复后库存不能为负数。"),
    onSuccess: () => {
      message.success("单据已恢复")
      setPage(1)
      invalidate()
    },
  })

  const openEditor = (document?: InventoryDocumentPublic) => {
    setEditingDocument(document)
    setEditorOpen(true)
  }
  const handleTableChange: TableProps<InventoryDocumentPublic>["onChange"] = (
    pagination,
  ) => {
    const nextPageSize = pagination.pageSize ?? pageSize
    setPageSize(nextPageSize)
    setPage(nextPageSize === pageSize ? (pagination.current ?? 1) : 1)
  }
  const columns: ColumnsType<InventoryDocumentPublic> = [
    { dataIndex: "business_date", title: "日期", width: 116 },
    { dataIndex: "document_number", title: "单号", width: 160 },
    {
      dataIndex: "lines",
      render: (lines: InventoryDocumentPublic["lines"], document) =>
        renderLinesSummary(document, lines),
      title: "明细",
      width: 420,
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
        onChange={(nextType) => {
          setActiveType(nextType as typeof activeType)
          setPage(1)
        }}
      />
      <Form
        form={filterForm}
        layout="inline"
        onValuesChange={(_, values: DocumentFilters) => {
          setFilters(values)
          setPage(1)
        }}
      >
        <Form.Item label="日期" name="business_dates">
          <DatePicker.RangePicker />
        </Form.Item>
        <Form.Item label="加工单位" name="processing_unit_id">
          <Select
            allowClear
            className="min-w-40"
            loading={processingUnitsQuery.isLoading}
            options={(processingUnitsQuery.data?.data ?? []).map((unit) => ({
              label: unit.name,
              value: unit.id,
            }))}
            showSearch
          />
        </Form.Item>
        {activeType === "FINISHED_SHIPMENT" ? (
          <Form.Item label="收货单位" name="receiving_unit_id">
            <Select
              allowClear
              className="min-w-40"
              loading={receivingUnitsQuery.isLoading}
              options={(receivingUnitsQuery.data?.data ?? []).map((unit) => ({
                label: unit.name,
                value: unit.id,
              }))}
              showSearch
            />
          </Form.Item>
        ) : null}
        <Form.Item label="单号" name="document_number">
          <Input allowClear placeholder="输入单号" />
        </Form.Item>
        <Button
          onClick={() => {
            filterForm.resetFields()
            setFilters({})
            setPage(1)
          }}
        >
          清除筛选
        </Button>
      </Form>
      <Table
        columns={columns}
        dataSource={documentsQuery.data?.data ?? []}
        loading={documentsQuery.isFetching}
        locale={{ emptyText: "暂无单据" }}
        onChange={handleTableChange}
        pagination={{
          current: page,
          pageSize,
          pageSizeOptions: PAGE_SIZE_OPTIONS,
          responsive: true,
          showQuickJumper: true,
          showSizeChanger: true,
          showTotal: (total, [start, end]) => `${start}-${end} / ${total}`,
          total: documentsQuery.data?.count ?? 0,
        }}
        rowKey="id"
        scroll={{ x: 1020 }}
        size="middle"
      />
      <DocumentEditorModal
        document={editingDocument}
        documentType={activeType}
        key={editingDocument?.id ?? activeType}
        onClose={() => setEditorOpen(false)}
        onSaved={() => setPage(1)}
        open={isEditorOpen}
      />
    </div>
  )
}
