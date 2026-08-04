# External ERP Consumer API E2E Test Plan

## Environment

- Target backend: `http://127.0.0.1:8000`
- Health check: `/api/v1/utils/health-check/`
- Isolation: a newly created PostgreSQL database ending in `_test` or `_pytest`
  and a dedicated Redis database/key prefix. Do not seed a development or
  production database.
- Feature gate: enable `EXTERNAL_API_ENABLED` only after migrations and fixture
  provisioning. Keep a separate regression case with the gate disabled.
- Fixtures: a Platform Administrator, one active ERP client with both V1
  scopes, one balance-only client, active/retiring/revoked credential variants,
  raw/finished inventory rows, and documents within and outside the seven-day
  window. Fixtures include internal `remarks`, a soft-deleted document, and
  user/audit fields to prove they are not serializable externally.

## Cases

| ID | Endpoint / Flow | Setup Data | Request | Expected Response | Persistence / Side Effects | Failure Assertions |
| --- | --- | --- | --- | --- | --- | --- |
| E2E-001 | Feature gate and SPA regression | External gate disabled; valid SPA user | Request external OpenAPI/token path and existing `/api/v1/login/access-token` | External path unavailable; SPA login/current API behavior unchanged | No external client/call rows | The SPA schema/client never gains external paths. |
| E2E-002 | Client provisioning and one-time secret | Platform Administrator and no ERP client | Protected internal create client/credential request | Metadata plus a secret only in this response | Client, two scopes, credential metadata, and one semantic lifecycle audit event persist | Later list/get/semantic-audit payloads never contain the secret/hash; unprivileged caller is denied. |
| E2E-003 | Client Credentials token | Active client with both scopes | Form `grant_type=client_credentials`, client ID and secret | `200` token with Bearer type, 900-second expiry, external audience, assigned scopes | Exactly one minimal `oauth.token` success call row, no token/secret data | Password grant, invalid grant, bad secret, inactive/revoked/expired credential receive generic `401` and one rejection audit row. |
| E2E-004 | Immediate revocation and rotation | Issued valid token; active and then rotating credentials | Read before/after revoke, deactivate, and expiry; use both secrets during 24-hour overlap | Valid before revoke; next request fails `401` after revoke/deactivation/overlap end | Call row records each outcome; secret metadata retains state | No token remains valid merely because its 15-minute JWT expiry has not passed. |
| E2E-005 | Scope separation | Balance-only token | GET balances, then GET documents | Balance `200`; documents `403 insufficient_scope` | One call row per request with correct scope decision | No document payload or existence information is returned. |
| E2E-006 | Balance snapshot and redaction | Raw and finished fixtures plus excluded fields | First GET balances with kind/filter/page size, then cursored pages | `200`, stable snapshot metadata, at most 100 data items, allowed balance fields only | Snapshot rows use allowlisted projection; success call rows include record count | Invalid/foreign/tampered/expired cursor returns public error and no other client's data. Excluded fields never appear. |
| E2E-007 | Seven-day document snapshot | Documents inside/outside window, soft-deleted and later-mutated fixtures | First GET documents for exactly seven days; fetch every `next_cursor` | Complete, stable allowed document/line projection; outside/deleted records absent | Snapshot is client-bound and has one call row per page | Window over seven days is rejected. `remarks`, deletion/user/audit/import fields never appear. |
| E2E-008 | Mutation during paging | Create first document snapshot, then internally update/delete/restore a document before next page | Continue original cursor then create a new snapshot | Original pages retain first snapshot projection; new snapshot reflects current visible state | ERP can safely treat only completed original snapshot as authoritative | No duplicate/missing page caused by live offset pagination; partial snapshot cannot direct local deletion. |
| E2E-009 | Rate limits and retry headers | Active client; isolated Redis bucket | Exceed token 5/minute and data 60/minute + burst 20 | `429` contains `Retry-After`, public error, and `X-Request-ID` | Each rejection produces one call row; bucket is shared across workers | A second worker cannot bypass the limit. Redis failure returns `503` and no inventory data. |
| E2E-010 | Audit minimization and retention | Execute success, 401, 403, 429, and 503 paths | Inspect `external_api_call`, then run cleanup around 90-day cutoff | One row per final outcome with only approved fields; rows exactly at cutoff remain | Older rows delete deterministically; semantic audit remains distinct | No credential secret/hash, auth header, query value, payload, raw error, or response body persists. |
| E2E-011 | Version/OpenAPI compatibility | Enabled external app and existing SPA schema | Fetch `/api/external/v1/openapi.json`, `/api/v1/openapi.json`, and an external response marked deprecated in a fixture | External schema contains only external routes; SPA schema contains no external routes; deprecation response carries documented headers | No generated SPA client modification from external schema | Breaking V1 contract is rejected by contract/Spectral tests; V2 requires separate route/schema. |
| E2E-012 | Migration and rollback | Fresh isolated database, then populated external durable records | Upgrade, inspect comments/indexes/constraints, attempt downgrade | Upgrade succeeds; Chinese comments and indexes exist; populated downgrade refuses | Durable client/credential/call records remain intact | Snapshot-only cleanup cannot permit destruction of durable records. |

## Execution

1. Start the isolated backend and Redis, verify the health endpoint, and verify
   that test configuration uses no production credential or database.
2. Run every case in order. Exercise data routes with real form/token headers,
   complete cursors, and database assertions rather than mocked middleware.
3. The ERP reconciliation is a consumer operation: prove the server returns a
   stable complete snapshot and that a partial/failed cursor sequence has no
   server-side deletion behavior. Use a small test consumer fixture to prove
   `document_id` and `line_no` support local upsert and only a completed window
   can be reconciled.
4. Run focused, full backend, OpenAPI/Spectral, generated-client, and diff
   checks from `implement.md`. Record command output or a concrete isolated
   environment blocker there; unrun cases are not passed.
