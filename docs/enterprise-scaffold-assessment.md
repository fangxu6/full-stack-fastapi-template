# 企业脚手架适配性评估与拆分建议

可以，但**更适合作为“企业级研发底座”**，还**不适合直接作为“所有业务长期无序叠加”的最终形态**。

## 先说结论

**当前项目适合做企业脚手架 7/10：**

- **适合的部分**：技术栈统一、前后端契约清晰、工程化基础不错。
- **不足的部分**：当前更像“中后台模板 + demo 业务”，还不是“企业平台化基座”。

你这个仓库现在已经具备这些优点：

- 后端：FastAPI + SQLModel + Alembic + PostgreSQL，分层清晰
- 前端：React + TanStack Router/Query + 生成 client，工程链路完整
- 有 Docker、测试、OpenAPI、文档驱动流程

但从仓库现状看，平台能力还偏薄：

- 业务模块还很少，主要还是 `users / items / docs(rules)`
- 权限控制仍明显偏模板化，很多地方还是 `is_superuser`
- 缺少企业常见平台模块：工作流、通知、文件中心、集成中心、审计中心、任务调度、报表中心、字典/参数中心等
- 前端目前还是“页面集合”，还不是“平台壳 + 业务域 + 通用能力”的结构

## 建议：要拆，但先做模块化单体拆分，不要一上来微服务

如果后续“所有业务都在这个脚手架下做”，我建议：

### 不建议

- 一开始就按微服务拆
- 一开始就按团队/部门拆库拆服务
- 所有业务直接往 `routes/components/services` 里平铺堆

### 建议

先做成 **模块化单体（Modular Monolith）**：

- **平台共享模块**
- **业务域模块**
- 每个模块内部再保留自己的前后端分层

这样后面如果某些模块真的需要独立部署，再抽服务也更容易。

## 一、从“功能角度”拆分

### 1）后端功能拆分

#### 当前后端结构

现在偏技术分层：

- `api/routes`
- `services`
- `crud`
- `models`
- `schemas`

这个结构适合起步，但如果业务越来越多，后面会出现：

- 同一个 `services` 目录越来越大
- 业务边界模糊
- 公共能力和业务能力混杂

#### 建议目标结构

按**业务域 + 平台能力**拆：

##### A. 平台基础模块

1. **iam / auth 模块**
   - 登录、JWT、刷新令牌
   - 用户、角色、权限、菜单、数据权限
   - 组织、部门、岗位
2. **system 模块**
   - 系统参数
   - 数据字典
   - 枚举管理
   - Feature Flag
   - 租户配置（如果未来多租户）
3. **workflow 模块**
   - 审批流定义
   - 审批实例
   - 待办/已办
   - 节点动作、回退、转签
4. **notification 模块**
   - 站内信
   - 邮件
   - 短信
   - Webhook / IM 通知
5. **file 模块**
   - 上传/下载
   - 预览
   - 文件元数据
   - OSS/MinIO/S3 适配
6. **integration 模块**
   - 第三方系统接入
   - 外部 API client
   - Webhook
   - 消息适配器
7. **job 模块**
   - 定时任务
   - 异步任务
   - 重试/补偿
8. **audit 模块**
   - 操作日志
   - 审计日志
   - 数据变更记录
9. **reporting 模块**
   - 报表查询
   - 导出
   - 看板接口

##### B. 业务域模块

每个业务单独成模块，例如：

- `customer`
- `sales`
- `purchase`
- `inventory`
- `quality`
- `finance`
- `project`
- `contract`

每个业务模块内部自己有：

- route
- service
- repository/crud
- model
- schema

也就是从“全局技术分层”升级为“**按业务垂直切块，块内再分层**”。

### 2）前端功能拆分

#### 当前前端结构

现在偏：

- `routes`
- `components`
- `hooks`
- `client`

这对模板项目够用，但业务一多，容易变成：

- 页面逻辑分散
- 通用能力和业务能力混用
- 组件目录膨胀

#### 建议目标结构

前端按 **App Shell + Platform Features + Domain Features** 拆：

##### A. 平台层

1. **app-shell**
   - Layout
   - Sidebar
   - Header
   - Tabs
   - Breadcrumb
   - Theme
2. **auth-permission**
   - 登录态
   - 权限点
   - 路由守卫
   - 菜单可见性
   - 按钮级权限
3. **system-management**
   - 用户管理
   - 角色管理
   - 部门管理
   - 字典管理
   - 参数配置
4. **workflow-workbench**
   - 我的待办
   - 我的已办
   - 发起流程
   - 审批详情
5. **notification-center**
   - 消息中心
   - 通知偏好设置
6. **file-center**
   - 上传控件
   - 文件列表
   - 预览器
7. **report-center**
   - 报表页
   - 导出中心
   - Dashboard

##### B. 业务功能层

每个业务一个 feature：

- `features/customer`
- `features/sales`
- `features/purchase`
- `features/inventory`
- `features/quality`

每个 feature 下面再拆：

- pages
- components
- hooks
- query
- forms
- utils

##### C. 前端通用业务组件层

- 通用表格页框架
- 通用搜索表单
- 通用详情页
- 通用弹窗表单
- 通用导入导出
- 通用状态标签/审批流组件

## 二、从“非功能角度”拆分

### 1）后端非功能拆分

#### A. 安全

当前项目能做登录鉴权，但企业化还应拆出：

- **认证子模块**：登录、刷新 token、单点登录预留
- **授权子模块**：RBAC、数据权限、资源权限
- **安全治理子模块**：
  - 限流
  - 密码策略
  - 登录失败锁定
  - IP 白名单/黑名单
  - 审计追踪

> 目前仓库里权限能力还偏基础，且前端 token 在 `localStorage`，更适合内部系统 MVP，不是企业强化版终态。

#### B. 可观测性

单独沉淀：

- 日志规范
- Trace / Request ID
- Metrics
- 健康检查 `/health` `/readiness`
- 慢查询/慢接口监控
- 结构化错误追踪（structlog stdout NDJSON + Request ID）

#### C. 性能

拆出：

- 缓存层
- 查询优化层
- 分页/批处理规范
- 异步任务执行层
- 导入导出任务化

#### D. 稳定性

拆出：

- 事务边界规范
- 重试/补偿
- Outbox/Event 机制
- 幂等控制
- 降级策略

#### E. 数据治理

拆出：

- 审计字段基类
- 软删除/归档策略
- 数据权限
- 租户隔离（如果要做 SaaS）
- 主数据/字典统一治理

#### F. 工程治理

拆出：

- OpenAPI 规范治理
- Migration 管理
- Seed 数据机制
- 契约测试
- 模块脚手架生成器

### 2）前端非功能拆分

#### A. 权限与导航治理

单独做：

