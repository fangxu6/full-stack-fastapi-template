# External ERP Consumer API Boundary Design

## Scope And Decisions

This design creates a managed machine-to-machine API for one ERP/planning
consumer. It is not a public copy of the SPA API. The consumer can obtain a
short-lived OAuth2 Client Credentials token and make only two logical,
read-only queries:

1. Raw or finished inventory balance summaries.
2. A paginated inventory-document snapshot with the allowed line detail.

The selected policy is enterprise-confidential structured data, five-minute
ERP polling, a complete seven-calendar-day document snapshot, 15-minute token
lifetime, 365-day secret lifetime, 24-hour regular rotation overlap, immediate
next-request revocation, and the approved per-client limits. No endpoint
creates or changes inventory, users, permissions, documents, files, jobs, or
workflow state.

## Boundary And OpenAPI

Mount a dedicated FastAPI subapplication at `/api/external/v1`. It owns its
router, error handlers, OpenAPI schema, and `GET /api/external/v1/openapi.json`.
It reuses the outer application's request-ID middleware, configuration, database
engine, and structured-observability setup. It must register the same exception
handlers as the main application so every external error continues to return a
server-issued `X-Request-ID`.

The existing main application keeps its `/api/v1` router and
`/api/v1/openapi.json` unchanged. The external subapplication schema is not
included in `frontend/openapi.json` and does not generate SPA client code. Any
new internal credential-management routes remain additive `/api/v1` routes and
require the normal generated-client review; they have no required frontend UI
in V1.

External V1 uses these public paths:

| Operation | Path | Required scope | Contract |
| --- | --- | --- | --- |
| Issue token | `POST /api/external/v1/oauth/token` | None | OAuth2 client-credentials form grant only. |
| Read balances | `GET /api/external/v1/inventory/balances` | `inventory.balances.read` | One selected `inventory_kind` (`raw` or `finished`) per snapshot. |
| Read documents | `GET /api/external/v1/inventory/documents` | `inventory.documents.read` | Bounded business-date window, snapshot cursor pagination. |

`v1` permits additive fields/endpoints only. A breaking contract requires
`/api/external/v2`, a compatibility document, `Deprecation` and `Sunset`
response headers on V1 responses, and a minimum 90-day migration period. V1
cannot be removed until the ERP integration owner has completed the published
migration plan.

## External Contract

### Token

The token endpoint accepts form-encoded `grant_type=client_credentials`,
`client_id`, and `client_secret`. It accepts no password grant, user token,
impersonation parameter, refresh token, or caller-selected scope escalation.
It returns `access_token`, `token_type=Bearer`, `expires_in=900`, and the
client's assigned space-delimited scopes.

External JWTs use a dedicated signing secret and issuer, not the SPA's
`SECRET_KEY`. Required validated claims are `sub`/`client_id`,
`credential_id`, `scope`, `aud=external-api`, `iss`, `iat`, `exp`, and `jti`.
The external authentication dependency never calls `CurrentUser` or
`reusable_oauth2` and never constructs a `User` actor.

The token endpoint returns a generic `401 invalid_client` for unknown,
inactive, expired, or revoked client credentials. It does not reveal which
state failed. External data endpoints return generic `401 invalid_external_token`
for missing, expired, revoked, deactivated, malformed, or wrong-audience
tokens, and `403 insufficient_scope` only for an otherwise valid client that
lacks the route's scope. Error bodies include stable `error_code`, public
`detail`, and `request_id`; they never include credential state or internal
policy details.

### Read Snapshots

Both read operations use the same cursor-paginated snapshot envelope:

```json
{
  "data": [],
  "page": {
    "snapshot_id": "uuid",
    "snapshot_at": "2026-08-04T00:00:00Z",
    "expires_at": "2026-08-04T00:30:00Z",
    "total": 0,
    "next_cursor": null
  }
}
```

