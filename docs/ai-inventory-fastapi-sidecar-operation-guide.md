# AI inventory FastAPI and sidecar operation guide

This guide describes the non-Docker startup path for the inventory AI pilot.
It keeps FastAPI as the authorization and inventory business boundary. The
Mastra sidecar is a private local process.

## Runtime topology

```text
Yaak or browser -> FastAPI 127.0.0.1:8000 -> sidecar 127.0.0.1:3000
sidecar -> FastAPI internal inventory endpoints -> PostgreSQL
sidecar -> OpenAI-compatible provider
```

Do not expose port `3000`. Do not call the sidecar from Yaak or a browser.

## Secret files

Root `.env` is tracked by this repository. Keep normal application and database
settings there only. Do not put AI service tokens, the actor-grant signing key,
or the provider API key in that file.

Use two separate secret sources:

- `D:\Workspace\full-stack-fastapi-template\.env.ai.secrets`: sidecar only.
  This file is ignored by Git.
- `%LOCALAPPDATA%\full-stack-fastapi-template\ai-backend.env`: FastAPI only,
  or use the deployment platform's secret manager. Keep this file outside the
  repository.

The two service tokens are distinct. `AI_PROVIDER_API_KEY` must never enter the
FastAPI process. `AI_ACTOR_GRANT_SIGNING_KEY` must never enter the sidecar
process.

## FastAPI configuration

Create `%LOCALAPPDATA%\full-stack-fastapi-template\ai-backend.env` with these
placeholders:

```env
AI_ENABLED=true
AI_ORCHESTRATOR_URL=http://127.0.0.1:3000
AI_ORCHESTRATOR_SERVICE_TOKEN=<orchestrator-service-token>
AI_INTERNAL_SERVICE_TOKEN=<internal-service-token>
AI_ACTOR_GRANT_SIGNING_KEY=<actor-grant-signing-key>
```

Load the file into the current PowerShell process, then start FastAPI. This
loader accepts `KEY=value` lines and does not print values.

```powershell
$secretFile = Join-Path $env:LOCALAPPDATA 'full-stack-fastapi-template\ai-backend.env'

Get-Content -LiteralPath $secretFile | ForEach-Object {
  if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$') {
    [Environment]::SetEnvironmentVariable($matches[1], $matches[2].Trim(), 'Process')
  }
}

Set-Location D:\Workspace\full-stack-fastapi-template\backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`AI_ENABLED=true` requires all four listed FastAPI settings. Start FastAPI on
`127.0.0.1` for this direct-process topology.

## Sidecar configuration

Create or update the repository-root `.env.ai.secrets` file. It contains only
sidecar settings:

```env
AI_SIDECAR_HOST=127.0.0.1
AI_INTERNAL_BASE_URL=http://127.0.0.1:8000
AI_INTERNAL_SERVICE_TOKEN=<internal-service-token>
AI_ORCHESTRATOR_SERVICE_TOKEN=<orchestrator-service-token>

AI_PROVIDER_NAME=<lowercase-provider-name>
AI_PROVIDER_BASE_URL=https://<provider-host>/v1
AI_PROVIDER_ALLOW_INSECURE_HTTP=false
AI_PROVIDER_API_KEY=<provider-api-key>
AI_PROVIDER_MODEL=gpt-5.6-luna
```

For an internal HTTP provider, set the base URL to its `/v1` API path and set:

```env
AI_PROVIDER_ALLOW_INSECURE_HTTP=true
```

Use HTTP only for a local or private-network provider. `AI_SIDECAR_HOST` accepts
only `127.0.0.1` or `0.0.0.0`; retain `127.0.0.1` outside Docker.

Start the sidecar from `sidecar/` with Bun's explicit env-file option. Do not
use `bun --env-file=... run start`, because the current `start` script launches
a nested Bun process that does not inherit the option.

```powershell
Set-Location D:\Workspace\full-stack-fastapi-template\sidecar
bun --env-file=../.env.ai.secrets src/server.ts
```

## Database migration

The BFF writes every request to `ai_run` and each inventory projection call to
`ai_tool_call`. Confirm the database revision before enabling AI:

```powershell
Set-Location D:\Workspace\full-stack-fastapi-template\backend
uv run alembic current
```

The required revision is `5f3a7c1d9e2b (head)`. If the database is behind,
review the pending migrations and take a backup before running:

```powershell
uv run alembic upgrade head
```

The preceding `4d7e8f9a0b1c` migration repairs inventory business dates from
legacy import data and cannot be downgraded. Do not run `upgrade head` on a
production database until that data change is approved.

## Health checks

Use `curl.exe --noproxy "*"` because a local HTTP proxy can otherwise return a
misleading `502` response.

```powershell
curl.exe --noproxy "*" -i http://127.0.0.1:8000/api/v1/utils/health-check/
curl.exe --noproxy "*" -i http://127.0.0.1:3000/health
```

Both responses must be `200 OK`. This proves process availability only. It does
not prove that the provider supports the inventory workflow.

## Provider compatibility gate

The sidecar requires more than a reachable OpenAI-compatible `/v1/models` or
`/v1/chat/completions` endpoint. The fixed model must support all of these:

- OpenAI-compatible Chat Completions.
- JSON Schema structured output used by Mastra `experimental_output`.
- Function or tool calling.

The current provider investigation established that ordinary chat completions
work, but the Mastra structured-output probe returned no parsed object. Until
the provider supports structured output and tool calling for `gpt-5.6-luna`, a
real BFF question returns `503 AI inventory query is unavailable` before any
inventory tool call.

## Diagnose a BFF failure

Use the response `request_id` to inspect the minimal audit record. Do not query
or log the full question, grant, service tokens, or raw inventory payload.

```sql
SELECT
  request_id,
  status,
  provider,
  model,
  error_category,
  used_tool_calls,
  max_tool_calls,
  started_at,
  completed_at
FROM ai_run
WHERE request_id = '<request-id>';
```

Interpret the result as follows:

| Result | Meaning | Action |
| --- | --- | --- |
| `COMPLETED` with `used_tool_calls > 0` | Full BFF, provider, and internal-tool path succeeded | Review citations and audit metadata |
| `FAILED`, `orchestrator_unavailable`, `used_tool_calls = 0` | Sidecar returned no completed envelope before a tool call | Check provider structured output, model mapping, and sidecar startup config |
| `FAILED`, `orchestrator_unavailable`, sidecar health unavailable | FastAPI cannot reach the local sidecar | Check `AI_ORCHESTRATOR_URL` and loopback listeners |
| `500 Internal Server Error` with missing `ai_run` | AI migration was not applied | Review then apply Alembic migrations |

## Operational boundaries

- FastAPI owns superadmin authorization, actor grants, audit persistence, and
  inventory read projections.
- The sidecar owns provider calls and no database credentials.
- The provider receives only the data returned by approved read-only tools.
- The public BFF accepts a question only. It does not accept SQL, tool names,
  provider configuration, grants, or service tokens.