- 路由守卫层
- 菜单权限层
- 按钮权限层
- 页面级权限兜底

#### B. 状态与数据获取治理

单独收口：

- Query Key 规范
- 缓存失效策略
- 错误处理统一
- Loading / Empty / Error 三态统一

#### C. UI 设计系统

单独沉淀：

- Design Tokens
- 通用表单规范
- 通用表格规范
- 弹窗/抽屉规范
- 审批/状态/标签规范

#### D. 可观测性

单独做：

- 前端错误监控
- 埋点体系
- 页面性能采样
- 用户行为日志

#### E. 性能

单独做：

- 路由级懒加载
- 大表格虚拟滚动
- 大表单分片渲染
- 首屏资源拆分
- 低频模块按需加载

#### F. 运行时配置

单独做：

- 多环境配置
- Feature Flag
- 动态菜单/动态字典
- 品牌化/主题化能力

#### G. 测试体系

单独沉淀：

- 组件测试
- 页面测试
- 权限场景测试
- E2E 流程测试

## 三、推荐的“前后端最终拆分方式”

### 后端建议

从现在的：

- 全局 `routes/services/crud/models`

升级到：

- `core`：配置、数据库、异常、日志、安全基础
- `infra`：缓存、消息、文件存储、第三方适配
- `modules`：按业务/平台模块拆
  - `iam`
  - `system`
  - `workflow`
  - `notification`
  - `file`
  - `integration`
  - `audit`
  - `reporting`
  - `customer`
  - `sales`
  - `purchase`
  - ...

### 前端建议

从现在的：

- 全局 `routes/components/hooks`

升级到：

- `app`：应用壳
- `platform`：权限、系统管理、通知、工作流、文件、报表
- `features`：各业务域
- `shared`：通用组件、hooks、utils、types

## 四、最该优先补的模块

如果你要把它真正变成“企业长期脚手架”，我建议优先做这几件：

### 第一优先级

1. **RBAC/IAM 正式落地**
2. **系统管理模块**（用户/角色/部门/字典/参数）
3. **审计日志**
4. **文件中心**
5. **统一异常/日志/trace 体系**
6. **前端权限守卫 + 菜单权限 + 按钮权限**

### 第二优先级

7. **工作流中心**
8. **通知中心**
9. **任务调度中心**
10. **集成中心**

### 第三优先级

11. **报表中心**
12. **多租户/数据权限**
13. **模块脚手架生成能力**

## 五、最终判断

**结论很明确：**

- **适合做企业脚手架的基础盘**
- **但必须先从“模板型项目”升级成“模块化平台型项目”**
- **需要拆分，但优先是模块拆分，不是微服务拆分**

如果你愿意，我下一步可以直接给你输出一版更落地的：

1. **后端目录拆分方案（到文件夹级）**
2. **前端目录拆分方案（到 feature 级）**
3. **企业脚手架 1.0 必备模块清单**
4. **按 3 个阶段的演进路线图**

## 六、基于当前仓库的落地目录拆分方案

这一节不是抽象建议，而是基于当前仓库实际结构：

- 后端当前主目录：`backend/app/api`、`backend/app/services`、`backend/app/crud`、`backend/app/models`、`backend/app/schemas`
- 前端当前主目录：`frontend/src/routes`、`frontend/src/components`、`frontend/src/hooks`、`frontend/src/client`

目标不是一次性重写，而是在**保持现有 API 和页面可用**的前提下，把后续新增能力迁移到新结构里。

### 1）后端建议目标目录

建议从当前：

- `backend/app/api/routes/*.py`
- `backend/app/services/*.py`
- `backend/app/crud/*.py`
- `backend/app/models/*.py`
- `backend/app/schemas/*.py`

逐步演进为：

```text
backend/app/
  api/
    main.py
    deps.py
    dependencies/
      auth.py
      database.py
  core/
    config.py
    db.py
    security.py
    exceptions.py
    logging.py
    observability.py
  infra/
    db/
      base.py
      session.py
    cache/
      redis.py
    storage/
      local.py
      s3.py
    messaging/
      webhook.py
      email.py
    tasks/
      queue.py
    integrations/
      base.py
  modules/
    iam/
      api.py
      service.py
      repository.py
      models.py
      schemas.py
      permissions.py
    system/
      api.py
      service.py
      repository.py
      models.py
      schemas.py
    audit/
      api.py
      service.py
      repository.py
      models.py
      schemas.py
    file/
      api.py
      service.py
      repository.py
      models.py
      schemas.py
      storage.py
    workflow/
      api.py
      service.py
      repository.py
      models.py
      schemas.py
    notification/
      api.py
      service.py
      repository.py
      models.py
      schemas.py
    reporting/
      api.py
      service.py
      repository.py
      schemas.py
    items/
      api.py
      service.py
      repository.py
      models.py
      schemas.py
    users/
      api.py
      service.py
      repository.py
      models.py
      schemas.py
    docs/
      api.py
      service.py
      schemas.py
  main.py
```

### 2）后端拆分原则

- `core` 只放跨模块基础能力，不放业务逻辑。
- `infra` 只放技术适配层，比如缓存、文件存储、邮件、Webhook、任务执行器。
- `modules` 才是业务和平台能力的主承载区。
- 每个模块内部自己维护 `api/service/repository/models/schemas`，避免全局 `services` 和 `crud` 持续膨胀。
- 现有 `users/items/docs` 不必一次性重写，可以先按“新模块增量、新代码新结构、老代码逐步迁移”的方式推进。

### 3）后端第一步实际落法

建议不要第一天就移动所有文件，而是分三步：

1. 新增 `backend/app/modules/`，先把**新增模块**放进去。
2. 把 `api/main.py` 的路由注册机制改成“可同时注册老 routes 和新 modules api”。
3. 等 `iam/system/audit/file` 这些新模块稳定后，再把 `users/items/docs` 逐步迁移进去。

这比一次性重构风险小很多，也更符合当前模板仓库的演进方式。

### 4）前端建议目标目录

建议从当前：

- `frontend/src/routes`
- `frontend/src/components`
- `frontend/src/hooks`
- `frontend/src/client`

逐步演进为：

```text
frontend/src/
  app/
    router/
    providers/
    layout/
    navigation/
  platform/
    auth/
      hooks/
      guards/
      components/
      utils/
    system/
      users/
      roles/
      departments/
      dictionaries/
      params/
    workflow/
      pages/
      components/
      query/
    notification/
      pages/
      components/
      query/
    file/
      pages/
      components/
      query/
    reporting/
      pages/
      components/
      query/
  features/
    items/
      pages/
      components/
      hooks/
      query/
      forms/
      utils/
    users/
      pages/
      components/
      hooks/
      query/
      forms/
      utils/
  shared/
    components/
    hooks/
    utils/
    types/
    permissions/
    table/
    form/
  client/
  routes/
```