The first call supplies filters and `page_size` (1-100), then creates a
30-minute, client-bound materialized snapshot. Later calls provide only the
opaque `next_cursor`; it encodes a signed snapshot ID and page position and
cannot be reused by another client or with changed filters. An expired,
tampered, or foreign cursor returns a generic restart-required `410` or `400`
without exposing snapshot membership. Snapshot rows are removed when consumed
or expired and are also cleaned by a direct periodic task.

Materialization is required because the internal document list is offset based,
can be updated/soft-deleted/restored, and orders live rows by business date and
ID. Paging that live query cannot prove the completed ERP window is
authoritative. Creation runs in one database transaction, serializes only the
external allowlisted projection, and persists page items before returning the
first page. Subsequent pages read only snapshot rows, so an internal update or
deletion after snapshot creation cannot create a missing/duplicate page.

`/inventory/documents` requires `business_date_from` and `business_date_to`.
Their inclusive range is at most seven calendar days. Scheduled ERP work uses
the most recent seven days every five minutes. A controlled historical backfill
uses the same endpoint in consecutive seven-day chunks. The ERP upserts its own
local document by `document_id` and its lines by `document_id + line_no`; after
all pages complete, it treats the full window as authoritative. It must not
delete or invalidate local data after an incomplete, rate-limited, or failed
run.

`/inventory/balances` requires `inventory_kind` and may filter on
`processing_unit_id` and `item_name`. A balance snapshot represents the values
at `snapshot_at`; it does not make an inter-system reservation or consistency
guarantee.

Only these fields are serializable into an external snapshot:

| Resource | Fields |
| --- | --- |
| Balance | `inventory_kind`, `processing_unit_id`, `item_name`, `item_code`, `wool_content`, `color_code`, `dye_lot_no`, `rolls_balance`, `meters_balance` |
| Document | `document_id`, `document_type`, `business_date`, `processing_unit_id`, `receiving_unit_id`, `document_number` |
| Document line | `line_no`, `item_name`, `item_code`, `wool_content`, `color_code`, `dye_lot_no`, `quantity_rolls`, `quantity_meters` |

`remarks`, deletion timestamps/status, creator/updater data, import-batch
links, request/audit IDs, raw payloads, and unmodeled JSON are forbidden in
external DTOs and snapshot payloads.

## Client, Credential, And Scope Model

Add an `external_api_client` entity with immutable UUID ID, stable unique code,
display name, active state, role-level ownership labels, creation metadata, and
no destructive delete path. Add `external_api_client_scope` for explicit
allowlisted scope assignments. V1 permits only `inventory.balances.read` and
`inventory.documents.read`; the strings match existing inventory permission
vocabulary but are a separate client-scope assignment, not a human RBAC grant.

Add `external_api_credential` with immutable UUID credential ID, client ID,
Argon2-compatible secret hash, non-secret credential version/fingerprint,
status, issue/not-before/expiry/retirement/revocation timestamps, and no
plaintext secret column. A client has at least one active scope and may have
one active credential plus one 24-hour retiring credential. Secret generation
uses cryptographically secure randomness. Creation and rotation return the
secret exactly once through a protected internal management operation; later
reads return metadata only.

A protected internal management surface under `/api/v1/iam/external-api-clients`
creates clients, assigns fixed scopes, creates/rotates credentials, and
activates/deactivates clients or revokes credentials. It requires a new
catalogued `external_api.clients.manage` permission assigned to the built-in
Platform Administrator role. It exposes no secret after the create/rotate
response and has no V1 user interface. D-003 semantic audit events record
these lifecycle changes with a human administrator actor; the external call
table records machine traffic.

Every external protected request validates signature/claims, then reads current
client and credential state in the database. A deactivated client, revoked
credential, expired secret, or elapsed rotation deadline rejects an otherwise
unexpired token immediately. This database lookup is intentional: a cache would
violate the approved next-request revocation guarantee.

## Limits And Call Evidence

