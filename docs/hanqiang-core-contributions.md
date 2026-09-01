# hanqiang 通用与核心提交整理

> 生成日期：2026-09-01  
> 作者：`hanqiang <240448317@qq.com>`  
> 范围：`backend/JSECommon`、`frontend/JSE_UI_AI` 的全部可达 Git 引用（`--all`）

## 结论

在本次可读取的历史中，筛出 **98 条**系统通用功能、通用组件或核心能力相关提交：后端 59 条、前端 39 条。它们集中在权限与身份、运行时与可观测性、文件与异步处理、通知、事件回调、审批流、计划任务、服务通信、外部集成，以及前端应用壳和通用组件。

这不是作者全部提交的罗列。清单只收录满足下列任一条件的非合并提交：

1. 修改了跨业务复用的运行时、权限、通信、异步、存储、审批或计划任务能力；
2. 新增或改造了前端应用壳、路由/状态/工具、跨页面组件或通用服务；
3. 实现了由多个业务域消费的系统级平台能力（例如事件回调、服务通信、外部集成）。

以下内容明确排除：合并提交、子模块指针、开发日志、依赖产物、单一业务实体/工单/页面的实现，以及仅随业务功能附带的展示调整。

## 检索与复核

```bash
git -C backend/JSECommon log --all --author=hanqiang --no-merges
git -C frontend/JSE_UI_AI log --all --author=hanqiang --no-merges
git -C backend/JSECommon show --stat --oneline <SHA>
git -C frontend/JSE_UI_AI show --stat --oneline <SHA>
```

作者身份经两个子模块的 `git shortlog -sne --all` 校验。`backend/JSEToolingRust` 处于未初始化状态；在该目录执行 Git 会回退到根仓库，因此本清单不伪造或混入其独立历史。

表中“主要路径”是该提交的核心改动路径摘要，不等于完整文件列表；完整列表以对应 `git show --stat` 为准。

## 后端：权限、运行时与基础能力

| SHA | 日期 | 原始主题 | 主要路径 |
| --- | --- | --- | --- |
| [`c2fe51b1`](hanqiang-core-contributions/backend-2025-10-29-c2fe51b1.md) | 2025-10-29 | RABC权限系统根据新库实现 | `app/dependencies/permission_check.py`、`app/services/{permission,rbac_init,role}_service.py` |
| [`7d6aa5ab`](hanqiang-core-contributions/backend-2025-10-29-7d6aa5ab.md) | 2025-10-29 | RABC+字段解释器实现 | `app/api/v1/routes/permissions.py`、`app/core/{database,db_lock}.py` |
| [`b6e8fbbb`](hanqiang-core-contributions/backend-2025-10-31-b6e8fbbb.md) | 2025-10-31 | 权限完成 | `app/core/{config,database,dependencies}.py`、`app/dependencies/permission_check.py` |
| [`e0857d0d`](hanqiang-core-contributions/backend-2025-12-01-e0857d0d.md) | 2025-12-01 | 通用枚举完成 | `app/{api,crud,schemas,services}/enum_*` |
| [`7f775049`](hanqiang-core-contributions/backend-2025-11-27-7f775049.md) | 2025-11-27 | 通用枚举功能api | `app/api/v1/routes/enum_routes.py`、`app/models/common_enum.py` |
| [`a92c637f`](hanqiang-core-contributions/backend-2025-11-27-a92c637f.md) | 2025-11-27 | 调整redis,支持外部服务器+密码形式，优化README | `app/core/{cache,celery_app,config,redis_client}.py` |
| [`7ba88a12`](hanqiang-core-contributions/backend-2025-11-27-7ba88a12.md) | 2025-11-27 | 修复ENCRYPTION_KEY不从yaml配置文件读取 | `app/core/config.py` |
| [`5aaa334e`](hanqiang-core-contributions/backend-2025-12-03-5aaa334e.md) | 2025-12-03 | token刷新加入redis分布式锁，防止抢刷新。 | `app/utils/redis_lock.py`、`app/services/wxwork/wxwork_api.py` |
| [`89b47c34`](hanqiang-core-contributions/backend-2026-01-30-89b47c34.md) | 2026-01-30 | CORS 暴露 Content-Disposition 响应头 | `app/{main,main_refactored}.py` |
| [`21039f44`](hanqiang-core-contributions/backend-2026-02-14-21039f44.md) | 2026-02-14 | feat(logging): ELK Data Stream observability | `app/core/{logging,security}.py`、`app/middlewares/http_observability.py` |
| [`526927fb`](hanqiang-core-contributions/backend-2026-03-13-526927fb.md) | 2026-03-13 | 整理应用初始化数据库会话退出逻辑 | `app/main_refactored.py` |
| [`72bda3f7`](hanqiang-core-contributions/backend-2026-04-02-72bda3f7.md) | 2026-04-02 | fix(startup): 去除后台启动预置写入 | `app/{main,main_refactored}.py`、启动集成测试 |