### 5）前端拆分原则

- `app` 放应用壳，不放具体业务页面。
- `platform` 放平台通用能力，例如权限、系统管理、通知、文件、工作流。
- `features` 放业务域功能，例如 `items`、未来的 `customer/sales/inventory`。
- `shared` 放纯复用层，不承载业务含义。
- `client` 仍然保留为生成代码目录，不直接手改。
- `routes` 在过渡期可以保留，用来承接 TanStack Router 的实际路由文件，再逐步把页面实现下沉到 `platform` / `features`。

### 6）前端第一步实际落法

建议先做这几件事：

1. 把侧边栏、Header、用户态、主题切到 `app/layout`、`app/navigation`、`app/providers`。
2. 把现有 `Admin`、`Items` 组件沉到 `features/users`、`features/items`。
3. 新增权限守卫层，后续所有新页面统一通过守卫接入。
4. 保持 `routes/*.tsx` 足够薄，只做路由装配和页面挂载。

## 七、企业脚手架 1.0 必备模块清单

这里的 1.0 不是“所有企业功能”，而是“足以支撑多个业务继续往上长”的最小平台底座。

### P0：必须先补齐

#### 1. IAM / RBAC

目标：

- 替代大量 `is_superuser` 判断
- 引入用户、角色、权限点、菜单权限、按钮权限
- 为后续数据权限预留扩展点

落地范围：

- 后端：用户、角色、权限点、角色权限关联、用户角色关联
- 前端：路由守卫、菜单可见性、按钮级权限封装
- 契约：当前用户权限集合接口、菜单权限接口

验收标准：

- 非超管也能通过角色获得访问能力
- 页面按钮可按权限点隐藏/禁用
- 后端接口不再依赖页面是否隐藏来保证安全

#### 2. 系统管理模块

目标：

- 提供平台管理后台的最小闭环

落地范围：

- 用户管理
- 角色管理
- 部门管理
- 字典管理
- 系统参数管理

验收标准：

- 能通过管理页完成基础系统配置
- 字典和参数可供业务模块复用

#### 3. 审计日志

目标：

- 为“谁在什么时间改了什么”提供统一记录能力

落地范围：

- 登录日志
- 操作日志
- 审批操作日志
- 关键字段变更记录

验收标准：

- 至少关键写操作有统一记录
- 日志可按用户、时间、对象、动作查询

#### 4. 文件中心

目标：

- 提供统一上传、下载、预览、引用能力

落地范围：

- 文件元数据表
- 本地存储适配
- 对象存储适配预留
- 通用上传组件

验收标准：

- 业务模块不再各自散落实现上传逻辑
- 后续附件类需求可直接复用

#### 5. 异常 / 日志 / Trace 体系

目标：

- 先把“可维护性底盘”补起来

落地范围：

- 统一异常结构
- Request ID / Trace ID
- 统一日志格式
- 基本健康检查

验收标准：

- 前后端错误可追踪到一次具体请求
- 常见异常返回结构一致

#### 6. 前端权限守卫与导航治理

目标：

- 不让平台壳继续散乱增长

落地范围：

- 页面级权限守卫
- 菜单渲染规则
- 按钮权限组件
- 403 / 无权限兜底页

验收标准：

- 新增页面接入权限不需要重复写一套判断

### P1：平台能力开始成型

#### 7. 工作流中心

- 审批定义
- 审批实例
- 待办 / 已办
- 动作流转

#### 8. 通知中心

- 站内信
- 邮件
- Webhook
- 用户通知偏好

#### 9. 任务调度中心

- 定时任务
- 异步任务
- 导入导出任务化
- 重试机制

#### 10. 集成中心

- 第三方 API 接入配置
- 凭据管理
- Webhook 管理
- 适配器层

### P2：规模化演进能力

#### 11. 报表中心

- 统一查询接口
- 导出
- Dashboard 数据源

#### 12. 多租户 / 数据权限

- 行级数据权限
- 部门级隔离
- 租户维度预留

#### 13. 模块脚手架生成器

- 后端模块模板
- 前端 feature 模板
- OpenAPI client 联动约定

## 八、按 3 个阶段的演进路线图

### 阶段一：模板升级为平台底座

目标：

- 让当前仓库从“可演示模板”升级为“可持续接业务”的底座

建议周期：

- 2 到 4 周

建议事项：

1. 建立 `modules/`、`platform/`、`features/` 目录骨架
2. 落 IAM / RBAC 最小闭环
3. 落系统管理最小闭环
4. 落审计日志和统一异常 / 日志 / trace
5. 落文件中心最小闭环
6. 前端完成权限守卫、菜单权限、按钮权限治理

阶段完成标志：

- 平台用户和角色体系成型
- 新业务不必再依赖 `is_superuser`
- 新功能可以按模块化方式接入

### 阶段二：平台共享能力补齐

目标：

- 让多个业务模块开始真正共享平台能力，而不是各做各的

建议周期：

- 4 到 8 周

建议事项：

1. 落工作流中心
2. 落通知中心
3. 落任务调度中心
4. 落集成中心
5. 把已有业务模块开始按新结构迁移
6. 沉淀前端通用 CRUD 页面壳、详情页壳、审批流组件

阶段完成标志：

- 新业务可以直接复用审批、通知、附件、任务能力
- 平台共享能力开始明显大于业务重复建设

### 阶段三：走向规模化与产品化

目标：

- 让平台从“可开发多个系统”升级为“可由多个团队长期维护”

建议周期：

- 8 周以上，按业务规模滚动推进

建议事项：

1. 落报表中心
2. 落多租户或数据权限
3. 落模块脚手架生成器
4. 为高负载模块引入缓存、异步化、导出任务化
5. 评估是否需要把个别模块拆成独立服务

阶段完成标志：

- 平台有明确的模块边界、治理边界、扩展边界
- 是否微服务化可以基于真实负载和团队边界决策，而不是预设架构

## 九、推荐的迁移实施原则

### 1）先增量，后迁移

不要一开始移动 `users/items/docs` 全量代码。

正确方式是：

- 新模块按新结构写
- 老模块先保持可运行
- 有业务机会再逐步迁移老模块

### 2）先统一契约，再统一结构

比起先整理目录，更重要的是先统一这些东西：

- 权限模型
- 异常返回模型
- 审计模型
- 文件引用模型
- 路由命名规范
- Query Key 规范

如果这些契约不统一，目录再漂亮也只是换壳。

### 3）保持 OpenAPI 为前后端边界

当前仓库最大的优点之一就是：

- 后端 FastAPI OpenAPI 边界清晰
- 前端有生成 client

这个边界必须保住。后续任何模块化改造都应该坚持：