Use a Redis atomic token-bucket script, with a dedicated rate-limit database
separate from the existing Celery broker/result databases. Key buckets by
validated client ID and class (`token` or `data`) and calculate `Retry-After`
from the atomic result. Token requests are limited to 5/minute per client; the
two data operations share 60/minute with burst capacity 20. Redis loss or
script failure fails closed with a request-correlated `503`, not an in-process
per-worker limiter or a fail-open path.

Add an append-only `external_api_call` table. It stores only occurred time,
nullable known client/credential IDs, a server-owned operation code, scope
decision, status code, elapsed milliseconds, optional returned-record count,
and request ID. It stores no access token, secret/hash, authorization header,
query parameter, response body, error traceback, or inventory payload. Index
by occurred time, client/time, and operation/time. Every token/data outcome,
including `200`, `401`, `403`, `429`, and rate-limiter `503`, writes one record
and retains it for 90 days.

An external-subapplication ASGI audit middleware collects server-owned route,
authentication, scope, status, elapsed, and record-count state. It writes the
call row through an independent database transaction before releasing the
bounded JSON response, so rejected dependency paths cannot roll back evidence
with the endpoint transaction. A write failure fails the external request
closed before the response is emitted. A daily direct Celery task deterministically
removes rows older than 90 days. There is no audit query API, UI, or export;
only controlled operations database readers inspect this table.

## Persistence And Migration

The migration creates `external_api_client`, `external_api_client_scope`,
`external_api_credential`, `external_api_snapshot`,
`external_api_snapshot_item`, and `external_api_call`, with Chinese table and
column comments, check constraints, foreign keys for live client state, and
indexes required by credential lookup, snapshot paging/expiry, call audit, and
retention. Snapshot item payload uses JSONB only for the fixed external DTO
projection and is deleted within 30 minutes; it is not a generic payload store.

Add distinct configuration for the feature gate, external JWT/cursor secrets,
issuer/audience, and Redis rate-limit URL. Startup rejects default or missing
external secrets outside local development. The external app is not mounted
while `EXTERNAL_API_ENABLED` is false, making the feature disabled by default
until migration, provisioning, and integration verification complete.

Downgrade must refuse when clients, credentials, or call-audit records exist;
it must never silently delete credential metadata or evidence. Expired snapshot
rows may be removed during a controlled downgrade only after durable tables are
proven empty.

## Rollout And Rollback

1. Apply migrations with the feature gate disabled and verify comments,
   constraints, indexes, and cleanup tasks in an isolated environment.
2. Provision the ERP client, two scopes, and first secret through the protected
   management surface; transfer the one-time secret through an approved
   out-of-band channel.
3. Give ERP a non-production OpenAPI document and run token, balance, and
   document-snapshot validation. Enable the gate only after role owners record
   named contacts and support channels.
4. Monitor call rows and ERP-owned sync alerts. Rotate/replace the initial
   credential only through the planned overlap procedure.

Emergency rollback disables the feature gate and revokes the credential. It
removes external reachability on the next deployment/request while preserving
SPA sessions, `/api/v1`, external client metadata, and 90-day call evidence.
Application rollback never drops durable external tables. Re-enablement requires
an owner review and a newly verified credential.

## Design Stress Test

| Risk | Design response |
| --- | --- |
| An external addition changes generated SPA clients. | A mounted external subapplication owns a separate OpenAPI document. |
| A revoked token remains usable for 15 minutes. | Every protected request validates current client/credential state after JWT verification. |
| Multi-worker limits are bypassed. | Redis executes a shared atomic token-bucket script; Redis failure is closed. |
| A live list mutates while ERP pages it. | The first page materializes an allowlisted, client-bound snapshot; later pages never query live rows. |
| A `401` or `429` loses its audit record to a route rollback. | Middleware persists minimal evidence in an independent transaction before response release. |
| Secrets or sensitive fields leak through logs/audit/snapshots. | Hash-only credential storage, explicit DTO allowlist, body-free audit schema, and no request/response payload logging. |
| An internal management action becomes an ERP capability. | Management routes stay under protected `/api/v1`; external scopes only read balances/documents. |