## 后端：文件、导入导出与异步处理

| SHA | 日期 | 原始主题 | 主要路径 |
| --- | --- | --- | --- |
| [`5b298070`](hanqiang-core-contributions/backend-2025-12-02-5b298070.md) | 2025-12-02 | ftp从APScheduler调整成celery | `app/core/celery_app.py`、`app/tasks/ftp_tasks.py` |
| [`9158d8fe`](hanqiang-core-contributions/backend-2025-12-03-9158d8fe.md) | 2025-12-03 | 修复异步任务celery出现的全局loop不兼容问题 | `app/utils/celery_utils.py`、邮件/FTP/企微任务 |
| [`eb990317`](hanqiang-core-contributions/backend-2025-12-03-eb990317.md) | 2025-12-03 | 统一fernet密钥，邮件服务异步任务messageid报错修复 | `app/core/config.py`、`app/tasks/email_send_task.py` |
| [`1612bd8b`](hanqiang-core-contributions/backend-2025-12-10-1612bd8b.md) | 2025-12-10 | 增加数据导入功能，整合list类api接口规范，新增部分接口v1/list，skip/limit->page/page_size | `app/services/datafile/**`、`app/schemas/pagination.py`、`app/utils/import_processor.py` |
| [`080c5f54`](hanqiang-core-contributions/backend-2025-12-10-080c5f54.md) | 2025-12-10 | ftp增加下载 | `app/services/ftp/transfer_service.py` |
| [`98710a55`](hanqiang-core-contributions/backend-2025-12-10-98710a55.md) | 2025-12-10 | 优化datafile文件上传的目录规则 | `app/api/v1/routes/datafile_import.py` |
| [`0dda0329`](hanqiang-core-contributions/backend-2025-12-17-0dda0329.md) | 2025-12-17 | fix(security): 防止路径遍历攻击（Path Traversal） | `app/utils/path_validator.py`、文件监控解析服务 |
| [`3946d900`](hanqiang-core-contributions/backend-2025-12-17-3946d900.md) | 2025-12-17 | fix(security): 实现简化版SSRF防护（适用于局域网环境） | `app/utils/url_validator.py`、文件监控 API 调用器 |
| [`438dedc8`](hanqiang-core-contributions/backend-2025-12-17-438dedc8.md) | 2025-12-17 | fix(security): 增强ReDoS防护（使用regex库+timeout） | `app/services/file_monitor/regex_matcher.py` |
| [`4d848398`](hanqiang-core-contributions/backend-2025-12-17-4d848398.md) | 2025-12-17 | perf(file-processor): 异步I/O + 避免重复MD5计算 | `app/services/file_monitor/file_processor.py` |
| [`5da1ecb8`](hanqiang-core-contributions/backend-2025-12-18-5da1ecb8.md) | 2025-12-18 | refactor(arch): 重构FileMonitor任务模块解耦职责 | `app/services/file_monitor/*_service.py`、`app/tasks/file_monitor_tasks.py` |
| [`96de28ae`](hanqiang-core-contributions/backend-2025-12-18-96de28ae.md) | 2025-12-18 | refactor(arch): 重构FileProcessor解决上帝对象 | `app/services/file_monitor/{attachment_lifecycle_handler,file_upload_coordinator}.py` |
| [`731b714f`](hanqiang-core-contributions/backend-2025-12-18-731b714f.md) | 2025-12-18 | refactor(structure): 移动依赖注入到 app/dependencies | `app/dependencies/file_monitor.py` |
| [`80479603`](hanqiang-core-contributions/backend-2025-12-18-80479603.md) | 2025-12-18 | fix(arch): Service层通过CRUD层访问数据库 | 文件监控配置、邮件与 FTP CRUD 边界 |
| [`d7a7858c`](hanqiang-core-contributions/backend-2025-12-18-d7a7858c.md) | 2025-12-18 | refactor(config): 拆分 ConfigService | `app/services/file_monitor/{config_factory,config_manager,config_service}.py` |
| [`83211001`](hanqiang-core-contributions/backend-2025-12-18-83211001.md) | 2025-12-18 | refactor(api): 拆分 API Caller 长函数并完善文档 | `app/services/file_monitor/api_caller.py` |
| [`3c10511b`](hanqiang-core-contributions/backend-2025-12-19-3c10511b.md) | 2025-12-19 | refactor(file): 优化配置验证模块 | `app/services/file_monitor/{config_validator,file_matcher}.py` |
| [`75a213a7`](hanqiang-core-contributions/backend-2025-12-19-75a213a7.md) | 2025-12-19 | refactor(core): config/logging/celery improvements + archive backup | `app/core/{celery_app,config,logging}.py`、归档备份服务 |