- 后端接口先稳定
- 再生成 client
- 前端通过 client 调用，而不是散乱手写请求

### 4）模块内聚，跨模块通过明确接口协作

比如：

- `workflow` 不直接读业务页面状态
- `notification` 不直接耦合某个具体业务表
- `file` 通过 `business_type + business_id` 建立引用

这样后面拆服务才有基础。

### 5）平台模块优先做“80 分通用能力”

不要一开始就追求极致通用。

例如：

- 文件中心先支持本地存储 + 对象存储适配口
- 通知中心先支持站内信 + 邮件
- 工作流先支持通用审批链，不急着做 BPMN 全能力

先做可复用，再做完美。

## 十、建议的首批改造顺序

如果从今天开始排优先级，我建议这样落：

1. 先补 IAM / RBAC 和前端权限治理
2. 再补系统管理
3. 再补审计日志、异常、日志、trace
4. 再补文件中心
5. 然后开始落工作流、通知、任务调度、集成
6. 最后再推进报表、多租户、脚手架生成

原因很简单：

- 权限、系统管理、审计、文件，是所有业务都会立刻依赖的基础件
- 工作流、通知、任务，是大量中后台业务会高频复用的共享件
- 报表、多租户、生成器，更适合在平台边界稳定后再投入

## 十一、最终可执行建议

如果你的目标是“这个仓库未来承接多个企业业务系统”，那么推荐的路线不是：

- 继续把业务直接堆在当前 `routes/components/services/crud` 下

而是：

1. 用当前仓库继续做基础盘
2. 把它升级成**模块化单体平台**
3. 先补平台底座模块
4. 再让后续业务全部按 `modules + platform/features + shared` 方式进入
5. 等真实复杂度出现后，再决定是否拆服务

这条路的优点是：

- 对当前仓库改动最稳
- 能保留现有 FastAPI + React + OpenAPI client 的优势
- 不会太早为微服务付出复杂度成本
- 后续真要拆，也有清晰的模块边界可拆

## 十二、后端目录拆分方案（到文件夹和职责级）

这一版不是“未来理想图”，而是基于当前仓库现状直接给出的迁移蓝图。

### 1）当前后端目录现状

当前实际结构的核心是：

```text
backend/app/
  api/
    main.py
    deps.py
    dependencies/
    routes/
      login.py
      users.py
      items.py
      docs.py
      utils.py
      private.py
  core/
    config.py
    db.py
    security.py
  crud/
    user.py
    item.py
  models/
    base.py
    user.py
    item.py
  schemas/
    security.py
    user.py
    item.py
    docs.py
  services/
    auth.py
    user.py
    item.py
    docs.py
```

这个结构在模板阶段没有问题，但继续叠加业务后，问题会集中在：

- `services/` 会成为全局业务垃圾桶
- `crud/` 只适合简单原子操作，不适合平台模块横向增长
- `models/`、`schemas/` 会不断混入不相关领域对象
- `api/routes/` 会变成超长平铺目录

### 2）建议目标目录

建议目标结构如下：

```text
backend/app/
  api/
    main.py
    deps.py
    dependencies/
      auth.py
      database.py
  core/
    config.py
    db.py
    security.py
    exceptions.py
    logging.py
    observability.py
    pagination.py
  infra/
    db/
      session.py
      mixins.py
    cache/
      redis.py
    storage/
      local.py
      s3.py
    mail/
      sender.py
    tasks/
      runner.py
    integrations/
      base.py
  modules/
    iam/
      api.py
      service.py
      repository.py
      models.py
      schemas.py
      permissions.py
    system/
      api.py
      service.py
      repository.py
      models.py
      schemas.py
    audit/
      api.py
      service.py
      repository.py
      models.py
      schemas.py
    file/
      api.py
      service.py
      repository.py
      models.py
      schemas.py
      storage.py
    workflow/
      api.py
      service.py
      repository.py
      models.py
      schemas.py
    notification/
      api.py
      service.py
      repository.py
      models.py
      schemas.py
    reporting/
      api.py
      service.py
      repository.py
      schemas.py
    users/
      api.py
      service.py
      repository.py
      models.py
      schemas.py
    items/
      api.py
      service.py
      repository.py
      models.py
      schemas.py
    docs/
      api.py
      service.py
      schemas.py
  main.py
```

### 3）后端目录职责表

| 目录 | 职责 | 放什么 | 不放什么 |
| --- | --- | --- | --- |
| `api/` | 全局 API 装配层 | 路由注册、全局依赖、API 聚合 | 具体业务实现 |
| `core/` | 框架基础设施 | 配置、数据库、认证、安全、异常、日志 | 业务规则 |
| `infra/` | 技术适配层 | 存储、缓存、邮件、Webhook、任务执行器 | 直接面向页面的业务逻辑 |
| `modules/` | 业务与平台模块主承载区 | 模块内 API、服务、仓储、模型、Schema | 跨所有模块的杂项工具 |
| `modules/*/api.py` | 模块对外 HTTP 接口 | APIRouter、依赖声明、输入输出绑定 | 复杂业务逻辑 |
| `modules/*/service.py` | 模块业务逻辑 | 规则编排、事务边界、权限协同 | SQL 细节散落 |
| `modules/*/repository.py` | 模块数据访问 | 查询、持久化、分页封装 | HTTP 细节 |
| `modules/*/models.py` | 模块 ORM 模型 | SQLModel 实体 | Response DTO |
| `modules/*/schemas.py` | 模块接口契约 | 请求、响应、过滤器、分页结构 | ORM 关系定义 |

### 4）当前目录到目标目录映射

| 当前路径 | 目标路径 | 说明 |
| --- | --- | --- |
| `backend/app/api/routes/users.py` | `backend/app/modules/users/api.py` | 先迁路由壳，内部仍可调用旧服务 |
| `backend/app/services/user.py` | `backend/app/modules/users/service.py` | 用户业务逻辑迁入模块 |
| `backend/app/crud/user.py` | `backend/app/modules/users/repository.py` | 原子数据访问改名为 repository |
| `backend/app/models/user.py` | `backend/app/modules/users/models.py` | 用户模型就近归属 |
| `backend/app/schemas/user.py` | `backend/app/modules/users/schemas.py` | 用户接口契约就近归属 |
| `backend/app/api/routes/items.py` | `backend/app/modules/items/api.py` | Items 模块化 |
| `backend/app/services/item.py` | `backend/app/modules/items/service.py` | Items 业务逻辑迁移 |
| `backend/app/crud/item.py` | `backend/app/modules/items/repository.py` | Items 数据访问迁移 |
| `backend/app/models/item.py` | `backend/app/modules/items/models.py` | Items 模型归属 |
| `backend/app/schemas/item.py` | `backend/app/modules/items/schemas.py` | Items DTO 归属 |
| `backend/app/api/routes/docs.py` | `backend/app/modules/docs/api.py` | 文档接口模块化 |
| `backend/app/services/docs.py` | `backend/app/modules/docs/service.py` | 规则文档读取逻辑归入 docs 模块 |
| `backend/app/schemas/docs.py` | `backend/app/modules/docs/schemas.py` | 文档接口契约归入 docs 模块 |
| `backend/app/services/auth.py` | `backend/app/modules/iam/service.py` 或 `core/security.py` | 取决于是业务鉴权还是通用安全能力 |

