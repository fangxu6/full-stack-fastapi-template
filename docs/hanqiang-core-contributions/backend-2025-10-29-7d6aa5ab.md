# RABC+字段解释器实现

> 来源总览：[hanqiang 通用与核心提交整理](../hanqiang-core-contributions.md)  
> 复用定位：将稳定字段名与面向用户的表头解耦，并以版本化、幂等初始化接入 RBAC 功能域。

## 提交信息

- 仓库：`JSECommon`
- SHA：`7d6aa5ab`
- 日期：`2025-10-29`
- 分类：后端：权限、运行时与基础能力
- 原始主题：RABC+字段解释器实现

## 该提交补全的能力

在 `c2fe51b1` 建立功能 RBAC 后，本提交补充了两项平台运行能力：

1. 字段解释器（当前实现名称为表头翻译）：按功能或数据表把稳定的内部字段名映射为显示/导出表头，并支持反向映射。
2. RBAC 配置初始化的可靠性：增加版本记录、幂等初始化处理和多 worker 启动锁，避免多个进程同时写入默认数据。

“字段解释器”在这里仅转换键名，并不负责类型转换、格式化、单位换算或敏感字段脱敏。其它项目应将这些职责拆开，避免把所有展示逻辑塞进一张字段映射表。

## 字段映射的可迁移契约

```text
业务 DTO / 导出行：{"UserCode": "U001", "IsEnabled": true}
             │
             ├─ FeatureID 优先，或 TableName 作为映射作用域
             ▼
HeaderTranslation：{"UserCode": "用户编号", "IsEnabled": "是否启用"}
             ▼
展示 / 导出行：{"用户编号": "U001", "是否启用": true}
```

当前记录模型 `Common_Feature_HeaderTrans` 的核心字段为：

| 字段 | 语义 | 复用建议 |
| --- | --- | --- |
| `FeatureID` | 映射所属的功能域 | 用稳定 UUID/code 关联到功能注册表；同一物理表在不同业务场景可有不同表头。 |
| `TableName` | 物理或逻辑数据表名 | 可替换为资源名/DTO 名；不要要求前端暴露真实数据库表名。 |
| `FieldName` | 内部字段键 | 保持稳定、机器可读，不随多语言或文案改动。 |
| `HeaderName` | 展示表头 | 面向用户；多语言项目建议改为 i18n key，而非直接存某一种语言。 |
| `IsDeleted` | 生命周期 | 映射读取必须忽略已删除记录。 |

当前唯一约束是 `(FeatureID, FieldName)`。若目标项目允许同一功能下同字段按版本、地区或导出模板不同，应显式加入 scope/version/locale，而不是依赖查询顺序覆盖。

## 当前接口与服务行为

`HeaderTransService` 提供以下稳定的抽象：

| 操作 | 输入 | 输出与优先级 |
| --- | --- | --- |
| `get_feature_mapping` | `feature_id` | `{field_name: header_name}`。 |
| `get_table_mapping` | `table_name` | `{field_name: header_name}`。 |
| `apply_header_translation` | `data_list` + `feature_id` 或 `table_name` | 逐行替换键名；同时提供两者时以 `feature_id` 为准。 |
| `get_reverse_mapping` | 同上 | `{header_name: field_name}`，用于导入或前端回传。 |

HTTP 接口位于 `app/api/v1/routes/header_translations.py`：

- `GET /header-translations/feature/{feature_id}/mapping`
- `GET /header-translations/table/{table_name}/mapping`
- `GET /header-translations/all-mappings?group_by=feature|table`
- `POST /header-translations/translate`
- `GET /header-translations/reverse-mapping`

`POST /translate` 要求 `table_name` 或 `feature_id` 至少一个非空；没有映射的字段保留原键。该“保留原键”策略适合渐进接入，但导出模板需要字段完全受控时，应额外启用白名单校验并在缺失映射时失败。

## 使用方式

### 导出

