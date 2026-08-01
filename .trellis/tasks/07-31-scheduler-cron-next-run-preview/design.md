# 定时任务 Cron 后续时点预览设计

## Scope And Decisions

本任务实现一个只读的 Cron 解释能力，而不是任务状态或运行创建能力。

- D-001：请求直接携带 Cron，因此保存前和保存后的编辑值使用同一端点。
- D-002：服务端取当前 UTC 时间为基准，固定计算 5 个严格后续时点；公开 API 不提供基准时间
  或数量参数。
- D-003：编辑表单在 Cron 输入变化后自动刷新预览。
- D-004：输入停止变化 300ms 后请求；当前值的错误内联显示，旧值结果/错误不保留，也不弹出
  全局消息。

本任务不新增数据库对象、Celery 任务、配置项、权限或导航项。

## Data Flow

```text
Cron Form.useWatch
  -> scheduler-page-local 300ms debounce
  -> React Query + generated SchedulerService
  -> GET /api/v1/scheduler/cron-preview?cron_expression=...
  -> scheduler router (scheduler.jobs.read)
  -> scheduler service (fixed server clock + five iterations)
  -> existing cron.next_run_at (Celery + Asia/Shanghai)
  -> public response / generated client
  -> inline Shanghai-time preview or inline error
```

The router has no scheduler `Session` parameter and the service has no model,
CRUD, dispatch, audit-binding, or Celery dependency on this path. Permission
resolution remains the only request-scoped database activity outside this
capability.

## Public API Contract

### Endpoint

`GET /api/v1/scheduler/cron-preview?cron_expression=<five-field-expression>`

- Permission: `scheduler.jobs.read`.
- Input: only `cron_expression`, represented by a query parameter. It is not
  tied to a job ID, class path, config, `after`, or `count`.
- Success: `200` with the response below.

```json
{
  "base_at": "2026-07-26T00:00:00Z",
  "timezone": "Asia/Shanghai",
  "next_run_ats": [
    "2026-07-27T00:00:00Z",
    "2026-07-28T00:00:00Z",
    "2026-07-29T00:00:00Z",
    "2026-07-30T00:00:00Z",
    "2026-07-31T00:00:00Z"
  ]
}
```

`base_at` and each member of `next_run_ats` are timezone-aware UTC datetimes.
`timezone` is the literal `Asia/Shanghai`, which tells a client how to render
the business schedule. The list has exactly five ascending values, each
strictly later than `base_at`.

### Errors

| Condition | HTTP | Contract | Side effect |
| --- | --- | --- | --- |
| Caller lacks `scheduler.jobs.read` | 403 | Unified `detail` and `request_id` | No scheduler write or dispatch. |
| Empty, non-five-field, or Celery-invalid Cron | 422 | Unified `detail` and `request_id` | No scheduler write or dispatch. |
| Valid Cron | 200 | Fixed response shape above | No job/run/audit mutation and no Celery message. |

The endpoint does not use a task-class resolver: class availability, config
validation, capability flags, soft deletion, and manual-operation rules are
unrelated to interpreting a submitted Cron expression.

## Backend Design

1. Add `SchedulerCronPreviewPublic` to `backend/app/schemas/scheduler.py` with
   `base_at: datetime`, `timezone: Literal["Asia/Shanghai"]`, and
   `next_run_ats: list[datetime]` constrained to exactly five items with
   `Field(min_length=5, max_length=5)`.
2. Add a scheduler service helper with an optional `now` argument for tests.
   It calls `utc_now(now)` once, keeps that result as `base_at`, and invokes
   the existing `next_run_at(expression, after=cursor)` five times. Each result
   becomes the next cursor.
3. Translate the existing helper's `ValueError` into `SchedulerValidationError`
   at the service boundary so global exception handling retains `422`, `detail`,
   and `request_id`.
4. Add the permission-protected router `GET /cron-preview` without a session
   dependency. It delegates to the service and constructs the public response.

The iterative service shape deliberately reuses the production helper instead
of duplicating Celery Cron matching, Shanghai conversion, or day/week AND
semantics. `next_run_at()` has been verified with a base of `2026-07-26T00:00Z`
and `0 8 * * *`: its five values begin at `2026-07-27T00:00Z`, never at the
base time itself.

## Frontend Design

The existing scheduler editor is the only presentation surface. It already owns
the Cron field through `Form.useWatch`, so no new route, drawer, or shared
component is justified.

1. Add a page-local `useDebouncedValue` timer hook following the existing
   inventory select pattern. The 300ms timer is an external-time synchronization
   effect with cleanup.
2. Derive a trimmed Cron expression during render. Query only while the editor
   is open and the debounced expression is nonempty. Use a query key containing
   that expression and do not use `placeholderData` for this query.
3. While the value is debouncing or fetching, hide a previous result. When the
   current query fails, show its error in an inline Ant Design `Alert`; do not
   call `message.error`. The form remains editable and its existing save
   mutation remains authoritative.
4. Render a compact preview section immediately below the Cron field: its
   label includes `Asia/Shanghai`, it shows the returned base time and five
   ordered local times, and it visually distinguishes this calculated result
   from the table's saved `next_run_at` value.
5. Replace scheduler-page time rendering with an explicit
   `timeZone: "Asia/Shanghai"` formatter for both the new preview and existing
   scheduler timestamps. Browser locale must not decide scheduler business time.

The page-local debounce helper must not be imported from the inventory feature
or promoted to `shared/*`: it is a single-page interaction and the existing
repository rule avoids premature sharing.

## Compatibility And Rollback

- No migration, scheduler scan change, model change, task dispatch change, or
  new configuration is needed.
- Existing job CRUD, manual operations, task schema, list paging, permissions,
  and generated types remain compatible. Only the generated SDK gains one new
  read method and response type.
- Rollback removes the route, response schema, service helper, page-local query
  and generated client output together. Persisted jobs/runs need no recovery.

## Design Review Record

- `CONTEXT.md` defines a Permission as server-verifiable; `scheduler.jobs.read`
  is therefore enforcement, while the page query is not authorization.
- The Ant Design ADR supports compact feedback and form composition in this
  data-dense admin page.
- No scheduler-domain glossary term conflicts with the precise term “Cron
  preview”; no ADR is warranted because the route and fixed window are local,
  reversible feature decisions.
