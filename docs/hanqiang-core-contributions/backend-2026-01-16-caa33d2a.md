# 审批流平台初版

> 来源总览：[hanqiang 通用与核心提交整理](../hanqiang-core-contributions.md)

## 1. 提交信息

- 仓库：backend/JSECommon
- SHA：caa33d2a20030c8df03b664657fda49e71dc2c25
- 日期：2026-01-16
- 作者：hanqiang
- 原始主题：审批流初版
- 变更规模：42 个文件，新增 11,891 行、删除 5,005 行

这是审批流的领域骨架提交，包含工作流配置、审批角色、流程实例、节点分配、API、Schema、CRUD，以及与既有事件回调平台的桥接。coverage.xml、config/config_Feature.json 等产物不应直接复制。

## 2. 文件地图

| 层次 | 文件 | 可复用职责 |
| --- | --- | --- |
| 路由 | app/api/v1/routes/approve/workflow.py | 工作流创建、列表、详情、更新、删除、调试启动 |
| 路由 | app/api/v1/routes/approve/role.py | 审批角色 CRUD、角色成员增删、审批人查询 |
| 路由 | app/api/v1/routes/approve/process.py | 流程启动、确认、业务数据修改、取消/中止、弃审、催办、重新提交、详情 |
| 路由 | app/api/v1/routes/approve/approval.py | 待审批列表与节点审批动作 |
| 路由 | app/api/v1/routes/approve/my_processes.py | 当前用户发起流程列表 |
| Schema | app/schemas/approve/workflow.py、role.py、process.py、approval.py、my_processes.py | 请求校验、列表/详情/时间轴响应和调试输入 |
| 模型 | app/models/approve/workflow_master.py、workflow_detail.py | 工作流主表与节点配置 |
| 模型 | app/models/approve/role_master.py、role_user_detail.py | 角色定义与角色成员 |
| 模型 | app/models/approve/process_master.py、process_detail.py | 流程实例与节点执行记录 |
| CRUD | app/crud/approve/crud_workflow*.py、crud_role*.py、crud_process*.py | 数据访问、分页、节点位置重算 |
| 服务 | app/services/approve/workflow_service.py | 工作流配置生命周期与节点校验 |
| 服务 | app/services/approve/role_service.py | 角色类型、成员和审批人解析 |
| 服务 | app/services/approve/process_service.py | 发起、确认、推进、详情、重新提交和运维动作 |
| 服务 | app/services/approve/approval_service.py | 抢单、审批动作、并行组判定和终态处理 |
| 服务 | app/services/approve/node_assignment_service.py | 角色成员、部门负责人/部门审批人列表和阶段分配 |
| 服务 | app/services/approve/event_dispatcher.py | 审批事件到通用事件回调平台的桥接 |
| 服务 | app/services/approve/approval_process_service.py | 供其他模块调用的 start_process 门面 |

CodeGraph 显示的主要调用关系：

~~~text
API route
  -> process_service / approval_service / workflow_service / role_service
     -> CRUD + SQLAlchemy models
     -> node_assignment_service
     -> approve.event_dispatcher.trigger_event()
        -> 通用 event_dispatcher.publish()
~~~

## 3. 数据模型与状态

### 3.1 工作流配置

Approve_Workflow_Master 保存 WorkflowCode、WorkflowName、FeatureID、FeatureNodeCode、InitiationMode、FlowAdminRoleID、IsEnabled、IsSystem；WorkflowCode 唯一，流程管理员角色必须是 RoleType=2。

Approve_Workflow_Detail 是节点配置：

- NodeLevel 使用正整数格式 stage.order，如 1.2；
- NodePosition：1 首节点、2 中间节点、3 末节点、4 唯一节点；
- ParallelPolicy：1 串行、2 并行 AND、3 并行 OR；
- IsSingleApproval=true 强制节点按串行处理；
- RoleID 绑定审批角色；
- TimeoutHours/TimeoutAction 预留给超时策略；
- EnableWXNotify 控制节点通知。

### 3.2 审批角色

Approve_Role_Master.RoleType 区分普通审批人、流程管理员、动态部门负责人、部门审批人列表、发起人自选审批人（1~5）。Approve_Role_UserDetail 以 RoleID + UserID 关联成员；节点角色必须有效、启用且类型在 1/3/4/5，流程管理员必须为类型 2。

### 3.3 流程实例与节点记录