## 后端：通知、事件回调与审批流

| SHA | 日期 | 原始主题 | 主要路径 |
| --- | --- | --- | --- |
| [`4d916409`](hanqiang-core-contributions/backend-2025-12-02-4d916409.md) | 2025-12-02 | 完成企业微信通知模块开发，完成IsActive/is_active->IsEnabled/is_enabled统一化改造。 | `app/services/wxwork/**`、`app/tasks/wxwork_tasks.py`、`app/utils/encryption.py` |
| [`e5708f7e`](hanqiang-core-contributions/backend-2026-02-09-e5708f7e.md) | 2026-02-09 | 企业微信跳转后台地址由config配置 | `app/core/config.py`、环境配置文件 |
| [`5b65edac`](hanqiang-core-contributions/backend-2026-06-10-5b65edac.md) | 2026-06-10 | fix: retry expired wxwork access tokens | 企微访问令牌刷新服务 |
| [`ff4db2d4`](hanqiang-core-contributions/backend-2026-06-10-ff4db2d4.md) | 2026-06-10 | feat: support custom wxwork retry recipients | 企微重试接收人配置与通知服务 |
| [`72589c64`](hanqiang-core-contributions/backend-2026-01-04-72589c64.md) | 2026-01-04 | 事件回调初版 | `app/services/event/**`、`app/tasks/callback_worker.py`、DataFile 回调 |
| [`66ae2419`](hanqiang-core-contributions/backend-2026-01-06-66ae2419.md) | 2026-01-06 | 事件回调初版 | 事件路由、调度器、回调 Worker 与契约 |
| [`0b5f74b5`](hanqiang-core-contributions/backend-2026-01-07-0b5f74b5.md) | 2026-01-07 | fix(event): 修复事件回调模块审查发现的16个问题 | `app/services/event/executors/external_executor.py`、`app/utils/url_validator.py` |
| [`8950f544`](hanqiang-core-contributions/backend-2026-01-07-8950f544.md) | 2026-01-07 | fix(event): 修复事件回调模块审查发现的16个问题 | 事件回调审查修复的历史分支提交 |
| [`caa33d2a`](hanqiang-core-contributions/backend-2026-01-16-caa33d2a.md) | 2026-01-16 | 审批流初版 | `app/services/approve/**`、审批模型与 API |
| [`c32e1c10`](hanqiang-core-contributions/backend-2026-01-16-c32e1c10.md) | 2026-01-16 | 审批流主流程完成，待测试 | 审批流程、节点与超时服务 |
| [`fb4c0214`](hanqiang-core-contributions/backend-2026-01-20-fb4c0214.md) | 2026-01-20 | 审批流核心功能完成 | `approval_service.py`、`process_service.py`、事件模板解析 |
| [`f68b3c8d`](hanqiang-core-contributions/backend-2026-01-21-f68b3c8d.md) | 2026-01-21 | 审批流-事件回调主流程完成，不包含弃审 | 审批事件载荷、分发与超时处理 |
| [`eb5e17b6`](hanqiang-core-contributions/backend-2026-01-21-eb5e17b6.md) | 2026-01-21 | 审批角色优化 | 审批角色、流程监控与操作日志服务 |
| [`7c805e02`](hanqiang-core-contributions/backend-2026-01-26-7c805e02.md) | 2026-01-26 | 完成审批流功能 | 审批工作流、告警、企微通知与 Celery 接入 |
| [`6cc930bc`](hanqiang-core-contributions/backend-2026-01-30-6cc930bc.md) | 2026-01-30 | 优化审批流接口与流程监控 | `app/api/v1/routes/approve/**`、流程服务 |
| [`fee47911`](hanqiang-core-contributions/backend-2026-07-14-fee47911.md) | 2026-07-14 | fix(approve): serialize parallel stage advancement | 并行审批阶段推进并发控制 |
| [`9dc50a5b`](hanqiang-core-contributions/backend-2026-07-30-9dc50a5b.md) | 2026-07-30 | perf(approve): optimize role and workflow list APIs | 审批角色/工作流列表服务、计时与权限依赖 |
| [`cdf8843a`](hanqiang-core-contributions/backend-2026-08-04-cdf8843a.md) | 2026-08-04 | perf(approve): optimize workflow detail reads | `app/services/approve/workflow_service.py` |

