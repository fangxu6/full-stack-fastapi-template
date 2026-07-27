# 定时任务管理审查问题修复实施计划

## Delivery order

1. **先补失败测试**
   - 保留 `0d3c59d` 的临时 `.env` CSV 回归测试，并补充真实环境变量来源覆盖，防止
     `NoDecode` 基线被回退。
   - 覆盖嵌套 Secret 类型和 `credential`、`authorization`、`access_key` 绕过。
   - 覆盖业务 `ValueError`、并发创建冲突、queued 重投风暴和上海补发最大值。

2. **修复配置与启动边界**
   - 验证 scheduler settings 字段中的既有 `NoDecode`、CSV parser 和唯一性校验；除非回归
     测试暴露缺口，不重复修改该已落地修复。
   - 移除 Celery signal 校验，改为 `app.core.celery` 导入时直接 fail-fast。
   - 增加 Worker/Beat 子进程退出码测试，并验证 FastAPI app 在同样缺配置环境仍可导入。

3. **收紧凭据边界**
   - 扩展敏感键规则，递归检查配置模型 JSON Schema 中的 password format。
   - 在 create/update/schema/冻结快照路径复用同一 validator，不新增实现类级接口。
   - API 测试断言 422 且数据库没有 job/run 快照写入。
   - 不添加历史 JSONB 扫描、清洗或凭据轮换；用户已确认历史 scheduler 配置没有凭据。

4. **修复运行创建事务**
   - `create_run` 统一锁定 job 行并在 `commit=False` 时使用 savepoint。
   - IntegrityError 只回滚当前 savepoint，不回滚扫描器外层事务。
   - 增加两个任务同批扫描且其中一个发生并发冲突的回归测试。

5. **限制技术投递**
   - 新增 `next_dispatch_at` 模型字段、Alembic 回填和部分索引。
   - 提取按 ID/批量领取的共享投递 helper，批量上限固定为 100，重投间隔复用 visibility
     timeout；禁止引入新设置或队列。
   - 自动扫描和人工 API 都使用该 helper，删除“查询全部 queued 并逐条 delay”的逻辑。
   - 测试首次立即投递、broker 失败下分钟重试、成功后 visibility timeout 前不重复、超时后
     仍 queued 可重投，以及单次最多 100 条。

6. **修正执行分类**
   - 分离类/配置解析和业务 `run()` 两个 try boundary。
   - 保留 `ScheduledTaskSkipped`，将业务 `ValueError` 纳入 `EXECUTION_FAILED`。
   - 验证状态、安全摘要、邮件类别和对应限频字段。

7. **修正前端时间并回归**
   - 增加无依赖的上海 `datetime-local` 格式 helper，并替换当前 UTC max。
   - 在现有 Playwright 基础设施中增加 scheduler 补发流测试，固定时间断言 max 显示和提交
     的 UTC 转换；不引入 Vitest 或新的日期时间依赖。
   - 执行 scheduler、inventory、Celery、API、迁移和质量钩子回归。

## Validation

```powershell
Set-Location ..
bash backend/scripts/lint.sh

Set-Location backend
uv run pytest tests/modules/scheduler tests/api/routes/test_scheduler.py tests/core/test_celery.py tests/modules/inventory/test_daily_report.py

Set-Location ../frontend
bunx biome ci --no-errors-on-unmatched --files-ignore-unknown=true ./
bun run build
bunx playwright test tests/scheduler.spec.ts --project=chromium

Set-Location ..
python hooks/run_quality_hooks.py --json
```

迁移升级、降级和真实 Celery 进程测试必须使用隔离数据库、Redis 与空 SMTP 测试配置，不得
向开发或生产收件人发送邮件。

## Completion checklist

- [ ] 7 项 finding 均有先失败、修复后通过的针对性测试。
- [ ] 数据库迁移升级/降级通过，现有 queued 行可继续被投递。
- [ ] 父任务的原始行为和既定架构约束未改变。
- [ ] 质量钩子、后端类型/风格检查、前端类型检查和构建通过。
- [ ] 实施结果回写父任务验收状态；本子任务完成后再继续父任务收尾。
