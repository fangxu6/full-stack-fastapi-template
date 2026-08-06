import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query"
import { useSearch } from "@tanstack/react-router"
import {
  App,
  Button,
  Descriptions,
  Drawer,
  Empty,
  Input,
  Segmented,
  Space,
  Table,
  Tabs,
  Tag,
  Tooltip,
} from "antd"
import type { ColumnsType, TableProps } from "antd/es/table"
import { Check, Eye, FilePenLine, RotateCcw, X } from "lucide-react"
import { useEffect, useState } from "react"

import { myPermissionsQueryOptions } from "@/app/permissions"
import {
  type InventoryCorrectionDocumentProposal,
  type InventoryCorrectionOperation,
  type InventoryCorrectionRequestPublic,
  InventoryCorrectionsService,
  type InventoryCorrectionWorkItemPublic,
  type InventoryDocumentCreate,
  InventoryService,
} from "@/client"
import { DocumentEditorModal } from "@/features/inventory/components/DocumentEditorModal"
import {
  type CorrectionTab,
  correctionQueryKeys,
  createCorrectionRequest,
  getCorrectionAccess,
  getCorrectionTabs,
  recoverCorrectionWorkItem,
  resolveCorrectionTab,
  runCorrectionRequestAction,
} from "@/features/inventory/correction-workspace"
import {
  DEFAULT_PAGE_SIZE,
  PAGE_SIZE_OPTIONS,
  toOffset,
} from "@/features/inventory/pagination"

const operationLabels: Record<InventoryCorrectionOperation, string> = {
  DELETE_DOCUMENT: "删除单据",
  RESTORE_DOCUMENT: "恢复单据",
  UPDATE_DOCUMENT: "修改单据",
}

const requestStatusColors: Record<
  InventoryCorrectionRequestPublic["status"],
  string
> = {
  APPLICATION_FAILED: "red",
  APPLIED: "green",
  APPROVED: "blue",
  PENDING_REVIEW: "gold",
  REJECTED: "default",
  STALE: "orange",
  WITHDRAWN: "default",
}

const workItemStatusColors: Record<
  InventoryCorrectionWorkItemPublic["status"],
  string
> = {
  APPROVED_PENDING_APPLY: "blue",
  RUNNING: "gold",
  SUCCEEDED: "green",
  TERMINAL_FAILED: "red",
}

function formatTime(value: string | null) {
  return value
    ? new Date(value).toLocaleString("zh-CN", { timeZone: "Asia/Shanghai" })
    : "-"
}