## 后端：计划任务、服务通信与外部集成

| SHA | 日期 | 原始主题 | 主要路径 |
| --- | --- | --- | --- |
| [`012d8658`](hanqiang-core-contributions/backend-2026-05-07-012d8658.md) | 2026-05-07 | feat(scheduled-task): add generic scheduled task backend | `app/{api,crud,models,schemas,services}/scheduled_task/**`、Celery 任务 |
| [`0350dc41`](hanqiang-core-contributions/backend-2026-05-08-0350dc41.md) | 2026-05-08 | feat(scheduled-task): complete maintenance reminder pipeline | 计划任务执行、通知与任务变量能力 |
| [`c978b4b6`](hanqiang-core-contributions/backend-2026-05-08-c978b4b6.md) | 2026-05-08 | fix(scheduled-task): hydrate task graph before logging | 计划任务图装载与执行日志 |
| [`a3b3ddff`](hanqiang-core-contributions/backend-2026-07-15-a3b3ddff.md) | 2026-07-15 | fix(scheduled-task): persist beat last-run baseline | Celery Beat 运行基线持久化 |
| [`14910a94`](hanqiang-core-contributions/backend-2026-07-15-14910a94.md) | 2026-07-15 | fix(scheduled-task): restore pending dispatch status | 待调度状态恢复 |
| [`2cebb894`](hanqiang-core-contributions/backend-2026-07-21-2cebb894.md) | 2026-07-21 | refactor(scheduled-task): simplify socket life warnings | 计划任务通用告警选择逻辑 |
| [`f5b95769`](hanqiang-core-contributions/backend-2026-07-28-f5b95769.md) | 2026-07-28 | feat(communication): add generic Python service communication | `app/services/service_communication/**`、服务通信模型/API |
| [`06723893`](hanqiang-core-contributions/backend-2026-07-29-06723893.md) | 2026-07-29 | feat(service-communication): add action-level chain queries | `app/services/service_communication/chains.py`、链路索引 |
| [`9111e45b`](hanqiang-core-contributions/backend-2026-08-14-9111e45b.md) | 2026-08-14 | feat(pms): implement external integration center | `app/services/integration/external_integration_service.py`、外部集成契约 |
| [`a4193e5e`](hanqiang-core-contributions/backend-2026-08-17-a4193e5e.md) | 2026-08-17 | refactor(external-integration): split backend service | `app/services/integration/external_integration_*.py` |
| [`da7f708f`](hanqiang-core-contributions/backend-2026-08-27-da7f708f.md) | 2026-08-27 | feat(integration): support callback condition operators | 集成事件与条件策略服务 |

## 前端：身份权限、基础数据与应用框架