Approve_Process_Master 的 ProcessStatus 为 1 待确认、2 进行中、3 已通过、4 已否决、5 已退回、6 已取消、7 已弃审；CallbackStatus 为 0 无、1 执行中、2 成功、3 失败。BusinessCode 配合 ActiveBusinessCode 约束活跃流程唯一，BusinessData 保存业务快照，ParentProcessID 指向重新提交前流程。

Approve_Process_Detail 记录每个节点的 ApproverID、ApproveStatus（1 未处理、2 同意、3 否决、4 退回、5 失效）、NodeGeneration、AssignTime 和 ApproveTime。初始 ApproverID 为空，采用抢单模式。

## 4. 核心流程

### 4.1 发起

POST /processes/start -> process_service.start_process()：

1. 校验工作流、发起人和 BusinessCode 唯一性；
2. 创建进行中的流程并由 NodeAssignmentService 分配首阶段节点；
3. 提交主事务；
4. 提交后写操作日志并发布 approval_process_started、approval_node_assigned 事件。

ApprovalProcessService.start_process() 提供后端门面，并允许 auto_commit=false 由调用方控制事务。

### 4.2 审批与推进

POST /process-nodes/{process_node_id}/handle -> ApprovalService.handle_approval()：

- 角色成员或直接分配审批人才能操作；
- UPDATE ... WHERE ApproveStatus=1 实现抢单，重复处理被拒绝；
- APPROVE 调用 advance_process()；
- RETURN 仅中间/末节点可用，OR 并行不支持退回；
- REJECT 对串行、AND 并行、OR 并行分别计算终态；
- advance_process() 不 commit：串行逐节点、AND 全组通过、OR 任一短路，无下一节点则完成。

### 4.3 重新提交和运维

RETURN/REJECT/CANCEL/STOP 分别产生退回、否决、取消/中止状态；重新提交为拒绝/退回/取消流程创建新实例并递增 NodeGeneration。拒绝或取消从首节点重审，退回复制已通过节点后从退回节点继续。流程管理员相关催办、弃审和流程详情接口必须单独授权。

## 5. 事件回调桥接

app/services/approve/event_dispatcher.py 定义 started、node_assigned、node_approved、returned、rejected、completed、abandon、resubmitted、cancelled、stopped 十类审批事件。trigger_event() 调用通用事件平台；失败时回写 CallbackStatus=3，但不阻塞已提交的审批主业务。事件数据应包含 ProcessID、BusinessCode、WorkflowID、NodeLevel、操作者和终态信息。

初版采用“主事务提交后发布事件”，数据库与消息队列不是原子事务；迁移时必须保留回调状态、重试和补偿策略。

## 6. API 权限边界

路由使用细粒度权限：approve:workflow:create/update/delete/debug、approve:role:create/update/delete/assign、approve:mvp:process:start/resubmit、approve:my_processes:confirm/edit_business_data、approve:process:interrupt/abandon/urge、approve:mvp:process-node:handle。业务授权仍需在服务层校验，不能依赖前端隐藏按钮。

## 7. 跨项目迁移与验收

- [ ] 建立工作流、节点、角色、角色成员、流程主表、流程节点六类数据及唯一/状态索引。
- [ ] 统一 NodeLevel、ParallelPolicy、NodePosition 和所有状态字典。
- [ ] 为串行、AND、OR、抢单并发、退回、否决、取消、重新提交补测试。
- [ ] 角色解析抽为策略，支持部门负责人、部门审批人列表和发起人自选。
- [ ] 审批、超时任务和流程推进共用锁与条件状态更新。
- [ ] 事件失败可追踪、可补偿，事件载荷和业务数据脱敏。
- [ ] UUID、BIT(1)、JSON 在数据库适配层统一转换。
- [ ] 调试启动、催办、弃审和流程管理员操作有独立权限与审计。

## 8. CodeGraph/Git 复核命令

~~~bash
rtk codegraph explore "approval_service process_service approve workflow node assignment event dispatcher"
rtk codegraph explore "ApprovalService handle_approval ProcessService start_process advance_process"
rtk codegraph node backend/JSECommon/app/models/approve/process_master.py
rtk codegraph node backend/JSECommon/app/models/approve/process_detail.py
rtk git -C backend/JSECommon show --stat --oneline --summary caa33d2a
rtk git -C backend/JSECommon show --name-status --format=fuller caa33d2a
~~~