### 5）后端建议新增模块优先级

第一批建议新建但不必立即全部实现的目录：

```text
backend/app/modules/
  iam/
  system/
  audit/
  file/
  users/
  items/
  docs/
```

原因：

- `iam` 是替换 `is_superuser` 的前提
- `system` 是管理后台基础域
- `audit` 是平台治理基础域
- `file` 是高复用基础域
- `users/items/docs` 是现有模块的就地演进样板

### 6）后端模块内部建议职责

#### `modules/iam`

- `api.py`：登录、刷新 token、当前用户权限查询、角色权限管理接口
- `service.py`：鉴权流程、角色授权流程、权限校验编排
- `repository.py`：用户角色、角色权限、权限点等查询封装
- `models.py`：`Role`、`Permission`、`UserRole`、`RolePermission`
- `schemas.py`：登录请求、权限返回、角色管理 DTO
- `permissions.py`：模块级权限判断工具

#### `modules/system`

- `api.py`：字典、参数、部门、岗位、菜单管理接口
- `service.py`：系统配置类业务逻辑
- `repository.py`：参数、字典、组织树查询
- `models.py`：`Department`、`DictType`、`DictItem`、`SystemParam`
- `schemas.py`：树形结构、下拉字典、参数更新 DTO

#### `modules/audit`

- `api.py`：日志查询接口
- `service.py`：操作日志记录、审计聚合查询
- `repository.py`：日志写入、日志检索
- `models.py`：`OperationLog`、`AuditLog`
- `schemas.py`：日志查询条件、日志明细返回

#### `modules/file`

- `api.py`：上传、下载、预览、列表接口
- `service.py`：文件元数据处理、业务对象绑定
- `repository.py`：文件元数据持久化
- `models.py`：`FileObject`、`FileRelation`
- `schemas.py`：上传结果、文件列表、预览 DTO
- `storage.py`：模块级存储策略封装

### 7）后端路由注册建议

当前 `backend/app/api/main.py` 还是直接：

- `include_router(login.router)`
- `include_router(users.router)`
- `include_router(docs.router)`
- `include_router(items.router)`

建议逐步演进为：

```python
from app.modules.users.api import router as users_router
from app.modules.items.api import router as items_router
from app.modules.docs.api import router as docs_router
from app.modules.iam.api import router as iam_router
from app.modules.system.api import router as system_router

api_router = APIRouter()
api_router.include_router(iam_router)
api_router.include_router(users_router)
api_router.include_router(items_router)
api_router.include_router(docs_router)
api_router.include_router(system_router)
```

过渡期允许老 routes 和新 modules 并存，但新增模块不再进入 `api/routes/` 平铺目录。

### 8）后端迁移顺序建议

建议顺序：

1. 先建 `modules/iam`、`modules/system`、`modules/audit`、`modules/file`
2. 再把 `users` 迁成样板模块
3. 再把 `items` 迁成样板模块
4. `docs` 最后迁，因为它复杂度最低，可作为轻量模块示例

理由：

- `users` 是权限体系的直接依赖，先迁最有示范价值
- `items` 是标准 CRUD，适合作为通用业务模块模板
- `docs` 无数据库写入，适合最后收尾

## 十三、前端目录拆分方案（到 feature、页面和组件级）

### 1）当前前端目录现状

当前实际核心结构：

```text
frontend/src/
  routes/
    __root.tsx
    _layout.tsx
    login.tsx
    signup.tsx
    recover-password.tsx
    reset-password.tsx
    _layout/
      index.tsx
      items.tsx
      admin.tsx
      rules.tsx
      settings.tsx
  components/
    Admin/
    Items/
    Pending/
    Sidebar/
    UserSettings/
    Common/
    ui/
  hooks/
    useAuth.ts
    useMobile.ts
    useCopyToClipboard.ts
    useCustomToast.ts
  client/
```

当前已经有一些 feature 雏形，比如 `Admin`、`Items`、`UserSettings`，但它们仍然是按组件目录堆放，不是按 feature 组织。

### 2）建议目标目录

```text
frontend/src/
  app/
    layout/
      AppLayout.tsx
      AppHeader.tsx
      AppFooter.tsx
    navigation/
      AppSidebar.tsx
      menu-config.ts
      permission-menu.ts
    providers/
      AppProviders.tsx
      AuthProvider.tsx
      ThemeProvider.tsx
    router/
      guards.ts
      route-meta.ts
  platform/
    auth/
      pages/
      components/
      hooks/
      guards/
      query/
    system/
      users/
        pages/
        components/
        query/
        forms/
      roles/
      departments/
      dictionaries/
      params/
    docs/
      rules/
        pages/
        components/
        query/
    audit/
      pages/
      components/
      query/
    file/
      pages/
      components/
      query/
  features/
    items/
      pages/
      components/
      query/
      forms/
      utils/
    dashboard/
      pages/
      components/
  shared/
    components/
      table/
      feedback/
      status/
    hooks/
    utils/
    permissions/
    types/
  client/
  routes/
```

### 3）前端目录职责表

| 目录 | 职责 | 放什么 | 不放什么 |
| --- | --- | --- | --- |
| `app/` | 应用壳层 | Layout、Header、Sidebar、Provider、路由守卫 | 业务页面实现 |
| `platform/` | 平台通用能力层 | 权限、系统管理、规则中心、文件中心、审计中心 | 某个垂直业务专属逻辑 |
| `features/` | 业务功能层 | `items`、未来的 `customer/sales/inventory` | 全局通用基础能力 |
| `shared/` | 纯复用层 | 通用表格、空态、错误态、权限组件、hooks、utils | 带业务语义的页面逻辑 |
| `routes/` | TanStack Router 文件路由层 | 页面挂载、search 参数绑定、轻量 beforeLoad | 大量页面业务逻辑 |
| `client/` | 生成代码层 | OpenAPI 生成结果 | 手工修改 |

### 4）当前页面到目标 feature 映射

