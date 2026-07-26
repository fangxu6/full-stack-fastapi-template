import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query"
import {
  Alert,
  App,
  Button,
  Collapse,
  Drawer,
  Form,
  Input,
  Modal,
  Popconfirm,
  Space,
  Switch,
  Table,
  Tag,
  Tooltip,
} from "antd"
import type { ColumnsType, TableProps } from "antd/es/table"
import {
  CalendarClock,
  History,
  Pencil,
  Play,
  Plus,
  RotateCcw,
  Trash2,
} from "lucide-react"
import { useState } from "react"

import {
  IamService,
  type SchedulerJobPublic,
  type SchedulerRunPublic,
  SchedulerService,
} from "@/client"
import {
  DEFAULT_PAGE_SIZE,
  PAGE_SIZE_OPTIONS,
  toOffset,
} from "@/features/inventory/pagination"

type JobFormValues = {
  classPath: string
  configText: string
  cronExpression: string
  enabled: boolean
  name: string
}

const statusColors: Record<SchedulerRunPublic["status"], string> = {
  CANCELLED: "default",
  FAILED: "red",
  QUEUED: "blue",
  RUNNING: "gold",
  SKIPPED: "default",
  SUCCEEDED: "green",
}

function formatTime(value: string | null) {
  return value ? new Date(value).toLocaleString("zh-CN") : "-"
}

function parseConfig(value: string): Record<string, unknown> {
  const parsed: unknown = JSON.parse(value)
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    throw new Error("配置必须是 JSON 对象")
  }
  return parsed as Record<string, unknown>
}

function toShanghaiIso(value: string) {
  return new Date(`${value}:00+08:00`).toISOString()
}

