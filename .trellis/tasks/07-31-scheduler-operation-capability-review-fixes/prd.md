# 修复定时任务操作能力审查问题

## Goal

修复 `7488356` 审查确认的两项回归：保存任务的实现类在后续部署中失效时，管理 API 仍必须可读、可
修复；允许补发的任务必须继续覆盖上海本地时间补发弹窗和请求序列化的浏览器行为。

## Confirmed Baseline

- `SchedulerJobPublic` 的 `can_run_now` 与 `can_backfill` 由 router 为每个 job 调用
  `service.task_capabilities()` 得出。
- `resolve_task_class()` 对无法导入、类不再继承 `ScheduledTask` 或配置 schema 不再合法的 class
  path 抛出 `ValueError`。旧 job 的列表、详情和写操作响应不能因此变成 500。
- 两个已部署的库存日报实现类均不支持 backfill；它们在管理页继续隐藏补发操作。
- 之前的浏览器测试同时验证了允许补发时 Shanghai `datetime-local` 最大值与 UTC 请求转换，但该
  场景因日报任务现在禁用 backfill 而被移除。

## Requirements

- 对无法解析的已保存 job class path，所有 `SchedulerJobPublic` 响应返回
  `can_run_now=false`、`can_backfill=false`，而不改变 job 的其他可读、删除、恢复或历史查询行为。
- 对失效 class path 的 `run-now` 和 `backfill` 请求，服务层返回既有统一 `SchedulerValidationError`
  422，而不是未处理的 500；不创建 `SchedulerRun`、不投递 Celery。
- 显式 `False` 的实现类仍保留既有能力限制；可解析且未覆写能力的类继续默认允许。
- 浏览器测试同时覆盖：禁用补发时按钮不显示；允许补发时显示弹窗、使用 Shanghai 本地最大值并发送
  UTC `planned_at`。

## Acceptance Criteria

- [x] 人工插入或模拟的失效 class path job 在列表和详情 API 中返回 200 与两个 `false` 能力字段。
- [x] 对该 job 的立即运行和合法历史补发返回 422 `detail + request_id`，且 run 表与 dispatch 记录
      不变。
- [x] 现有两个库存日报任务继续在页面隐藏补发入口并允许立即运行。
- [x] 允许补发的 UI 分支恢复 Shanghai wall-clock 最大时间和 UTC 请求载荷的自动化覆盖。
- [x] scheduler 相关后端测试、类型/lint 和 scheduler Playwright 测试通过。

## Out Of Scope

- 为失效实现类创建数据库迁移、自动修复/替换 class path、变更 job 配置、增加新 API 字段或修改
  90 天补发规则。