| 当前路由文件 | 目标归属 | 说明 |
| --- | --- | --- |
| `frontend/src/routes/_layout.tsx` | `frontend/src/app/layout/AppLayout.tsx` + `app/router/guards.ts` | 现有登录态守卫和壳布局拆开 |
| `frontend/src/routes/_layout/index.tsx` | `frontend/src/features/dashboard/pages/DashboardPage.tsx` | 首页仪表板页 |
| `frontend/src/routes/_layout/items.tsx` | `frontend/src/features/items/pages/ItemsPage.tsx` | 标准业务 feature |
| `frontend/src/routes/_layout/admin.tsx` | `frontend/src/platform/system/users/pages/UsersAdminPage.tsx` | 当前 admin 实际上是系统用户管理 |
| `frontend/src/routes/_layout/rules.tsx` | `frontend/src/platform/docs/rules/pages/RulesPage.tsx` | 规则中心归平台层 |
| `frontend/src/routes/_layout/settings.tsx` | `frontend/src/platform/auth/pages/UserSettingsPage.tsx` | 用户设置属于平台认证域 |
| `frontend/src/routes/login.tsx` | `frontend/src/platform/auth/pages/LoginPage.tsx` | 认证页归平台 |
| `frontend/src/routes/signup.tsx` | `frontend/src/platform/auth/pages/SignupPage.tsx` | 注册页归平台 |
| `frontend/src/routes/recover-password.tsx` | `frontend/src/platform/auth/pages/RecoverPasswordPage.tsx` | 密码找回归平台 |
| `frontend/src/routes/reset-password.tsx` | `frontend/src/platform/auth/pages/ResetPasswordPage.tsx` | 重置密码归平台 |

### 5）当前组件到目标归属映射

#### `components/Sidebar`

| 当前组件 | 目标位置 | 说明 |
| --- | --- | --- |
| `components/Sidebar/AppSidebar.tsx` | `app/navigation/AppSidebar.tsx` | 侧边栏属于应用壳 |
| `components/Sidebar/Main.tsx` | `app/navigation/AppMenu.tsx` | 主菜单展示 |
| `components/Sidebar/User.tsx` | `app/navigation/AppSidebarUser.tsx` | 当前用户区块 |

#### `components/Common`

| 当前组件 | 目标位置 | 说明 |
| --- | --- | --- |
| `components/Common/Footer.tsx` | `app/layout/AppFooter.tsx` | 应用壳页脚 |
| `components/Common/AuthLayout.tsx` | `platform/auth/components/AuthLayout.tsx` | 认证页面专用布局 |
| `components/Common/DataTable.tsx` | `shared/components/table/DataTable.tsx` | 通用表格能力 |
| `components/Common/ErrorComponent.tsx` | `shared/components/feedback/ErrorState.tsx` | 通用错误态 |
| `components/Common/Appearance.tsx` | `app/providers` 或 `app/navigation` | 主题切换属于壳层 |
| `components/Common/Logo.tsx` | `shared/components/brand/Logo.tsx` | 品牌组件 |
| `components/Common/NotFound.tsx` | `shared/components/feedback/NotFound.tsx` | 通用 404 |

#### `components/Admin`

| 当前组件 | 目标位置 | 说明 |
| --- | --- | --- |
| `components/Admin/AddUser.tsx` | `platform/system/users/components/AddUserDialog.tsx` | 用户管理功能 |
| `components/Admin/EditUser.tsx` | `platform/system/users/components/EditUserDialog.tsx` | 用户管理功能 |
| `components/Admin/DeleteUser.tsx` | `platform/system/users/components/DeleteUserDialog.tsx` | 用户管理功能 |
| `components/Admin/UserActionsMenu.tsx` | `platform/system/users/components/UserActionsMenu.tsx` | 用户管理功能 |
| `components/Admin/columns.tsx` | `platform/system/users/components/user-columns.tsx` | 用户表格列定义 |

#### `components/Items`

| 当前组件 | 目标位置 | 说明 |
| --- | --- | --- |
| `components/Items/AddItem.tsx` | `features/items/components/AddItemDialog.tsx` | Items feature 组件 |
| `components/Items/EditItem.tsx` | `features/items/components/EditItemDialog.tsx` | Items feature 组件 |
| `components/Items/DeleteItem.tsx` | `features/items/components/DeleteItemDialog.tsx` | Items feature 组件 |
| `components/Items/ItemActionsMenu.tsx` | `features/items/components/ItemActionsMenu.tsx` | Items feature 组件 |
| `components/Items/columns.tsx` | `features/items/components/item-columns.tsx` | Items 表格列定义 |

#### `components/UserSettings`

| 当前组件 | 目标位置 | 说明 |
| --- | --- | --- |
| `components/UserSettings/UserInformation.tsx` | `platform/auth/components/UserProfileCard.tsx` | 当前用户资料 |
| `components/UserSettings/ChangePassword.tsx` | `platform/auth/components/ChangePasswordForm.tsx` | 认证域组件 |
| `components/UserSettings/DeleteAccount.tsx` | `platform/auth/components/DeleteAccountDialog.tsx` | 认证域组件 |
| `components/UserSettings/DeleteConfirmation.tsx` | `platform/auth/components/DeleteAccountConfirm.tsx` | 认证域组件 |

#### `components/Pending`

| 当前组件 | 目标位置 | 说明 |
| --- | --- | --- |
| `components/Pending/PendingUsers.tsx` | `platform/system/users/components/UsersTableSkeleton.tsx` | 用户页专属骨架屏 |
| `components/Pending/PendingItems.tsx` | `features/items/components/ItemsTableSkeleton.tsx` | Items 页专属骨架屏 |

### 6）当前 hooks 到目标归属映射

| 当前 Hook | 目标位置 | 说明 |
| --- | --- | --- |
| `hooks/useAuth.ts` | `platform/auth/hooks/useAuth.ts` | 认证域 Hook |
| `hooks/useMobile.ts` | `shared/hooks/useMobile.ts` | 通用设备判断 |
| `hooks/useCopyToClipboard.ts` | `shared/hooks/useCopyToClipboard.ts` | 通用 Hook |
| `hooks/useCustomToast.ts` | `shared/hooks/useCustomToast.ts` | 通用 UI Hook |

### 7）前端首批 feature 拆分建议

#### 第一批：立刻可拆

- `app/layout`
- `app/navigation`
- `platform/auth`
- `platform/system/users`
- `platform/docs/rules`
- `features/items`
- `shared/components/table`
- `shared/components/feedback`

这批是当前代码里已经有明显归属的内容，拆分成本低、收益高。

#### 第二批：随着 IAM / 系统管理推进再补

- `platform/system/roles`
- `platform/system/departments`
- `platform/system/dictionaries`
- `platform/system/params`
- `shared/permissions`
- `app/router/guards`

#### 第三批：平台化之后扩展

- `platform/file`
- `platform/audit`
- `platform/workflow`
- `platform/notification`
- `platform/reporting`

### 8）前端路由层建议

