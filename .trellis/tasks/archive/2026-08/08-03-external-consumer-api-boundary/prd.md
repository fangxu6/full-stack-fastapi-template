# External Consumer API Boundary

## Goal

D-005: define the smallest managed API product boundary for the first
approved external consumer, without changing the SPA authentication contract
or exposing internal platform capabilities by accident.

The product outcome is a reviewable consumer contract: one named consumer,
one contractual business use case, a minimum endpoint set, and explicit
identity, authorization, quota, audit, documentation, versioning, and
revocation behavior.

## Confirmed Facts

- This is a planning child of
  [`07-22-enterprise-platform-capability-backlog`](../07-22-enterprise-platform-capability-backlog/).
  It remains in `planning`; no implementation or application behavior change
  is authorized by this task.
- The current backend is FastAPI with a single `/api/v1` router and a generated
  OpenAPI contract (`backend/app/main.py:46-70`, `backend/app/api/main.py`).
  The frontend consumes the generated client; backend OpenAPI changes require
  client regeneration (`frontend/CODING_STANDARDS.md:88`).
- The SPA authenticates through `POST /api/v1/login/access-token` using the
  OAuth2 password form. The access JWT contains only `sub` and `exp`, uses the
  application `SECRET_KEY`, and is resolved to an active non-system `User`
  (`backend/app/api/routes/login.py:16-25`,
  `backend/app/api/dependencies/auth.py:24-49`,
  `backend/app/core/security.py:18-24`). There is no consumer/client identity,
  client-credential grant, scope claim, API-key contract, or token audience
  boundary today.
- Current API authorization is user/RBAC based. D-001 established stable
  server-side permission codes and default-deny behavior for the protected
  inventory and IAM surfaces; `is_superuser` remains a compatibility marker
  for deferred paths. D-005 must not silently widen those permissions.
- Request IDs are generated/normalized by middleware and returned as
  `X-Request-ID`; they are available in request state and structured logs
  (`backend/app/core/exceptions.py:80-109`).
- D-003 provides an append-only application audit table/writer with actor UUID,
  request ID, namespaced action/resource IDs, allowlisted JSONB changes, and
  365-day retention. V1 has no audit query API/UI/export; an external API
  design must define its own call-audit event vocabulary and reader policy
  before exposing it.
- Existing structured observability records all errors/slow responses but
  samples successful HTTP responses, and D-009 has not selected an operating
  external log platform. D-003 `audit_event` records low-volume semantic
  changes for 365 days. Neither is the complete external-call audit required
  here; V1 therefore needs a dedicated, append-only 90-day call record.
- The parent backlog explicitly excludes raw database, filesystem, shell,
  network, private-service, and retired AI/MCP capabilities from any external
  API surface.
- The current inventory module exposes separate authenticated read routes for
  raw balances (`backend/app/modules/inventory/router.py:384-406`), finished
  balances (`:408-430`), paginated/filterable document lists
  (`:298-329`), document-by-ID reads (`:331-346`), ledger entries
  (`:432-463`), processing/receiving master units (`:172-274`), and field
  suggestions (`:465-489`). The balance and document response models include
  identifiers, item attributes, quantities, document lines, remarks, and
  deletion timestamps (`backend/app/schemas/inventory.py:119-178`). These
  existing routes require human/RBAC permissions and are not yet an external
  contract.
- Internal inventory documents support update, soft delete, and restore
  operations (`backend/app/modules/inventory/router.py:348-382`), while the
  external V1 response deliberately excludes deletion metadata. The external
  contract therefore needs an explicit correction/reconciliation rule instead
  of implying append-only source data.

## Fundamental Truths And Constraints

1. An external consumer needs a stable machine identity and revocable
   credentials that are distinct from a human SPA account.
2. Authorization must be enforced by the backend for every consumer request;
   frontend visibility is irrelevant to an external caller.
3. A consumer contract must minimize data and operations to the approved use
   case; the existing SPA route catalog is not a public API catalog.
4. Every call must be attributable without storing bearer secrets or raw
   request/response bodies, and quota enforcement must produce a deterministic
   client-visible response.
5. Existing SPA JWT behavior and generated-client compatibility remain stable
   unless a separately reviewed migration explicitly changes them.
6. Scheduled pull requires a bounded, client-bound snapshot cursor: a completed
   document window must not paginate a changing live list. V1 does not require
   event delivery or server push.
