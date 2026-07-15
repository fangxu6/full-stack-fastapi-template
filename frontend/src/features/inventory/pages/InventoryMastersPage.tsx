import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query"
import {
  App,
  Button,
  Form,
  Input,
  Modal,
  Space,
  Switch,
  Table,
  Tabs,
  Tooltip,
} from "antd"
import type { ColumnsType, TableProps } from "antd/es/table"
import { Pencil, Plus } from "lucide-react"
import { useState } from "react"

import { InventoryService, type MasterUnitPublic } from "@/client"
import {
  readProcessingUnitsPage,
  readReceivingUnitsPage,
} from "@/features/inventory/api"
import {
  DEFAULT_PAGE_SIZE,
  PAGE_SIZE_OPTIONS,
  toOffset,
} from "@/features/inventory/pagination"

type UnitKind = "processing" | "receiving"

const unitConfig: Record<UnitKind, { label: string; queryKey: string }> = {
  processing: { label: "加工单位", queryKey: "inventory-processing-units" },
  receiving: { label: "收货单位", queryKey: "inventory-receiving-units" },
}

export function InventoryMastersPage() {
  const [activeKind, setActiveKind] = useState<UnitKind>("processing")
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)
  const [editingUnit, setEditingUnit] = useState<MasterUnitPublic>()
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm<{ name: string }>()
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const unitsQuery = useQuery({
    queryFn: () =>
      activeKind === "processing"
        ? readProcessingUnitsPage({
            limit: pageSize,
            skip: toOffset(page, pageSize),
          })
        : readReceivingUnitsPage({
            limit: pageSize,
            skip: toOffset(page, pageSize),
          }),
    queryKey: [unitConfig[activeKind].queryKey, { page, pageSize }],
    placeholderData: keepPreviousData,
  })
  const invalidate = () =>
    void queryClient.invalidateQueries({
      queryKey: [unitConfig[activeKind].queryKey],
    })
  const saveMutation = useMutation({
    mutationFn: (values: { name: string }) => {
      if (editingUnit) {
        return activeKind === "processing"
          ? InventoryService.updateProcessingUnit({
              requestBody: values,
              unitId: editingUnit.id,
            })
          : InventoryService.updateReceivingUnit({
              requestBody: values,
              unitId: editingUnit.id,
            })
      }
      return activeKind === "processing"
        ? InventoryService.createProcessingUnit({ requestBody: values })
        : InventoryService.createReceivingUnit({ requestBody: values })
    },
    onError: () => message.error("保存失败，单位名称可能已存在。"),
    onSuccess: () => {
      message.success("主数据已保存")
      setPage(1)
      invalidate()
      setModalOpen(false)
    },
  })
  const activeMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      activeKind === "processing"
        ? InventoryService.updateProcessingUnit({
            requestBody: { is_active: isActive },
            unitId: id,
          })
        : InventoryService.updateReceivingUnit({
            requestBody: { is_active: isActive },
            unitId: id,
          }),
    onError: () => message.error("状态更新失败。"),
    onSuccess: invalidate,
  })
  const columns: ColumnsType<MasterUnitPublic> = [
    { dataIndex: "name", title: "名称" },
    {
      dataIndex: "is_active",
      render: (isActive: boolean, unit) => (
        <Switch
          checked={isActive}
          checkedChildren="启用"
          loading={activeMutation.isPending}
          onChange={(nextActive) =>
            activeMutation.mutate({ id: unit.id, isActive: nextActive })
          }
          unCheckedChildren="停用"
        />
      ),
      title: "状态",
      width: 120,
    },
    {
      render: (_, unit) => (
        <Tooltip title="编辑名称">
          <Button
            aria-label="编辑名称"
            icon={<Pencil size={16} />}
            onClick={() => {
              setEditingUnit(unit)
              form.setFieldsValue({ name: unit.name })
              setModalOpen(true)
            }}
            type="text"
          />
        </Tooltip>
      ),
      title: "操作",
      width: 80,
    },
  ]

  const openCreate = () => {
    setEditingUnit(undefined)
    form.resetFields()
    setModalOpen(true)
  }
  const handleTableChange: TableProps<MasterUnitPublic>["onChange"] = (
    pagination,
  ) => {
    const nextPageSize = pagination.pageSize ?? pageSize
    setPageSize(nextPageSize)
    setPage(nextPageSize === pageSize ? (pagination.current ?? 1) : 1)
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">主数据管理</h1>
          <p className="text-sm text-muted-foreground">
            停用后不能用于新单据，历史记录保持可追溯。
          </p>
        </div>
        <Button icon={<Plus size={16} />} onClick={openCreate} type="primary">
          新建{unitConfig[activeKind].label}
        </Button>
      </div>
      <Tabs
        activeKey={activeKind}
        items={Object.entries(unitConfig).map(([key, config]) => ({
          key,
          label: config.label,
        }))}
        onChange={(key) => {
          setActiveKind(key as UnitKind)
          setPage(1)
        }}
      />
      <Table
        columns={columns}
        dataSource={unitsQuery.data?.data ?? []}
        loading={unitsQuery.isFetching}
        locale={{ emptyText: "暂无主数据" }}
        onChange={handleTableChange}
        pagination={{
          current: page,
          pageSize,
          pageSizeOptions: PAGE_SIZE_OPTIONS,
          responsive: true,
          showQuickJumper: true,
          showSizeChanger: true,
          showTotal: (total, [start, end]) => `${start}-${end} / ${total}`,
          total: unitsQuery.data?.count ?? 0,
        }}
        rowKey="id"
      />
      <Modal
        destroyOnHidden
        footer={null}
        onCancel={() => setModalOpen(false)}
        open={modalOpen}
        title={`${editingUnit ? "编辑" : "新建"}${unitConfig[activeKind].label}`}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={(values) => saveMutation.mutate(values)}
        >
          <Form.Item
            label="名称"
            name="name"
            rules={[{ required: true, whitespace: true }]}
          >
            <Input autoFocus maxLength={255} />
          </Form.Item>
          <div className="flex justify-end">
            <Space>
              <Button onClick={() => setModalOpen(false)}>取消</Button>
              <Button
                htmlType="submit"
                loading={saveMutation.isPending}
                type="primary"
              >
                保存
              </Button>
            </Space>
          </div>
        </Form>
      </Modal>
    </div>
  )
}