export function InventoryCorrectionsPage() {
  const { documentId } = useSearch({ from: "/_layout/inventory/corrections" })
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<CorrectionTab>("mine")
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)
  const [reason, setReason] = useState("")
  const [operation, setOperation] =
    useState<InventoryCorrectionOperation>("UPDATE_DOCUMENT")
  const [editorOpen, setEditorOpen] = useState(false)
  const [selectedRequestId, setSelectedRequestId] = useState<number>()
  const permissionsQuery = useQuery(myPermissionsQueryOptions)
  const access = getCorrectionAccess(permissionsQuery.data?.permissions)
  const { canRecover, canRequest, canReview } = access
  const effectiveTab = resolveCorrectionTab(activeTab, access)
  const targetQuery = useQuery({
    enabled: Boolean(documentId) && canRequest,
    queryFn: () =>
      InventoryService.readInventoryDocument({ documentId: documentId ?? "" }),
    queryKey: correctionQueryKeys.target(documentId),
  })
  const target = targetQuery.data

  useEffect(() => {
    if (target?.deleted_at) {
      setOperation("RESTORE_DOCUMENT")
    } else {
      setOperation("UPDATE_DOCUMENT")
    }
  }, [target?.deleted_at])

  const queryArgs = { limit: pageSize, skip: toOffset(page, pageSize) }
  const mineQuery = useQuery({
    enabled: canRequest && effectiveTab === "mine",
    queryFn: () =>
      InventoryCorrectionsService.readMyCorrectionRequests(queryArgs),
    placeholderData: keepPreviousData,
    queryKey: correctionQueryKeys.list("mine", queryArgs),
  })
  const reviewQuery = useQuery({
    enabled: canReview && effectiveTab === "review",
    queryFn: () =>
      InventoryCorrectionsService.readCorrectionReviewQueue(queryArgs),
    placeholderData: keepPreviousData,
    queryKey: correctionQueryKeys.list("review", queryArgs),
  })
  const recoveryQuery = useQuery({
    enabled: canRecover && effectiveTab === "recovery",
    queryFn: () =>
      InventoryCorrectionsService.readCorrectionRecoveryQueue(queryArgs),
    placeholderData: keepPreviousData,
    queryKey: correctionQueryKeys.list("recovery", queryArgs),
  })
  const detailQuery = useQuery({
    enabled: selectedRequestId !== undefined,
    queryFn: () =>
      InventoryCorrectionsService.readCorrectionRequest({
        correctionRequestId: selectedRequestId ?? 0,
      }),
    queryKey: correctionQueryKeys.detail(selectedRequestId),
  })
  const invalidate = () =>
    void queryClient.invalidateQueries({
      queryKey: correctionQueryKeys.all,
    })
  const createMutation = useMutation({
    mutationFn: ({
      operation: nextOperation,
      proposal,
    }: {
      operation: InventoryCorrectionOperation
      proposal: InventoryCorrectionDocumentProposal | null
    }) => {
      return createCorrectionRequest({
        operation: nextOperation,
        proposal,
        reason,
        target,
      })
    },
    onError: (error) =>
      message.error(
        error instanceof Error ? error.message : "纠错申请提交失败。",
      ),
    onSuccess: (_, values) => {
      if (values.operation !== "UPDATE_DOCUMENT") {
        message.success("纠错申请已提交")
      }
      setReason("")
      invalidate()
    },
  })
  const requestActionMutation = useMutation({
    mutationFn: ({
      action,
      requestId,
    }: {
      action: "approve" | "reject" | "withdraw"
      requestId: number
    }) => {
      return runCorrectionRequestAction(action, requestId)
    },
    onError: () => message.error("操作失败，请刷新后重试。"),
    onSuccess: () => {
      message.success("状态已更新")
      invalidate()
      void queryClient.invalidateQueries({
        queryKey: correctionQueryKeys.detailRoot(),
      })
    },
  })
  const recoverMutation = useMutation({
    mutationFn: (workItemId: number) => recoverCorrectionWorkItem(workItemId),
    onError: () => message.error("恢复申请失败，请刷新后重试。"),
    onSuccess: () => {
      message.success("已加入自动执行队列")
      invalidate()
    },
  })

  const submitWithoutProposal = () => {
    if (!reason.trim()) {
      message.error("请填写纠错原因")
      return
    }
    createMutation.mutate({ operation, proposal: null })
  }
  const submitUpdateProposal = async (proposal: InventoryDocumentCreate) => {
    if (!reason.trim()) {
      throw new Error("请填写纠错原因")
    }
    await createMutation.mutateAsync({
      operation: "UPDATE_DOCUMENT",
      proposal,
    })
  }
  const handleTableChange: TableProps<InventoryCorrectionRequestPublic>["onChange"] =
    (pagination) => {
      const nextPageSize = pagination.pageSize ?? pageSize
      setPageSize(nextPageSize)
      setPage(nextPageSize === pageSize ? (pagination.current ?? 1) : 1)
    }
  const handleRecoveryTableChange: TableProps<InventoryCorrectionWorkItemPublic>["onChange"] =
    (pagination) => {
      const nextPageSize = pagination.pageSize ?? pageSize
      setPageSize(nextPageSize)
      setPage(nextPageSize === pageSize ? (pagination.current ?? 1) : 1)
    }
  const requestColumns: ColumnsType<InventoryCorrectionRequestPublic> = [
    { dataIndex: "id", title: "申请号", width: 90 },
    {
      dataIndex: "operation",
      render: (value: InventoryCorrectionOperation) => operationLabels[value],
      title: "操作",
      width: 120,
    },
    {
      dataIndex: "status",
      render: (value: InventoryCorrectionRequestPublic["status"]) => (
        <Tag color={requestStatusColors[value]}>{value}</Tag>
      ),
      title: "状态",
      width: 160,
    },
    {
      dataIndex: "created_at",
      render: formatTime,
      title: "提交时间",
      width: 180,
    },
    {
      key: "actions",
      render: (_, request) => (
        <Space size={0}>
          <Tooltip title="查看详情">
            <Button
              aria-label="查看详情"
              icon={<Eye size={16} />}
              onClick={() => setSelectedRequestId(request.id)}
              type="text"
            />
          </Tooltip>
          {effectiveTab === "review" && request.status === "PENDING_REVIEW" ? (
            <>
              <Tooltip title="批准">
                <Button
                  aria-label="批准"
                  icon={<Check size={16} />}
                  loading={requestActionMutation.isPending}
                  onClick={() =>
                    requestActionMutation.mutate({
                      action: "approve",
                      requestId: request.id,
                    })
                  }
                  type="text"
                />
              </Tooltip>
              <Tooltip title="拒绝">
                <Button
                  aria-label="拒绝"
                  danger
                  icon={<X size={16} />}
                  loading={requestActionMutation.isPending}
                  onClick={() =>
                    requestActionMutation.mutate({
                      action: "reject",
                      requestId: request.id,
                    })
                  }
                  type="text"
                />
              </Tooltip>
            </>
          ) : null}
          {effectiveTab === "mine" && request.status === "PENDING_REVIEW" ? (
            <Tooltip title="撤回">
              <Button
                aria-label="撤回"
                danger
                icon={<X size={16} />}
                loading={requestActionMutation.isPending}
                onClick={() =>
                  requestActionMutation.mutate({
                    action: "withdraw",
                    requestId: request.id,
                  })
                }
                type="text"
              />
            </Tooltip>
          ) : null}
        </Space>
      ),
      title: "操作",
      width: 130,
    },
  ]
  const recoveryColumns: ColumnsType<InventoryCorrectionWorkItemPublic> = [
    { dataIndex: "id", title: "工作项", width: 100 },
    {
      dataIndex: "status",
      render: (value: InventoryCorrectionWorkItemPublic["status"]) => (
        <Tag color={workItemStatusColors[value]}>{value}</Tag>
      ),
      title: "状态",
      width: 160,
    },
    {
      dataIndex: "terminal_failure_category",
      render: (value: string | null) => value ?? "-",
      title: "失败类别",
      width: 170,
    },
    {
      dataIndex: "updated_at",
      render: formatTime,
      title: "更新时间",
      width: 180,
    },
    {
      key: "actions",
      render: (_, workItem) => (
        <Tooltip title="再次自动执行">
          <Button
            aria-label="再次自动执行"
            icon={<RotateCcw size={16} />}
            loading={recoverMutation.isPending}
            onClick={() => recoverMutation.mutate(workItem.id)}
            type="text"
          />
        </Tooltip>
      ),
      title: "操作",
      width: 90,
    },
  ]
  const activeRequests =
    effectiveTab === "mine" ? mineQuery.data : reviewQuery.data
  const activeRequestLoading =
    effectiveTab === "mine" ? mineQuery.isFetching : reviewQuery.isFetching
  const tabs = getCorrectionTabs(access)

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h1 className="text-2xl font-semibold">库存异常纠错</h1>
        <p className="text-sm text-muted-foreground">
          已影响台账的单据通过申请、审核和自动执行完成更正。
        </p>
      </div>
      {canRequest && documentId ? (
        <div className="border p-4">
          {targetQuery.isLoading ? "正在加载单据..." : null}
          {target ? (
            <div className="flex flex-col gap-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="font-medium">
                    {target.document_number ?? "-"}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {target.business_date} · {target.document_type}
                  </div>
                </div>
                <Tag color={target.deleted_at ? "default" : "green"}>
                  {target.deleted_at ? "已删除" : "生效"}
                </Tag>
              </div>
              <Segmented
                onChange={(value) =>
                  setOperation(value as InventoryCorrectionOperation)
                }
                options={
                  target.deleted_at
                    ? [
                        {
                          label: operationLabels.RESTORE_DOCUMENT,
                          value: "RESTORE_DOCUMENT",
                        },
                      ]
                    : [
                        {
                          label: operationLabels.UPDATE_DOCUMENT,
                          value: "UPDATE_DOCUMENT",
                        },
                        {
                          label: operationLabels.DELETE_DOCUMENT,
                          value: "DELETE_DOCUMENT",
                        },
                      ]
                }
                value={operation}
              />
              <Input.TextArea
                maxLength={500}
                onChange={(event) => setReason(event.target.value)}
                placeholder="纠错原因"
                rows={3}
                value={reason}
              />
              <div>
                {operation === "UPDATE_DOCUMENT" ? (
                  <Button
                    icon={<FilePenLine size={16} />}
                    onClick={() => {
                      if (!reason.trim()) {
                        message.error("请填写纠错原因")
                        return
                      }
                      setEditorOpen(true)
                    }}
                    type="primary"
                  >
                    编辑纠错提案
                  </Button>
                ) : (
                  <Button
                    loading={createMutation.isPending}
                    onClick={submitWithoutProposal}
                    type="primary"
                  >
                    提交纠错申请
                  </Button>
                )}
              </div>
            </div>
          ) : targetQuery.isError ? (
            <Empty description="单据不可用于纠错" />
          ) : null}
        </div>
      ) : null}
      <Tabs
        activeKey={effectiveTab}
        items={tabs}
        onChange={(key) => {
          setActiveTab(key as CorrectionTab)
          setPage(1)
        }}
      />
      {effectiveTab === "recovery" ? (
        <Table
          columns={recoveryColumns}
          dataSource={recoveryQuery.data?.data ?? []}
          loading={recoveryQuery.isFetching}
          locale={{ emptyText: "暂无可恢复工作项" }}
          onChange={handleRecoveryTableChange}
          pagination={{
            current: page,
            pageSize,
            pageSizeOptions: PAGE_SIZE_OPTIONS,
            responsive: true,
            showQuickJumper: true,
            showSizeChanger: true,
            total: recoveryQuery.data?.count ?? 0,
          }}
          rowKey="id"
          scroll={{ x: 700 }}
        />
      ) : (
        <Table
          columns={requestColumns}
          dataSource={activeRequests?.data ?? []}
          loading={activeRequestLoading}
          locale={{ emptyText: "暂无纠错申请" }}
          onChange={handleTableChange}
          pagination={{
            current: page,
            pageSize,
            pageSizeOptions: PAGE_SIZE_OPTIONS,
            responsive: true,
            showQuickJumper: true,
            showSizeChanger: true,
            total: activeRequests?.count ?? 0,
          }}
          rowKey="id"
          scroll={{ x: 760 }}
        />
      )}
      {target ? (
        <DocumentEditorModal
          document={target}
          documentType={target.document_type}
          onClose={() => setEditorOpen(false)}
          onSubmit={submitUpdateProposal}
          open={editorOpen}
          submitLabel="提交修改申请"
        />
      ) : null}
      <Drawer
        onClose={() => setSelectedRequestId(undefined)}
        open={selectedRequestId !== undefined}
        title="纠错申请详情"
        width={760}
      >
        {detailQuery.data ? (
          <div className="flex flex-col gap-5">
            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="申请号">
                {detailQuery.data.id}
              </Descriptions.Item>
              <Descriptions.Item label="操作">
                {operationLabels[detailQuery.data.operation]}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={requestStatusColors[detailQuery.data.status]}>
                  {detailQuery.data.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="纠错原因">
                {detailQuery.data.reason}
              </Descriptions.Item>
              <Descriptions.Item label="提案哈希">
                {detailQuery.data.proposal_hash}
              </Descriptions.Item>
            </Descriptions>
            {detailQuery.data.work_item ? (
              <Table
                columns={[
                  { dataIndex: "sequence", title: "序号", width: 80 },
                  { dataIndex: "origin", title: "来源", width: 100 },
                  { dataIndex: "status", title: "状态", width: 160 },
                  {
                    dataIndex: "failure_category",
                    render: (value: string | null) => value ?? "-",
                    title: "失败类别",
                  },
                  {
                    dataIndex: "finished_at",
                    render: formatTime,
                    title: "完成时间",
                    width: 180,
                  },
                ]}
                dataSource={detailQuery.data.work_item.attempts}
                pagination={false}
                rowKey="id"
                size="small"
              />
            ) : null}
          </div>
        ) : detailQuery.isLoading ? (
          "正在加载..."
        ) : (
          <Empty description="无法读取申请详情" />
        )}
      </Drawer>
    </div>
  )
}