7. Because V1 excludes deletion metadata and change events, a completed
   document window must be reconciled as a snapshot. A partial or failed window
   cannot safely remove ERP-local data.

## Requirements

### R1. Approved consumer contract

The first external consumer is an ERP/planning-system integration client. Its
V1 use case is read-only retrieval of inventory balances and inventory
documents to support planning. The approved business/technical role owners,
data classification, call pattern, error semantics, and endpoint set are
defined below. Before activation, the role owners must assign named contacts
and support channels; the set remains allowlisted by operation rather than
inferred from existing routes.

The approved V1 read surface is deliberately limited to:

- a balance summary covering both raw and finished inventory kinds, with
  bounded pagination and approved filters; and
- a document query with bounded pagination and approved date/unit/type filters,
  returning only the line detail required for planning.

The initial response allowlist is:

- Balance summary: inventory kind (`raw` or `finished`), processing-unit ID,
  item name/code, wool content, color code, dye-lot number, roll balance, and
  meter balance.
- Document list: document ID/type, business date, processing-unit ID,
  receiving-unit ID when applicable, document number, and line number, item
  name/code, wool content, color code, dye-lot number, roll quantity, and meter
  quantity.

`remarks`, `deleted_at`, creator/updater fields, import associations, request
IDs, audit fields, and arbitrary extra JSON are excluded from the external
schema even though some are present in internal models.

Ledger reads, document-by-ID reads, master-unit reads, suggestions, deleted
records, and any write/import/export operation are excluded from V1. They are
not transitively exposed because the SPA has a route for them.

For documents, the ERP calls the paginated list every five minutes with the
most recent seven calendar days as its business-date window. It upserts only
its own local copy by external `document_id` and `document_id + line_no`; this
does not write to the platform. After, and only after, every page in the window
has completed successfully, it treats the results as authoritative and marks
its local records absent from the completed window as invalid/deleted. Any
page failure, `429`, or `5xx` leaves its local data unchanged for deletion
purposes. Corrections older than seven days require a controlled manual ERP
backfill for a specified date range; V1 adds neither deletion tombstones nor
change events.

### R2. Consumer identity and credentials

Define a non-human consumer/client record, ownership, active/revoked status,
credential issuance and one-time secret reveal, credential rotation, expiry,
and emergency revocation. Consumer credentials must never be persisted or
written to logs in plaintext. V1 uses OAuth2 Client Credentials: the client
secret is stored only as a slow hash, token issuance verifies active client and
credential state, and every issued token has a distinct external audience,
client subject, approved scopes, issued-at and expiration claims. The design
uses a 15-minute access-token lifetime, 365-day maximum secret lifetime, and
24-hour regular-rotation overlap. It must validate issuer/audience and
clock-skew rules, and every protected request checks current client and
credential version state so deactivation or revocation rejects an otherwise
unexpired token on its next use.

### R3. Authorization and scope boundary

Map each approved endpoint to stable consumer scopes and the existing D-001
permission/resource boundary. Default deny applies when a scope, consumer
status, or underlying business permission is missing. Consumer credentials
must not impersonate a human user or inherit `is_superuser`; privileged
operations require an explicit product decision and separate scope.

V1 scopes are `inventory.balances.read` and `inventory.documents.read`, matching
the existing inventory authorization vocabulary. A client receives only the
scopes explicitly assigned to it; current SPA user permissions remain the
authorization source for `/api/v1` and are not exchanged for consumer scopes.

### R4. Quotas and rate limits

V1 applies a per-client combined bucket of 60 data reads per minute with burst
capacity 20 across the two external query operations. The OAuth2 token endpoint
is independently limited to 5 requests per minute per client. List pages are
bounded at 100 records. The rate-limit response is `429` with `Retry-After`
and `X-Request-ID`; its body follows the external error contract. Enforcement
must be safe under multiple backend workers and must state the storage/atomicity
requirement. No mutation exists in V1, so a quota rejection cannot partially
apply a business change.

### R5. Call audit and observability

V1 persists one dedicated, append-only minimal call record for every token
request and external data request, including successful calls and rejected
authentication, authorization, and rate-limit attempts. Its allowlist is
consumer ID, credential-version identifier (never its secret), operation,
scope decision, status code, elapsed time, returned-record count when
available, and request ID. It must not retain access tokens, client secrets,
authorization headers, query values, request/response bodies, raw errors, or
business resource payloads.