当前 `routes/_layout/admin.tsx`、`routes/_layout/items.tsx` 这类文件里，既有路由定义，也有完整页面实现、查询逻辑、权限判断。

后续建议把它们压薄成：

```tsx
import { createFileRoute } from "@tanstack/react-router";

import { UsersAdminPage } from "@/platform/system/users/pages/UsersAdminPage";

export const Route = createFileRoute("/_layout/admin")({
  component: UsersAdminPage,
});
```

也就是：

- `routes/` 只放路由壳
- 页面实现搬到 `platform/*/pages` 或 `features/*/pages`
- 查询逻辑搬到 `query/`
- 页面专用组件搬到 `components/`

### 9）前端建议的菜单与权限治理

当前侧边栏 `AppSidebar.tsx` 还是直接通过：

- `currentUser?.is_superuser`

决定是否显示 `Admin` 菜单。

后续建议替换为：

- `menu-config.ts` 定义所有菜单
- `permission-menu.ts` 根据权限点过滤
- `guards.ts` 做页面级访问控制
- `shared/permissions` 提供按钮级控制组件

也就是从：

- “是否超管”

升级为：

- “当前用户具备哪些权限点”
- “菜单需要哪些权限点”
- “页面需要哪些权限点”
- “按钮需要哪些权限点”

### 10）前端拆分落地顺序

建议顺序：

1. 先拆 `app/layout` 与 `app/navigation`
2. 再拆 `platform/auth`
3. 再拆 `platform/system/users`
4. 再拆 `features/items`
5. 然后统一 `shared/table`、`shared/feedback`、`shared/hooks`
6. 最后再上 `roles/departments/dictionaries/params`

这样可以先把壳、认证、用户管理、标准 CRUD 这些最容易复用的骨架稳定下来。

## 十四、企业脚手架 1.0 实施计划

这一节不是架构愿景，而是建议你真正执行时的落地顺序。目标是：

- 每个迭代都能交付可运行结果
- 每个迭代都尽量避免大爆炸式重构
- 每个迭代都让后续模块更容易进入平台

建议按 5 个批次推进，而不是把所有能力混在一个超长改造里。

### 批次 0：结构骨架与治理基线

#### 目标

- 建好后续平台化演进的最小骨架
- 不先碰复杂业务逻辑
- 先把“目录、守卫、日志、异常”这类治理底座收口

#### 后端目录改动

新增建议目录：

```text
backend/app/core/
  exceptions.py
  logging.py
  observability.py
  pagination.py

backend/app/infra/
  db/
    session.py
    mixins.py

backend/app/modules/
  iam/
  system/
  audit/
  file/
```

本批次不要求全部实现业务，只要求先建立目录和注册机制。

#### 前端目录改动

新增建议目录：

```text
frontend/src/app/
  layout/
  navigation/
  providers/
  router/

frontend/src/platform/
  auth/
  system/
  docs/

frontend/src/shared/
  components/
  hooks/
  utils/
  permissions/
```

#### 后端实施事项

1. 新增统一异常返回模型
2. 新增 Request ID / Trace ID 中间件
3. 新增统一日志格式
4. 改 `api/main.py`，支持未来从 `modules/*/api.py` 注册路由
5. 增加模块化目录骨架，但先不强制迁移老代码

#### 前端实施事项

1. 抽出 `AppLayout`、`AppSidebar`、`AppFooter`
2. 抽出基础认证守卫
3. 抽出菜单配置文件
4. 抽出通用 `shared` 空态、错误态、表格组件归属

#### 涉及的现有文件

- `backend/app/api/main.py`
- `backend/app/core/config.py`
- `backend/app/main.py`
- `frontend/src/routes/_layout.tsx`
- `frontend/src/components/Sidebar/AppSidebar.tsx`
- `frontend/src/components/Common/Footer.tsx`

#### 建议测试

后端：

- 异常返回结构测试
- Request ID 注入测试
- 路由注册回归测试

前端：

- 登录态守卫测试
- 菜单渲染测试
- 基础布局渲染测试

#### 验收标准

- 后续新增模块已经有明确落点
- 应用壳与页面实现开始解耦
- 后端错误和请求追踪有统一入口

### 批次 1：IAM / RBAC 最小闭环

#### 目标

- 把权限模型从 `is_superuser` 升级为可扩展的 RBAC
- 让后续页面和接口都能按权限点接入

#### 后端目录改动

重点落地：

```text
backend/app/modules/iam/
  api.py
  service.py
  repository.py
  models.py
  schemas.py
  permissions.py
```

#### 前端目录改动

重点落地：

```text
frontend/src/platform/auth/
  hooks/
  guards/
  query/
  components/

frontend/src/shared/permissions/
  CanAccess.tsx
  has-permission.ts
```

#### 后端实施事项

1. 设计 `Role`、`Permission`、`UserRole`、`RolePermission`
2. 增加当前用户权限集合接口
3. 增加角色管理接口
4. 增加权限校验依赖
5. 逐步把 `users` 的超管判断替换为权限点判断

#### 前端实施事项

1. 增加当前用户权限查询与缓存
2. 增加页面级守卫
3. 增加菜单权限过滤
4. 增加按钮权限组件
5. 先把现有 `Admin` 页接到权限点体系上

#### 建议新增接口

- `GET /api/v1/iam/me/permissions`
- `GET /api/v1/iam/roles`
- `POST /api/v1/iam/roles`
- `PATCH /api/v1/iam/roles/{id}`
- `POST /api/v1/iam/roles/{id}/permissions`

#### 涉及的现有文件

- `backend/app/api/deps.py`
- `backend/app/api/routes/users.py`
- `backend/app/services/auth.py`
- `frontend/src/hooks/useAuth.ts`
- `frontend/src/components/Sidebar/AppSidebar.tsx`
- `frontend/src/routes/_layout/admin.tsx`

#### 建议测试

后端：

- 权限点生效测试
- 非授权用户访问拒绝测试
- 角色权限绑定测试

前端：

- 菜单过滤测试
- 无权限页面跳转测试
- 按钮隐藏/禁用测试

#### 验收标准

- 不再依赖 `is_superuser` 作为唯一授权模型
- 用户可通过角色获得页面和接口访问能力
- 新页面可直接接权限守卫

### 批次 2：系统管理最小闭环

#### 目标

- 让平台具备最基本的“系统后台”能力
- 为后续业务模块提供字典、参数、组织结构等通用数据源

#### 后端目录改动

重点落地：

```text
backend/app/modules/system/
  api.py
  service.py
  repository.py
  models.py
  schemas.py
```

#### 前端目录改动

重点落地：

```text
frontend/src/platform/system/
  users/
  roles/
  departments/
  dictionaries/
  params/
```

#### 后端实施事项

1. 用户管理从临时 `Admin` 页语义升级为 `system/users`
2. 增加角色管理
3. 增加部门管理
4. 增加字典管理
5. 增加系统参数管理

