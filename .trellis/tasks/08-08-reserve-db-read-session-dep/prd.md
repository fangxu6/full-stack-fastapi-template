# 预留主从数据库读写依赖

## Goal

在不部署 PostgreSQL 复制基础设施的前提下，为应用预留明确的主库写入和读库查询边界。未配置从库时，所有行为必须保持当前主库行为。

## Requirements

### R1. 保持现有主库事务语义

- `SessionDep` 继续访问主库，用于认证、权限和混合场景。
- `WriteSessionDep` 继续访问主库，并拥有请求级 `commit`、`rollback` 和缓存失效处理职责。
- 所有 HTTP 写方法继续使用 `WriteSessionDep`。

### R2. 增加可选读库能力

- 增加可选的 `POSTGRES_READ_REPLICA_SERVER` 配置。
- 未配置从库时，`ReadSessionDep` 必须访问主库，且不得创建额外连接池。
- 配置从库后，`ReadSessionDep` 访问配置的读库。
- 读库连接失败时不自动回退主库。

### R3. 建立首批纯读边界

- scheduler 的任务列表、任务详情和运行记录列表使用 `ReadSessionDep`。
- inventory 的导出、主数据、单据查询、库存余额、台账和联想查询使用 `ReadSessionDep`。
- 认证、权限、用户详情、库存纠正状态和需要强一致的查询继续使用 `SessionDep`。

### R4. 保持外部契约不变

- 不修改数据库模型、Alembic migration、HTTP 请求/响应 schema 或前端客户端。
- 不部署或配置 PostgreSQL 流复制、Patroni、Pgpool-II、云数据库读端点或故障切换。

## Acceptance Criteria

- [ ] 无 `POSTGRES_READ_REPLICA_SERVER` 时，`read_engine` 复用主库 engine。
- [ ] `SessionDep` 和 `WriteSessionDep` 的现有生命周期、共享 Session 和事务测试继续通过。
- [ ] `ReadSessionDep` 使用 function scope，只创建和关闭 Session，不自动提交。
- [ ] 首批 scheduler/inventory 纯读接口显式使用 `ReadSessionDep`。
- [ ] 认证和权限依赖仍使用主库 Session。
- [ ] 配置读库后，读依赖连接读库；读库失败不会静默改走主库。
- [ ] 后端数据库规范记录三种依赖的使用边界和最终一致性约束。
- [ ] focused tests、backend lint 和 type checks 通过。

## Constraints

- 主库和从库复用端口、数据库、用户名和密码，仅主机地址可配置不同。
- 首批读接口接受未来物理复制产生的短暂延迟，不提供写后立即可见保证。
- 本 task 创建后保持 `planning` 状态，不启动 task、不创建分支、不修改应用代码。