1. 业务服务先产生稳定字段名的 DTO，不在业务查询中硬编码中文列名。
2. 选择功能域或逻辑资源作为映射作用域。
3. 调用 `apply_header_translation` 后交给 CSV/XLSX 生成器。
4. 以目标模板顺序输出列；映射服务只负责名称，不负责列顺序。

### 导入

1. 获取或加载反向映射，将用户表头还原为内部字段名。
2. 检测同名表头映射冲突、必填字段缺失和未知表头。
3. 再进入 DTO 校验、类型解析和业务写入。

当前 `get_reverse_mapping` 直接反转字典；如果两个字段映射到同一表头，后者会覆盖前者。因此迁移时必须在写入映射配置时校验“同一作用域内 HeaderName 唯一”。

## 配置初始化与并发控制

本提交修改了 `RBACInitService`、数据库启动流程和 `DBLock`：通过配置版本判断是否同步功能/表头映射，并用 MySQL `GET_LOCK` 避免多 worker 同时初始化种子数据。

推荐在其它项目中采用以下流程：

1. 用正规迁移创建表和索引，启动程序不承担生产 DDL。
2. 将功能与字段映射清单和版本号放入版本库，例如 JSON、YAML 或数据迁移。
3. 用单独的部署 job 或带租约的启动任务执行幂等 upsert；完成后写入版本记录。
4. 锁实现通过接口适配目标基础设施：MySQL 可用 `GET_LOCK`，PostgreSQL 可用 advisory lock，Kubernetes 可用 Job/Lease。
5. 初始化失败必须回滚并报告，不要把“任何异常都继续启动”当作成功。

历史实现中的 `DBLock` 依赖 MySQL 函数，不能原样复制到 PostgreSQL、SQLite 或无共享数据库的部署拓扑。锁范围应覆盖一次完整的初始化事务，而不是只包住单条插入。

## 与 RBAC 的边界

- `FeatureID` 将映射绑定到功能域，但字段映射本身不授予任何访问权限；接口仍需认证和授权。
- `app/api/v1/routes/permissions.py` 使用的是兼容的静态 `PermissionDefinitions` 树，字段映射的权威关联对象是数据库中的 `Common_Feature`。
- 数据脱敏、字段可见性和列级授权应在生成 DTO 前处理；映射表不能防止敏感字段被导出。

## CodeGraph 复核路径

| 层次 | 当前实现 | 追踪结论 |
| --- | --- | --- |
| 数据契约 | `app/schemas/header_translations.py` | 请求包含 `data`、可选 `table_name`、可选 `feature_id`；响应返回翻译后的记录集合。 |
| 业务服务 | `app/services/header_trans_service.py` | 将 CRUD 映射转换成正向、反向和批量行翻译操作。 |
| 数据访问 | `app/crud/crud_header_trans.py`、`app/models/common_feature_header_trans.py` | 所有读取过滤 `IsDeleted=0`，支持按功能或表分组。 |
| API 边界 | `app/api/v1/routes/header_translations.py` | 显式检查至少一个作用域并将业务异常转换为 400。 |
| 配置初始化 | `app/services/rbac_init_service.py` | 当前包含版本表保障、功能配置同步和 `init_header_translations`。 |

## 迁移验收清单

- 同一个输入 DTO 在指定功能域后得到确定且可重复的表头集合。
- 缺失映射按产品策略保留原键或拒绝导出，行为有自动化测试覆盖。
- 映射配置拒绝重复的 `(scope, field)` 和 `HeaderName` 冲突。
- 导入时反向映射后再做 DTO 校验，不能直接信任用户上传的显示列名。
- 多实例同时启动时，只会有一个实例执行初始化；重复部署不会创建重复数据。

## Git 复核

```bash
git -C backend/JSECommon show --stat --oneline 7d6aa5ab
git -C backend/JSECommon show 7d6aa5ab -- app/core/db_lock.py app/services/rbac_init_service.py
```