export function SchedulerJobsPage() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)
  const [includeDeleted, setIncludeDeleted] = useState(false)
  const [editingJob, setEditingJob] = useState<SchedulerJobPublic>()
  const [editorOpen, setEditorOpen] = useState(false)
  const [historyJob, setHistoryJob] = useState<SchedulerJobPublic>()
  const [historyPage, setHistoryPage] = useState(1)
  const [backfillJob, setBackfillJob] = useState<SchedulerJobPublic>()
  const [backfillTime, setBackfillTime] = useState("")
  const [form] = Form.useForm<JobFormValues>()
  const permissionsQuery = useQuery({
    queryKey: ["iam", "permissions"],
    queryFn: IamService.readMyPermissions,
  })
  const canManage =
    permissionsQuery.data?.permissions.includes("scheduler.jobs.manage") ??
    false
  const jobsQuery = useQuery({
    queryKey: ["scheduler", "jobs", { includeDeleted, page, pageSize }],
    queryFn: () =>
      SchedulerService.readJobs({
        includeDeleted,
        limit: pageSize,
        skip: toOffset(page, pageSize),
      }),
    placeholderData: keepPreviousData,
  })
  const classPath = Form.useWatch("classPath", form)
  const schemaQuery = useQuery({
    queryKey: ["scheduler", "schema", classPath],
    queryFn: () => SchedulerService.readTaskSchema({ classPath }),
    enabled: editorOpen && Boolean(classPath),
    retry: false,
  })
  const historyQuery = useQuery({
    queryKey: ["scheduler", "runs", historyJob?.id, historyPage, pageSize],
    queryFn: () =>
      SchedulerService.readRuns({
        jobId: historyJob?.id ?? 0,
        limit: pageSize,
        skip: toOffset(historyPage, pageSize),
      }),
    enabled: Boolean(historyJob),
    placeholderData: keepPreviousData,
  })
  const invalidate = () =>
    void queryClient.invalidateQueries({ queryKey: ["scheduler"] })
  const saveMutation = useMutation({
    mutationFn: async (values: JobFormValues) => {
      const config = parseConfig(values.configText)
      const requestBody = {
        class_path: values.classPath.trim(),
        config,
        cron_expression: values.cronExpression.trim(),
        name: values.name.trim(),
      }
      const job = editingJob
        ? await SchedulerService.updateJob({
            jobId: editingJob.id,
            requestBody,
          })
        : await SchedulerService.createJob({ requestBody })
      if (values.enabled !== job.enabled) {
        return values.enabled
          ? SchedulerService.enableJob({ jobId: job.id })
          : SchedulerService.disableJob({ jobId: job.id })
      }
      return job
    },
    onError: (error) => {
      message.error(
        error instanceof Error ? error.message : "任务保存失败，请检查配置。",
      )
    },
    onSuccess: () => {
      message.success("定时任务已保存")
      setEditorOpen(false)
      setPage(1)
      invalidate()
    },
  })
  const actionMutation = useMutation({
    mutationFn: async (
      action:
        | { kind: "delete"; job: SchedulerJobPublic }
        | { kind: "restore"; job: SchedulerJobPublic }
        | { kind: "run"; job: SchedulerJobPublic }
        | { kind: "toggle"; job: SchedulerJobPublic },
    ) => {
      if (action.kind === "delete") {
        return SchedulerService.deleteJob({ jobId: action.job.id })
      }
      if (action.kind === "restore") {
        return SchedulerService.restoreJob({ jobId: action.job.id })
      }
      if (action.kind === "run") {
        return SchedulerService.runNow({ jobId: action.job.id })
      }
      return action.job.enabled
        ? SchedulerService.disableJob({ jobId: action.job.id })
        : SchedulerService.enableJob({ jobId: action.job.id })
    },
    onError: () => message.error("操作失败，请稍后重试。"),
    onSuccess: () => invalidate(),
  })
  const backfillMutation = useMutation({
    mutationFn: (job: SchedulerJobPublic) =>
      SchedulerService.backfill({
        jobId: job.id,
        requestBody: { planned_at: toShanghaiIso(backfillTime) },
      }),
    onError: () => message.error("补发失败，请确认时间在 90 天内且命中 Cron。"),
    onSuccess: () => {
      message.success("补发任务已排队")
      setBackfillJob(undefined)
      invalidate()
    },
  })
  const openEditor = (job?: SchedulerJobPublic) => {
    setEditingJob(job)
    form.setFieldsValue({
      classPath: job?.class_path ?? "",
      configText: JSON.stringify(job?.config ?? {}, null, 2),
      cronExpression: job?.cron_expression ?? "",
      enabled: job?.enabled ?? false,
      name: job?.name ?? "",
    })
    setEditorOpen(true)
  }
  const columns: ColumnsType<SchedulerJobPublic> = [
    { dataIndex: "name", title: "任务", width: 180 },
    { dataIndex: "class_path", ellipsis: true, title: "实现类", width: 300 },
    { dataIndex: "cron_expression", title: "Cron", width: 130 },
    {
      dataIndex: "enabled",
      title: "状态",
      width: 110,
      render: (enabled: boolean, job) =>
        job.deleted_at ? (
          <Tag>已删除</Tag>
        ) : (
          <Tooltip title={enabled ? "停用任务" : "启用任务"}>
            <Switch
              checked={enabled}
              disabled={!canManage}
              loading={actionMutation.isPending}
              onChange={() => actionMutation.mutate({ kind: "toggle", job })}
            />
          </Tooltip>
        ),
    },
    {
      dataIndex: "next_run_at",
      title: "下次执行",
      width: 180,
      render: formatTime,
    },
    {
      title: "操作",
      width: 220,
      render: (_, job) => (
        <Space size={0}>
          <Tooltip title="运行历史">
            <Button
              aria-label="运行历史"
              icon={<History size={16} />}
              onClick={() => {
                setHistoryJob(job)
                setHistoryPage(1)
              }}
              type="text"
            />
          </Tooltip>
          {canManage && !job.deleted_at ? (
            <>
              <Tooltip title="编辑任务">
                <Button
                  aria-label="编辑任务"
                  icon={<Pencil size={16} />}
                  onClick={() => openEditor(job)}
                  type="text"
                />
              </Tooltip>
              <Tooltip title="立即执行">
                <Button
                  aria-label="立即执行"
                  icon={<Play size={16} />}
                  loading={actionMutation.isPending}
                  onClick={() => actionMutation.mutate({ kind: "run", job })}
                  type="text"
                />
              </Tooltip>
              <Tooltip title="补发任务">
                <Button
                  aria-label="补发任务"
                  icon={<CalendarClock size={16} />}
                  onClick={() => {
                    setBackfillJob(job)
                    setBackfillTime("")
                  }}
                  type="text"
                />
              </Tooltip>
              <Popconfirm
                description="删除后保留历史记录，可恢复为停用状态。"
                onConfirm={() => actionMutation.mutate({ kind: "delete", job })}
                title="删除这条定时任务？"
              >
                <Tooltip title="删除任务">
                  <Button
                    aria-label="删除任务"
                    danger
                    icon={<Trash2 size={16} />}
                    type="text"
                  />
                </Tooltip>
              </Popconfirm>
            </>
          ) : null}
          {canManage && job.deleted_at ? (
            <Tooltip title="恢复任务">
              <Button
                aria-label="恢复任务"
                icon={<RotateCcw size={16} />}
                loading={actionMutation.isPending}
                onClick={() => actionMutation.mutate({ kind: "restore", job })}
                type="text"
              />
            </Tooltip>
          ) : null}
        </Space>
      ),
    },
  ]
  const handleJobsTableChange: TableProps<SchedulerJobPublic>["onChange"] = (
    pagination,
  ) => {
    const nextPageSize = pagination.pageSize ?? pageSize
    setPageSize(nextPageSize)
    setPage(nextPageSize === pageSize ? (pagination.current ?? 1) : 1)
  }
  const handleHistoryTableChange: TableProps<SchedulerRunPublic>["onChange"] = (
    pagination,
  ) => {
    const nextPageSize = pagination.pageSize ?? pageSize
    setPageSize(nextPageSize)
    setHistoryPage(nextPageSize === pageSize ? (pagination.current ?? 1) : 1)
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">定时任务</h1>
          <p className="text-sm text-muted-foreground">
            Cron 按上海时区执行，运行记录保留 90 天。
          </p>
        </div>
        {canManage ? (
          <Button
            icon={<Plus size={16} />}
            onClick={() => openEditor()}
            type="primary"
          >
            新建任务
          </Button>
        ) : null}
      </div>
      <div className="flex items-center gap-2">
        <Switch
          checked={includeDeleted}
          onChange={(checked) => {
            setIncludeDeleted(checked)
            setPage(1)
          }}
        />
        <span className="text-sm text-muted-foreground">显示已删除</span>
      </div>
      {jobsQuery.isError ? (
        <Alert message="任务列表加载失败" type="error" />
      ) : null}
      <Table
        columns={columns}
        dataSource={jobsQuery.data?.data ?? []}
        loading={jobsQuery.isFetching}
        locale={{ emptyText: "暂无定时任务" }}
        onChange={handleJobsTableChange}
        pagination={{
          current: page,
          pageSize,
          pageSizeOptions: PAGE_SIZE_OPTIONS,
          responsive: true,
          showQuickJumper: true,
          showSizeChanger: true,
          showTotal: (total, [start, end]) => `${start}-${end} / ${total}`,
          total: jobsQuery.data?.count ?? 0,
        }}
        rowKey="id"
        scroll={{ x: 1100 }}
      />
      <Modal
        destroyOnHidden
        footer={null}
        onCancel={() => setEditorOpen(false)}
        open={editorOpen}
        title={editingJob ? "编辑定时任务" : "新建定时任务"}
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
            <Input maxLength={128} />
          </Form.Item>
          <Form.Item
            label="实现类"
            name="classPath"
            rules={[{ required: true, whitespace: true }]}
          >
            <Input placeholder="app.modules.inventory.scheduled_tasks.ExampleTask" />
          </Form.Item>
          <Form.Item
            label="Cron"
            name="cronExpression"
            rules={[{ required: true, whitespace: true }]}
          >
            <Input placeholder="0 8 * * *" />
          </Form.Item>
          <Form.Item
            label="JSON 配置"
            name="configText"
            rules={[
              { required: true },
              {
                validator: (_, value: string) => {
                  try {
                    parseConfig(value)
                    return Promise.resolve()
                  } catch (error) {
                    return Promise.reject(error)
                  }
                },
              },
            ]}
          >
            <Input.TextArea
              autoSize={{ minRows: 5, maxRows: 12 }}
              spellCheck={false}
            />
          </Form.Item>
          <Form.Item label="启用" name="enabled" valuePropName="checked">
            <Switch />
          </Form.Item>
          {schemaQuery.data ? (
            <Collapse
              items={[
                {
                  key: "schema",
                  label: "配置 Schema",
                  children: (
                    <pre className="overflow-auto text-xs">
                      {JSON.stringify(schemaQuery.data.json_schema, null, 2)}
                    </pre>
                  ),
                },
              ]}
            />
          ) : null}
          <div className="mt-4 flex justify-end">
            <Space>
              <Button onClick={() => setEditorOpen(false)}>取消</Button>
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
      <Modal
        destroyOnHidden
        onCancel={() => setBackfillJob(undefined)}
        onOk={() => backfillJob && backfillMutation.mutate(backfillJob)}
        okButtonProps={{
          disabled: !backfillTime,
          loading: backfillMutation.isPending,
        }}
        open={Boolean(backfillJob)}
        title="补发任务"
      >
        <Input
          max={new Date().toISOString().slice(0, 16)}
          onChange={(event) => setBackfillTime(event.target.value)}
          type="datetime-local"
          value={backfillTime}
        />
      </Modal>
      <Drawer
        destroyOnHidden
        onClose={() => setHistoryJob(undefined)}
        open={Boolean(historyJob)}
        title={historyJob ? `${historyJob.name} - 运行历史` : "运行历史"}
        width={900}
      >
        <Table
          columns={[
            {
              dataIndex: "status",
              title: "状态",
              render: (status: SchedulerRunPublic["status"]) => (
                <Tag color={statusColors[status]}>{status}</Tag>
              ),
            },
            { dataIndex: "trigger", title: "触发方式" },
            { dataIndex: "planned_at", title: "计划时间", render: formatTime },
            { dataIndex: "started_at", title: "开始时间", render: formatTime },
            { dataIndex: "finished_at", title: "结束时间", render: formatTime },
            { dataIndex: "attempt_count", title: "尝试" },
            { dataIndex: "error_summary", ellipsis: true, title: "结果" },
          ]}
          dataSource={historyQuery.data?.data ?? []}
          loading={historyQuery.isFetching}
          locale={{ emptyText: "暂无运行记录" }}
          onChange={handleHistoryTableChange}
          pagination={{
            current: historyPage,
            pageSize,
            pageSizeOptions: PAGE_SIZE_OPTIONS,
            showSizeChanger: true,
            total: historyQuery.data?.count ?? 0,
          }}
          rowKey="id"
          scroll={{ x: 900 }}
          size="small"
        />
      </Drawer>
    </div>
  )
}