| SHA | 日期 | 原始主题 | 主要路径 |
| --- | --- | --- | --- |
| [`e786e644`](hanqiang-core-contributions/frontend-2025-10-31-e786e644.md) | 2025-10-31 | 权限与人事完成，页面UI优化 | `PermissionTree.vue`、权限指令、`stores/user.ts`、RBAC 服务 |
| [`cda2ac7b`](hanqiang-core-contributions/frontend-2025-11-03-cda2ac7b.md) | 2025-11-03 | 多角色绑定 | 应用壳、认证/权限组合式函数、路由与角色服务 |
| [`57b44e86`](hanqiang-core-contributions/frontend-2025-11-28-57b44e86.md) | 2025-11-28 | 通用枚举前端 | `components/enum/**`、`services/enumService.ts`、枚举类型 |
| [`48a982e4`](hanqiang-core-contributions/frontend-2025-12-02-48a982e4.md) | 2025-12-02 | 完成企业微信通知模块开发，完成IsActive/is_active->IsEnabled/is_enabled统一化改造。 | 企微服务、菜单、权限树与状态类型 |
| [`0e25bf1d`](hanqiang-core-contributions/frontend-2025-12-10-0e25bf1d.md) | 2025-12-10 | 增加数据导入功能，整合list类api接口规范，新增部分接口v1/list，skip/limit->page/page_size | DataFile 服务/类型、通用列表接口适配 |
| [`e3f8464f`](hanqiang-core-contributions/frontend-2026-01-08-e3f8464f.md) | 2026-01-08 | 优化权限树 | `PermissionTree.vue` 与权限交互 |
| [`c7543cf1`](hanqiang-core-contributions/frontend-2026-01-30-c7543cf1.md) | 2026-01-30 | 权限树抽取查询按钮判断 | 权限树的通用查询动作规则 |
| [`3d749fa0`](hanqiang-core-contributions/frontend-2026-01-30-3d749fa0.md) | 2026-01-30 | 侧边栏菜单权限与培训报表入口 | `components/layout/AppSidebar.vue`、路由权限 |
| [`5e048690`](hanqiang-core-contributions/frontend-2026-03-31-5e048690.md) | 2026-03-31 | fix(permission): 兼容只读权限数组 | 权限数据兼容层 |
| [`a9036266`](hanqiang-core-contributions/frontend-2026-03-13-a9036266.md) | 2026-03-13 | 优化登录校验提示与日期时间输入样式 | 登录校验与公共输入样式 |
| [`1a420a3e`](hanqiang-core-contributions/frontend-2026-08-07-1a420a3e.md) | 2026-08-07 | fix(frontend): unify system user display | `utils/pmsUserDisplay.ts` 与跨模块用户展示 |

## 前端：文件、回调、审批与计划任务组件

| SHA | 日期 | 原始主题 | 主要路径 |
| --- | --- | --- | --- |
| [`5fcd5306`](hanqiang-core-contributions/frontend-2025-12-17-5fcd5306.md) | 2025-12-17 | 文件监控前端风格化完成 | `components/FileMonitor/**`、任务状态组件 |
| [`c076b877`](hanqiang-core-contributions/frontend-2025-12-19-c076b877.md) | 2025-12-19 | refactor(frontend): 拆分 FileMonitor 前端大组件 | FileMonitor 表单分区、解析历史组合式函数与服务 |
| [`88d8a596`](hanqiang-core-contributions/frontend-2026-01-04-88d8a596.md) | 2026-01-04 | 事件回调初版 | `components/event/**`、事件配置/日志页面与服务 |
| [`9c55b00b`](hanqiang-core-contributions/frontend-2026-01-06-9c55b00b.md) | 2026-01-06 | 事件回调初版 | 事件回调前端流程与日志展示 |
| [`f315a60f`](hanqiang-core-contributions/frontend-2026-01-26-f315a60f.md) | 2026-01-26 | 完成审批流功能 | 审批页面、路由、角色与工作流服务 |
| [`d45da2b5`](hanqiang-core-contributions/frontend-2026-01-30-d45da2b5.md) | 2026-01-30 | 优化审批页面与路由配置 | 审批模块路由与页面交互 |
| [`29e83a12`](hanqiang-core-contributions/frontend-2026-07-30-29e83a12.md) | 2026-07-30 | perf(approve): reduce role and workflow list requests | `services/approve/workflowService.ts`、角色/工作流页 |
| [`82ffe275`](hanqiang-core-contributions/frontend-2026-08-04-82ffe275.md) | 2026-08-04 | perf(approve): deduplicate workflow detail requests | 审批详情请求去重 |
| [`2c373c2c`](hanqiang-core-contributions/frontend-2026-05-07-2c373c2c.md) | 2026-05-07 | feat(scheduled-task): add scheduled task frontend module | `components/ScheduledTask/**`、路由、服务、类型 |
| [`8978bbe5`](hanqiang-core-contributions/frontend-2026-05-08-8978bbe5.md) | 2026-05-08 | feat(scheduled-task): refine task management experience | 任务表单、设备选择器、模板变量编辑器 |

## 前端：可复用交互、应用壳与导入能力