Records retain for 90 days and then are deterministically deleted. V1 has no
call-audit API, UI, or export; only controlled operations database readers may
inspect them. Call records correlate with D-002 request logs through request
ID but do not replace D-003 semantic-change evidence or duplicate its IAM
action vocabulary.

### R6. Versioning and compatibility

V1 is a separately named `/api/external/v1` boundary. It permits only
backward-compatible additions. A breaking change requires a side-by-side
`/api/external/v2`, at least 90 days' advance documentation and `Deprecation` /
`Sunset` response information, and an ERP migration plan. The SPA `/api/v1`
routes and their generated client remain behaviorally unchanged; external
OpenAPI is published separately and is never a source for the SPA client.

### R7. Documentation and operations

Specify the contractual OpenAPI document, authentication/scopes examples,
error and pagination schemas, rate-limit headers, changelog/deprecation
policy, onboarding/ownership runbook, credential rotation/revocation runbook,
and support/SLA expectations. Documentation must be generated from the
approved route contract and must not advertise internal routes.

The supply-chain/planning team owns business-contract approval; platform
API/integration owns the API, credentials, and limits; ERP integration owns
polling/retries and its 30-minute alert; security/operations owns emergency
revocation and call-audit database access. Activation must assign named contacts
and support channels to these roles without changing the role ownership model.

### R8. Safety, rollout, and rollback

Define feature gating/disabled-by-default rollout, migration order, secret
handling, monitoring, abuse response, and rollback that removes external
reachability without invalidating SPA sessions or deleting audit evidence.

## Acceptance Criteria

- [x] Product owner approved the ERP/planning-system integration client,
  role-level ownership, scheduled read-only balance/document use case,
  enterprise-confidential data classification, OAuth2 Client Credentials,
  two-capability minimum endpoint set, structured response allowlist without
  remarks/deletion/user/audit fields, 15-minute freshness, 30/60/120-second
  retries, and ERP-owned alerts after a 30-minute gap.
- [x] PRD maps the approved endpoint set to consumer identity, scopes,
  underlying permissions, data minimization, complete seven-day snapshot
  reconciliation, and explicit out-of-scope routes.
- [ ] Credential lifecycle is testable: issue, one-time reveal, rotate,
  365-day expiry, 24-hour rotation overlap, revoke, and rejected use after
  revoke; no plaintext secret persists or appears in logs.
- [ ] Backend authorization is default-deny and distinguishes missing,
  inactive, expired, revoked, and insufficient-scope credentials using the
  approved error contract without exposing sensitive details.
- [ ] Quota/rate-limit policy names limits, windows, burst behavior, atomic
  enforcement, response headers, `429` body, and `Retry-After`; V1 enforces
  the approved 60/minute + 20 burst data bucket, 5/minute token limit, and
  100-record page maximum without partial business changes.
- [ ] Call-audit policy records approved success and rejection events with
  consumer/credential/request/operation/status metadata, redacts secrets,
  headers, query values and raw payloads, retains records for 90 days, limits
  readers to controlled operations database access, and correlates with D-002/
  D-003 without duplicating semantic-change evidence.
- [ ] External API versioning, OpenAPI publication, error/pagination contract,
  90-day deprecation/sunset rules, and developer/operations documentation are
  reviewed; role ownership is assigned with named contacts before activation;
  current SPA `/api/v1` and generated client behavior remain compatible.
- [ ] The role owners assign named contacts and support channels before feature
  enablement or credential issuance.
- [x] Design and implementation plan include migration, feature gate,
  monitoring, emergency revocation, and rollback that leaves SPA access and
  existing audit evidence intact.
- [x] `e2e-api-tests.md` covers setup data, token/credential flows, allowed and
  denied endpoint calls, quota rejection, persistence, audit rows, successful
  complete-window reconciliation inputs, and failure-side-effect assertions
  against an isolated environment.

## Out Of Scope

- Implementing the consumer API, credential store, rate limiter, or developer
  portal in this planning task.
- Generic public exposure of the current SPA API, user password login for
  machine consumers, or consumer impersonation of human users.
- Raw database, filesystem, shell, network, private-service, retired AI/MCP,
  or generic workflow capabilities.
- Multi-tenant/organization data isolation, arbitrary user-defined scopes,
  billing, marketplace publication, or a full API gateway unless the approved
  first-consumer contract explicitly requires a separately planned slice.
