# AI Inventory Sidecar Contract

> Read before changing `sidecar/**`, its Compose service, or the FastAPI BFF
> client that calls it.

---

## 1. Scope / Trigger

- Trigger: changing the inventory AI sidecar's HTTP endpoint, model/tool
  registry, environment wiring, Docker exposure, or FastAPI-to-sidecar client.
- Primary files: `sidecar/src/{app,config,protocol,server,tools,workflow}.ts`,
  `sidecar/Dockerfile`, and `compose.yml`.
- Out of scope: FastAPI authorization/grant issuance, audit persistence, and
  inventory business queries, which remain owned by `backend/app/modules/ai/**`
  and `backend/app/modules/inventory/**`.

## 2. Signatures / Interfaces

- Private endpoint: `POST /v1/inventory/query`.
- Required headers: `X-AI-Orchestrator-Token`, `X-Request-ID`, and
  `X-AI-Actor-Grant`.
- Request body: `{"run_id":"<UUID>","question":"<1..2000 chars>"}`.
- Completed envelope: `status`, `answer`, `citations` (1-5), and
  `provider_metadata`.
- Failed envelope: `{"status":"failed","error":{"category":...,"retryable":...}}`.
- Health endpoint: `GET /health` returns `{"status":"ok"}` and is available
  only on the container network.

## 3. Contracts

- The sidecar accepts only the BFF service credential. It never accepts a
  browser JWT or database credential.
- FastAPI owns authorization and sends `AI_ORCHESTRATOR_SERVICE_TOKEN`; the
  sidecar calls inventory projections with the separate
  `AI_INTERNAL_SERVICE_TOKEN` and forwards the actor grant/request ID.
- FastAPI calls the sidecar with a 30-second `httpx` timeout and no retry. A
  completed envelope completes the matching `ai_run` with provider/model
  metadata; HTTP, timeout, or envelope-validation failure marks that run
  failed before returning the standard backend 503 error.
- `OPENAI_MODEL` is exactly `gpt-5.6-luna`, with `reasoning.effort=medium`.
  The tool registry is exactly `balances`, `documents`, `ledger`,
  `processing_units`, and `receiving_units`; web, file, MCP, shell, memory,
  and write tools are forbidden.
- The Compose service joins only `default`, declares no `ports` or Traefik
  labels, and receives no PostgreSQL credentials.
- Operational logs may contain only request ID, HTTP status, and completed or
  failed outcome. Do not add question text, grants, credentials, raw tool data,
  or provider error text to logging calls.

## 4. Validation & Error Matrix

| Condition | Expected behavior | Verification |
| --- | --- | --- |
| Valid BFF request and structured model result | completed envelope with citations and minimal metadata | `sidecar/tests/workflow.test.ts` |
| Missing/invalid BFF token or request shape | failed `tool_rejected` or `invalid_response`; no workflow execution | `sidecar/tests/auth.test.ts`, `sidecar/tests/app.test.ts` |
| Internal 401/403 | failed `tool_rejected`, not a provider failure | `sidecar/tests/workflow.test.ts` |
| Internal non-2xx or invalid JSON/schema | failed `tool_failed` or `invalid_response` | `sidecar/tests/workflow.test.ts`, `sidecar/tests/tools.test.ts` |
| Provider 429, timeout/abort, or other unavailable failure | `rate_limited`, `timeout`, or `provider_unavailable`; only these are retryable | `sidecar/tests/workflow.test.ts` |
| Public exposure or direct database access | prohibited by Compose/service contract | review `compose.yml` and `sidecar/Dockerfile` |

## 5. Good / Base / Bad Cases

- Good: FastAPI passes a run-bound grant and separate BFF token, sidecar
  returns a validated envelope, and only allowlisted metadata is logged.
- Base: tests use an injected agent and mocked FastAPI `fetch`; no real OpenAI
  request is needed to verify protocol behavior.
- Bad: returning provider exception text, registering a model-hosted tool not
  in the allowlist, reusing the two service tokens, adding Traefik labels, or
  making `GET /health` externally routable.

## 6. Tests Required

- Sidecar: run `bun test`, `bun run typecheck`, and `bunx biome check sidecar`.
- Contract: cover every failure category, BFF token rejection, grant/header
  forwarding, bounded tool inputs, structured result validation, health, and
  allowlisted logging.
- Cross-layer: when changing this protocol, update the FastAPI BFF client and
  its tests before regenerating any affected public OpenAPI client; do not
  manually edit `frontend/src/client/**`.
- Deployment: inspect the Compose service for absence of host ports, Traefik
  labels, and database environment variables. Run Docker integration only in
  an approved environment.

## 7. Wrong vs Correct

### Wrong

```ts
throw new Error(providerResponse.text())
```

This leaks provider details and makes callers parse natural-language errors.

### Correct

```ts
if (getErrorStatus(error) === 429) return failed("rate_limited")
return failed("provider_unavailable")
```

Return the frozen failure enum and keep raw provider data inside the sidecar.