| SHA | 日期 | 原始主题 | 主要路径 |
| --- | --- | --- | --- |
| [`36f0fda3`](hanqiang-core-contributions/frontend-2026-03-23-36f0fda3.md) | 2026-03-23 | feat: 统一页面快速筛选多标签组件 | `utils/quickFilters.ts`、快速筛选多标签 UI |
| [`15ff7530`](hanqiang-core-contributions/frontend-2026-06-05-15ff7530.md) | 2026-06-05 | feat: add application tab navigation | `components/layout/AppTabs.vue`、`composables/useNavigationTabs.ts`、状态仓库 |
| [`006645db`](hanqiang-core-contributions/frontend-2026-06-11-006645db.md) | 2026-06-11 | feat: refresh lists when returning to tabs | `composables/useListRefresh.ts` |
| [`56ecd81a`](hanqiang-core-contributions/frontend-2026-06-22-56ecd81a.md) | 2026-06-22 | fix: add clipboard fallback for copy actions | `utils/clipboard.ts` |
| [`b33e4960`](hanqiang-core-contributions/frontend-2026-01-30-b33e4960.md) | 2026-01-30 | 统一导出文件名解析工具 | 通用导出文件名解析工具 |
| [`ccc960d1`](hanqiang-core-contributions/frontend-2026-07-29-ccc960d1.md) | 2026-07-29 | fix(frontend): prevent duplicate import submissions | `JseImportPreviewDialog.vue`、`useImportPreviewDialog.ts` |
| [`a9032985`](hanqiang-core-contributions/frontend-2026-07-29-a9032985.md) | 2026-07-29 | fix(frontend): recover stale Vite lazy modules | 路由动态导入恢复、导航 Tab |
| [`f8ad092b`](hanqiang-core-contributions/frontend-2026-07-31-f8ad092b.md) | 2026-07-31 | fix(frontend): isolate cached tab routes | `components/layout/TabRouteScope.vue` |
| [`c6cd76d5`](hanqiang-core-contributions/frontend-2026-08-19-c6cd76d5.md) | 2026-08-19 | fix(training): 自定义弹窗与 Element Plus 弹层共用 z-index 计数器，修复二次确认/下拉被蒙层遮挡 | `components/JseDialog.vue`、`composables/useOverlayZIndex.ts` |

## 前端：服务通信与外部集成平台

| SHA | 日期 | 原始主题 | 主要路径 |
| --- | --- | --- | --- |
| [`2c33ff61`](hanqiang-core-contributions/frontend-2026-07-28-2c33ff61.md) | 2026-07-28 | feat(communication): add service communication administration | 服务端点管理、记录详情、路由、服务与类型 |
| [`1a80e1ff`](hanqiang-core-contributions/frontend-2026-07-29-1a80e1ff.md) | 2026-07-29 | feat(frontend): add service communication chain monitoring | `components/service-communication/**`、链路监控页 |
| [`4c6d6b52`](hanqiang-core-contributions/frontend-2026-08-14-4c6d6b52.md) | 2026-08-14 | feat(frontend): add external integration center | `ExternalIntegrationCenter.vue`、集成服务、类型与路由 |
| [`e09e795b`](hanqiang-core-contributions/frontend-2026-08-14-e09e795b.md) | 2026-08-14 | feat(frontend): align external integration dialogs | 外部集成 HTTP 配置编辑器与对话框壳 |
| [`f85eaed4`](hanqiang-core-contributions/frontend-2026-08-17-f85eaed4.md) | 2026-08-17 | refactor(external-integration): split frontend center | `components/externalIntegration/**`、集成组合式函数 |
| [`14d08c36`](hanqiang-core-contributions/frontend-2026-08-25-14d08c36.md) | 2026-08-25 | feat(external-integration): add FT event route editor | 集成回调编辑器、审计详情和事件路由 UI |
| [`7c6ca57c`](hanqiang-core-contributions/frontend-2026-08-26-7c6ca57c.md) | 2026-08-26 | feat(integration): show scenario callback variables | 外部集成回调变量展示 |
| [`f75e5a09`](hanqiang-core-contributions/frontend-2026-08-27-f75e5a09.md) | 2026-08-27 | feat(integration): configure FT equipment master events | 外部集成事件配置 |
| [`d7efa7e6`](hanqiang-core-contributions/frontend-2026-08-27-d7efa7e6.md) | 2026-08-27 | feat(integration): configure callback condition fields | `ConditionEditor.vue`、集成回调条件编解码 |

## 使用说明

从功能定位某次变更时，先按上面的分组找到能力边界，再在对应子模块执行：

```bash
git show --stat --oneline <SHA>
git show <SHA> -- <主要路径中的文件>
```

这样可避免把根仓库的子模块指针提交误认为实际实现提交。