#### 前端实施事项

1. 把 `Admin` 页面迁为 `platform/system/users`
2. 新增角色管理页
3. 新增部门管理页
4. 新增字典管理页
5. 新增参数管理页

#### 建议新增页面

- `/system/users`
- `/system/roles`
- `/system/departments`
- `/system/dictionaries`
- `/system/params`

#### 涉及的现有文件

- `frontend/src/routes/_layout/admin.tsx`
- `frontend/src/components/Admin/*`
- `backend/app/api/routes/users.py`
- `backend/app/services/user.py`

#### 建议测试

后端：

- 用户、角色、部门、字典、参数 CRUD 测试
- 权限校验测试

前端：

- 管理页列表加载测试
- 弹窗表单提交流程测试
- 权限场景测试

#### 验收标准

- 当前 `Admin` 从“模板管理员页面”升级为“系统管理模块”
- 字典和参数可被后续业务直接复用
- 角色和部门开始形成平台基础主数据

### 批次 3：审计日志、文件中心、统一治理能力

#### 目标

- 补齐企业底盘中最容易被后续所有模块依赖的共享能力

#### 后端目录改动

重点落地：

```text
backend/app/modules/audit/
  api.py
  service.py
  repository.py
  models.py
  schemas.py

backend/app/modules/file/
  api.py
  service.py
  repository.py
  models.py
  schemas.py
  storage.py
```

#### 前端目录改动

重点落地：

```text
frontend/src/platform/audit/
  pages/
  components/
  query/

frontend/src/platform/file/
  pages/
  components/
  query/
```

#### 后端实施事项

1. 关键写操作统一写审计日志
2. 建立文件元数据表与业务关联表
3. 提供上传、下载、列表、删除接口
4. 提供日志查询接口
5. 把异常、日志、trace 体系真正接到这些模块上

#### 前端实施事项

1. 新增日志查询页
2. 新增上传组件
3. 新增文件列表与预览入口
4. 抽出通用附件选择/上传能力

#### 建议新增接口

- `GET /api/v1/audit/logs`
- `POST /api/v1/files/upload`
- `GET /api/v1/files`
- `GET /api/v1/files/{id}`
- `DELETE /api/v1/files/{id}`

#### 建议新增页面

- `/audit/logs`
- `/files`

#### 建议测试

后端：

- 审计写入测试
- 文件上传下载测试
- 业务对象文件绑定测试

前端：

- 上传流程测试
- 文件列表加载测试
- 日志页查询过滤测试

#### 验收标准

- 关键操作有统一日志
- 附件类需求不再需要业务模块重复造轮子
- 平台治理能力开始具备复用价值

### 批次 4：把现有模块迁成样板模块

#### 目标

- 用当前已有模块做“模块化迁移样板”
- 为后续任何业务模块进入平台建立参考模板

#### 后端目录改动

迁移建议顺序：

1. `users`
2. `items`
3. `docs`

目标迁移到：

```text
backend/app/modules/users/
backend/app/modules/items/
backend/app/modules/docs/
```

#### 前端目录改动

迁移建议顺序：

1. `platform/system/users`
2. `features/items`
3. `platform/docs/rules`

#### 后端实施事项

1. 把 `users` 路由、服务、数据访问迁入模块目录
2. 把 `items` 路由、服务、数据访问迁入模块目录
3. 把 `docs` 路由和服务迁入模块目录
4. 清理旧 `services/crud/routes` 的重复实现

#### 前端实施事项

1. 把 `Items` 相关页面和组件迁到 `features/items`
2. 把 `Admin` 迁为 `platform/system/users`
3. 把 `Rules` 迁为 `platform/docs/rules`
4. 让 `routes/*.tsx` 变成轻量路由壳

#### 涉及的现有文件

- `backend/app/api/routes/users.py`
- `backend/app/api/routes/items.py`
- `backend/app/api/routes/docs.py`
- `backend/app/services/user.py`
- `backend/app/services/item.py`
- `backend/app/services/docs.py`
- `backend/app/crud/user.py`
- `backend/app/crud/item.py`
- `frontend/src/routes/_layout/admin.tsx`
- `frontend/src/routes/_layout/items.tsx`
- `frontend/src/routes/_layout/rules.tsx`
- `frontend/src/components/Admin/*`
- `frontend/src/components/Items/*`

#### 建议测试

后端：

- 迁移前后接口契约回归测试
- OpenAPI 变更检查

前端：

- 页面加载回归测试
- Query 缓存失效回归测试
- 菜单导航回归测试

#### 验收标准

- 至少有 2 到 3 个模块完整跑通新结构
- 团队后续开发有明确模块样板可参考
- 老目录可以开始冻结，不再接新业务

## 十五、每个批次建议输出物

为了避免“改了很多，但没有沉淀”，每个批次建议至少产出以下文档和产物。

### 批次 0 输出物

- 目录骨架代码
- 统一异常规范文档
- 前端壳层拆分说明

### 批次 1 输出物

- IAM / RBAC 接口文档
- 权限点命名规范
- 菜单权限映射规则

### 批次 2 输出物

- 系统管理模块接口文档
- 字典 / 参数使用规范
- 组织与角色边界说明

### 批次 3 输出物

- 审计日志模型说明
- 文件中心引用规范
- 错误与 trace 排障说明

### 批次 4 输出物

- 模块迁移样板说明
- 新模块创建模板
- 老目录冻结规则

## 十六、建议的验收方式

### 1）不要按“代码量”验收

应该按下面这些结果验收：

- 是否形成了稳定模块边界
- 是否减少了新功能接入成本
- 是否减少了权限、日志、文件的重复建设
- 是否让前后端契约更稳定

### 2）每个批次都做一次契约回归

重点检查：

- OpenAPI 是否稳定
- client 是否顺利生成
- 前端页面是否仍然能跑通
- 权限与菜单是否出现回退

### 3）每个批次都保留迁移样板

不要只完成功能，还要留下：

- 一个标准模块目录
- 一个标准页面 feature
- 一套标准 query / form / table 组织方式

否则后续团队还是会回到平铺式开发。

## 十七、推荐的执行顺序结论

如果从现在开始真正实施，我建议你按这个顺序推进：

1. 批次 0：先搭平台骨架和治理底盘
2. 批次 1：先把 IAM / RBAC 做成最小闭环
3. 批次 2：把系统管理模块补齐
4. 批次 3：补审计日志、文件中心、统一治理能力
5. 批次 4：再把现有 `users/items/docs` 迁成标准样板模块

这样做的好处是：

- 不会先陷入大规模搬目录
- 不会先做一堆“看起来很平台”的空壳
- 每一批都有明确业务价值
- 每一批都能为下一批降低成本
