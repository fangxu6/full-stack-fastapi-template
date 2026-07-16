# PostgreSQL 数据库导出与恢复

本文说明如何使用 PostgreSQL 官方客户端工具导出和恢复数据库，适用于本地开发、测试环境和生产环境的备份迁移。

## 1. 准备工作

需要安装与数据库版本兼容的 PostgreSQL 客户端工具：

- `pg_dump`：导出数据库。
- `pg_restore`：恢复自定义格式、目录格式或 tar 格式备份。
- `psql`：执行 SQL 文件或连接数据库。

先确认工具可用：

```bash
pg_dump --version
pg_restore --version
psql --version
```

建议通过环境变量提供连接参数。这样可以减少命令重复，并避免把密码直接写入命令行：

```bash
export PGHOST=127.0.0.1
export PGPORT=5432
export PGUSER=postgres
export PGDATABASE=aiadmin
export PGPASSWORD='postgres'
```

生产环境更建议使用 `.pgpass` 或 PostgreSQL 客户端的密码提示，不要长期设置 `PGPASSWORD`。Windows PowerShell 对应写法为：

```powershell
$env:PGHOST = "127.0.0.1"
$env:PGPORT = "5432"
$env:PGUSER = "postgres"
$env:PGDATABASE = "aiadmin"
$env:PGPASSWORD = "postgres"
```

本项目的后端数据库配置通常由以下环境变量组成：`POSTGRES_SERVER`、`POSTGRES_PORT`、`POSTGRES_USER`、`POSTGRES_PASSWORD` 和 `POSTGRES_DB`。导出时请使用实际运行环境中的值。

## 2. 导出数据库

### 2.1 导出为自定义格式（推荐）

自定义格式适合备份和迁移，可以在恢复时选择 schema、表或数据，并支持并行恢复：

```bash
pg_dump \
  --format=custom \
  --file=app-$(date +%Y%m%d-%H%M%S).dump \
  --no-owner \
  --no-privileges \
  "$PGDATABASE"
```

Windows PowerShell：

```powershell
$backup = "app-$(Get-Date -Format 'yyyyMMdd-HHmmss').dump"
pg_dump --format=custom --file=$backup --no-owner --no-privileges $env:PGDATABASE
```

### 2.2 导出为纯 SQL 文件

纯 SQL 文件便于审查、版本化或使用 `psql` 恢复：

```bash
pg_dump \
  --format=plain \
  --file=app.sql \
  --no-owner \
  --no-privileges \
  "$PGDATABASE"
```

如需压缩 SQL 文件，可以使用 gzip：

```bash
pg_dump --format=plain --no-owner --no-privileges "$PGDATABASE" | gzip > app.sql.gz
```

### 2.3 只导出结构或数据

只导出表结构：

```bash
pg_dump --schema-only --file=app-schema.sql "$PGDATABASE"
```

只导出数据：

```bash
pg_dump --data-only --file=app-data.sql "$PGDATABASE"
```

只导出指定 schema：

```bash
pg_dump --schema=public --file=app-public.dump --format=custom "$PGDATABASE"
```

只导出指定表及其数据：

```bash
pg_dump --table=public.users --table=public.items \
  --file=app-selected.dump --format=custom "$PGDATABASE"
```

### 2.4 导出时的一致性与大库选项

`pg_dump` 默认生成一致性快照，通常不需要停止应用。对生产库执行前仍应评估备份期间的负载和磁盘空间。

大数据库可以考虑：

```bash
pg_dump --format=directory --jobs=4 --file=app-backup-dir "$PGDATABASE"
```

目录格式支持并行导出和恢复。`--jobs` 不应盲目调大，应根据数据库服务器 CPU、磁盘和连接数限制调整。

## 3. 查看备份内容

查看自定义格式备份中的对象：

```bash
pg_restore --list app.dump
```

查看 SQL 文件而不执行：

```bash
less app.sql
```

Windows PowerShell 可使用：

```powershell
Get-Content .\app.sql -TotalCount 100
```

## 4. 恢复数据库

恢复前应确认目标数据库、目标服务器和备份文件均正确。生产恢复建议先在隔离环境演练，并保留目标库的当前备份。

### 4.1 恢复自定义格式

目标数据库已存在时：

```bash
pg_restore \
  --dbname="$PGDATABASE" \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  app.dump
```

如果要并行恢复目录格式或自定义格式：

```bash
pg_restore --username=postgres --dbname="$PGDATABASE"  --jobs=4 --no-owner --no-privileges app.dump
```

