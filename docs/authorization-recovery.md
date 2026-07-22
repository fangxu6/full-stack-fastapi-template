# RBAC 授权恢复手册

当应用启动记录 `RBAC startup invariant failed` 并终止时，说明系统中没有
任何同时满足“用户活跃、已分配、角色活跃”的 `platform_administrator`。
初始化不会自动启用用户或恢复角色分配，必须由经授权的数据库运维人员完成恢复。

## 前提与安全边界

- 停止应用实例，避免恢复期间出现并发的角色变更。
- 先完成当前数据库备份，并在维护记录中登记变更工单与被授权的操作者。
- 选择已完成身份核验的现有账号。不要在应用日志、工单正文或命令历史中写入
  密码、访问令牌或不必要的个人资料。
- 不要删除 IAM 表、内置角色或角色分配记录。恢复只补足一名已核验账号的角色。

## 恢复步骤

1. 先在已停止应用的目标数据库上确认迁移已经到达 RBAC 版本：

   ```sql
   SELECT version_num FROM alembic_version;
   ```

   如果缺少 IAM 表，应先通过受控发布流程执行应用迁移；不要手工创建表结构。

2. 在同一个事务中锁定内置角色和已核验用户，再补充分配。将
   `:approved_user_id` 替换为经过核验的内部 UUID 参数，由数据库客户端以参数方式
   传入，避免把账号标识写入 SQL 历史。

   ```sql
   BEGIN;

   SELECT id
   FROM iam_role
   WHERE code = 'platform_administrator'
   FOR UPDATE;

   SELECT id, is_active
   FROM "user"
   WHERE id = :approved_user_id
   FOR UPDATE;

   -- 仅当该账号已被明确批准恢复为可用状态时执行。
   -- UPDATE "user" SET is_active = TRUE WHERE id = :approved_user_id;

   INSERT INTO iam_user_role (user_id, role_id)
   SELECT :approved_user_id, id
   FROM iam_role
   WHERE code = 'platform_administrator'
   ON CONFLICT (user_id, role_id) DO NOTHING;

   COMMIT;
   ```

   若选定账号仍是停用状态，必须先由负责账号恢复的授权流程批准，再取消注释该
   `UPDATE`。RBAC 初始化本身绝不代替该决策。

3. 在重启前验证至少有一条有效分配，结果只需记录数量：

   ```sql
   SELECT count(DISTINCT u.id) AS active_platform_administrator_count
   FROM "user" AS u
   JOIN iam_user_role AS ur ON ur.user_id = u.id
   JOIN iam_role AS r ON r.id = ur.role_id
   WHERE u.is_active = TRUE
     AND r.is_active = TRUE
     AND r.code = 'platform_administrator';
   ```

   计数必须大于零。随后重启应用，并由该管理员登录确认
   `GET /api/v1/iam/me/permissions` 包含平台权限。

## 失败处理

事务中的角色或账号不存在、账号未经批准恢复、或有效管理员计数仍为零时，执行
`ROLLBACK`，保留应用停止状态并升级给授权负责人。不要通过修改 JWT、重置数据库
或重新运行初始化来绕过该不变量。
