# State Transition Design Guidelines

> 领域本地化状态与事件，统一可读、可审查、可测试的迁移契约。

## 1. Scope / Trigger

Apply this rule to a `modules/*` DDD design when a persistent or durable object has finite business lifecycle values and one or more of these characteristics:

- the current value restricts the next business action;
- transitions have explicit business events, terminal outcomes, retry, recovery, or lease semantics;
- permissions, optimistic timestamps, row locks, or concurrency affect whether a transition is legal;
- one command changes multiple entities or writes business/audit side effects atomically.

Do not require a matrix for every enum. A closed classification, trigger source, strategy, role, or error category is an enum when its current value does not define a lifecycle edge. A true binary fact or technical switch may remain a boolean under the database rules.

The matrix is a design contract, not a workflow runtime or a database table. Existing workflows may be documented without being refactored. See the [unified state transition design](../../../docs/state-machine-unified-transition-design.md) for the current project backfill.

## 2. Signatures / Naming

Use repository-relative names and keep them in the owning domain:

| Artifact | Required form |
| --- | --- |
| Design section | `## 状态迁移矩阵（State Transition Matrix）` |
| Matrix heading | `<domain>.<aggregate> 状态迁移矩阵` |
| New state type | `<Aggregate>State` |
| Existing state type | Keep an accurate `<Aggregate>Status`; do not rename only for this convention. |
| Event type | `<Aggregate>Event` with verb values such as `APPROVE`, `CLAIM`, `DELIVER`. |
| Optional code map | `<AGGREGATE>_TRANSITIONS`, only inside the owning domain when code validation consumes it. |

The matrix must use exactly these columns: `当前状态`, `事件`, `目标状态`, `前置条件`, `副作用`, `幂等/并发语义`.

An event may remain a domain service command when an event enum would add no value. The naming convention does not require new runtime types. `(新建)` and `不变/拒绝` are documentation markers, never persisted enum members.

## 3. Contracts

### Domain ownership

- Keep state types, event/command definitions, matrices, and transition services in the owning domain module.
- Use the smallest aggregate-local matrix that explains the lifecycle. Never create a global `ALL_TRANSITIONS`, cross-domain state enum, or registry that executes arbitrary callbacks.
- A state machine's state may and usually should be a local `StrEnum` shared by the model, schema, and named PostgreSQL enum. The matrix defines legal edges; it does not replace that value contract.

### Transition semantics

- A matrix describes structural edges: `current state + domain event -> target state`.
- List business authorization, target existence, expected timestamps/hashes, data integrity, retry limits, lease validity, and other preconditions explicitly. A matrix does not replace service validation.
- List every cross-entity update, audit event, external call boundary, and timestamp/lease change in `副作用`.
- State changes across multiple durable entities belong to one domain service transaction unless the design explicitly documents a committed handoff and recovery protocol.
- Use row locks, `SKIP LOCKED`, optimistic tokens, lease tokens, unique constraints, or another concrete mechanism where concurrency requires it. State names alone do not establish concurrency safety.
- Define duplicate commands and stale worker results as idempotent no-ops, stable conflicts, or safe retries. Do not leave their behavior implicit.
- Identify terminal states and whether recovery reopens the same object or creates a new attempt/version. Do not silently add an outgoing edge from a terminal state.

### Persistence and API

Persisted business states continue to follow [Database Guidelines](./database-guidelines.md): named `StrEnum`, named PostgreSQL enum, forward migrations for new values, Chinese database comments, and one shared enum contract through public schemas. Do not create a status table just because a matrix exists.

## 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Field is a closed category/source/strategy/role/error category | Use a domain-local enum; no matrix is required. |
| Field is a simple lifecycle value with no multi-step, retry, recovery, concurrency, or cross-entity semantics | Use a state enum and domain method; record why a matrix is unnecessary. |
| DDD workflow meets the trigger in Section 1 | Design document includes one or more aggregate-local matrices before implementation. |
| Event is not legal from the current state | Domain service rejects it with the domain's stable conflict/error contract; no partial state or side effect is committed. |
| Business precondition fails while a structural edge exists | Keep the current state unchanged unless the domain explicitly defines a committed business outcome such as `STALE`; record the precondition in the matrix. |
| Multiple entities change in one transition | Domain service owns one transaction and documents lock order and side effects. |
| Lease expires or a worker result is stale | Use the documented recovery/terminal edge and lease/version comparison; a stale result cannot overwrite a newer attempt. |
| New persisted state is added | Update the named PostgreSQL enum through a forward Alembic migration before application code persists it. |
| A second domain appears to share the same lifecycle mechanism | Prove the repeated boundary in a separate design task; do not promote the local matrix into a runtime registry by default. |

## 5. Good / Base / Bad Cases

### Good

`PENDING_REVIEW + APPROVE -> APPROVED` is documented in `inventory.correction_request`, with reviewer permission, target timestamp check, creation of WorkItem/Attempt, transaction owner, and duplicate approval behavior.

### Base

`SchedulerRunTrigger.MANUAL_NOW` remains an enum-only trigger classification. `SchedulerRunStatus` remains the persisted status enum, while its claim, lease, result, cancellation, and terminal behavior are documented in a scheduler-local matrix.

### Bad

```python
ALL_TRANSITIONS = {
    "PENDING": {"APPROVE": "APPROVED"},
    "RUNNING": {"DELIVER": "DELIVERED"},
}
```

This loses domain meaning, mixes unrelated states, and cannot express permissions, transaction ownership, lease tokens, or cross-table effects. A matrix does not justify a global executable map.

## 6. Tests Required

For every workflow matrix, tests must assert the applicable subset of:

- legal edge reaches the documented target state;
- illegal edge returns the stable domain error and leaves all affected rows unchanged;
- terminal state is not reopened or mutated by duplicate commands;
- retry, lease expiry, recovery, or attempt creation follows the documented edge;
- duplicate delivery, duplicate task messages, stale worker results, and repeated API commands are idempotent;
- concurrent claim/approval/recovery honors row locks, unique constraints, optimistic tokens, or lease tokens;
- multi-table transitions commit all required rows and audit data together, or follow an explicitly documented handoff protocol.

The test file should name the matrix heading or transition event in the test description so a future state change has an obvious review surface. Do not add tests for a plain enum solely because it has members.

## 7. Wrong vs Correct

### Wrong

```python
COMMON_STATUS = StrEnum("CommonStatus", {"RUNNING": "RUNNING", "FAILED": "FAILED"})
ALL_TRANSITIONS = {"RUNNING": {"FINISH": "FAILED"}}
```

It merges scheduler execution, correction application, and email delivery semantics and makes the shared map appear authoritative.

### Correct

```text
email.outbox 状态迁移矩阵
LEASED + DELIVER_SUCCESS -> DELIVERED
前置条件: result lease token matches the active lease
副作用: clear lease, set delivered_at, clear error
幂等/并发语义: stale worker result is a no-op
```

The state enum remains owned by Email Outbox, and the domain service owns the lock, transaction, SMTP boundary, and result handling.

## Related Rules

- [Backend Guidelines Index](./index.md)
- [Database Guidelines](./database-guidelines.md)
- [Directory Structure](./directory-structure.md)
- [Code Reuse Thinking Guide](../guides/code-reuse-thinking-guide.md)