`--clean` 会在创建对象前删除目标对象，可能造成数据丢失。除非明确需要覆盖目标库，否则不要使用该选项。

pg_restore `
  --host=localhost `
  --port=5432 `
  --username=postgres `
  --dbname=aiadmin `
  --jobs=4 `
  --clean `
  --if-exists `
  --no-owner `
  --no-privileges `
  --exit-on-error `
  .\app-20260715-100150.dump

### 4.2 恢复纯 SQL 文件

```bash
psql --dbname="$PGDATABASE" --file=app.sql
```

恢复压缩 SQL 文件：

```bash
gunzip -c app.sql.gz | psql --dbname="$PGDATABASE"
```

### 4.3 新建数据库后恢复

先连接维护数据库创建目标库：

```bash
createdb --host="$PGHOST" --port="$PGPORT" --username="$PGUSER" app_restore
```

再恢复备份：

```bash
pg_restore --dbname=app_restore --no-owner --no-privileges app.dump
```

如果备份包含数据库创建语句，可使用 `pg_restore --create`，但该选项会连接到维护数据库并创建备份中的数据库名；使用前请确认数据库名和权限符合预期。

## 5. 远程数据库导出

通过参数直接指定远程连接：

```bash
pg_dump \
  --host=db.example.com \
  --port=5432 \
  --username=backup_user \
  --format=custom \
  --file=app.dump \
  app
```

如果数据库只能通过 SSH 访问，可先建立端口转发：

```bash
ssh -N -L 15432:127.0.0.1:5432 user@server.example.com
```

然后让 `pg_dump` 连接本地转发端口：

```bash
pg_dump --host=127.0.0.1 --port=15432 --username=backup_user \
  --format=custom --file=app.dump app
```

远程导出前请确认防火墙、TLS、数据库访问控制和备份账号权限。优先使用最小权限的专用备份账号，不要使用应用超级用户。

## 6. 导出后验证

至少执行以下检查：

```bash
pg_restore --list app.dump > app-objects.txt
sha256sum app.dump > app.dump.sha256
```

在临时数据库进行恢复演练：

```bash
createdb app_restore_check
pg_restore --dbname=app_restore_check --no-owner --no-privileges app.dump
psql --dbname=app_restore_check --command='\dt'
```

验证完成后删除临时数据库：

```bash
dropdb app_restore_check
```

备份至少应具备：文件大小合理、校验和可复核、恢复命令可执行、关键表和关键数据可查询。仅确认文件生成成功，不代表备份可恢复。

## 7. 常见问题

### 密码认证失败

检查 `PGHOST`、`PGPORT`、`PGUSER`、`PGDATABASE` 和密码是否属于同一个环境；同时检查服务器的 `pg_hba.conf`、网络访问和 TLS 要求。

### `pg_restore` 报对象已存在

目标库已有对象时，可以选择：

- 在确认允许覆盖的情况下使用 `--clean --if-exists`。
- 恢复到新的空数据库。
- 使用 `pg_restore --list` 和 `--use-list` 精确选择恢复对象。

### 权限或 owner 错误

跨环境迁移时通常使用 `--no-owner --no-privileges`，然后由目标环境管理员按实际需要授予权限。如果必须保留 owner 和授权关系，应先在目标环境创建对应角色。

### 版本不兼容

导出工具版本不应明显低于源数据库版本。恢复到较旧的 PostgreSQL 大版本可能不受支持；迁移前应查阅目标版本兼容性并在临时环境验证。

### 中文或特殊字符导致命令失败

将路径用引号包裹，并确认终端编码。Windows PowerShell 中示例：

```powershell
pg_restore --dbname=$env:PGDATABASE --file=".\备份\app.dump"
```

注意：`pg_restore` 的备份文件作为最后一个位置参数传入；如果使用 `--file`，它表示输出 SQL，而不是输入备份文件。恢复自定义格式时更推荐直接把备份文件作为最后一个参数：

```powershell
pg_restore --dbname=$env:PGDATABASE ".\备份\app.dump"
```

## 8. 安全注意事项

- 不要将数据库密码、连接串或包含敏感数据的备份提交到 Git。
- 备份文件应设置严格的文件权限，并按组织要求加密存储和传输。
- 生产备份目录应限制访问，并设置保留周期和过期清理策略。
- 备份可能包含用户信息、令牌、业务数据和审计数据；分享前应脱敏或获得授权。
- 恢复生产数据到开发环境前，应清理或替换密码、访问令牌、邮件地址等敏感字段。
- 定期执行恢复演练，记录备份时间点、恢复耗时和恢复结果。

