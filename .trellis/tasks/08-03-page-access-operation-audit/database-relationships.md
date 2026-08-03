# IAM audit target database relationships

## Status and scope

This is the target schema for D-003 planning. `audit_event` and its PostgreSQL
enum types do not exist yet. This document describes the single new table and
its relationships to existing IAM and scheduler tables; it does not authorize
the migration or application implementation.

## Table inventory

| Object | Status | Ownership | Purpose |
| --- | --- | --- | --- |
| `audit_event` | New | Audit module | Immutable, queryable evidence for the IAM audit vertical slice. |
| `user` | Existing | Core identity | Supplies the current actor or IAM user resource. |
| `iam_role` | Existing | IAM | Supplies role resources referenced by role operations. |
| `iam_permission` | Existing | IAM | Supplies permission codes referenced by decisions and role changes. |
| `iam_user_role` | Existing | IAM | Represents the role assignment changed by `iam_user_roles_replace`. |
| `scheduler_job` | Existing | Scheduler | Will host the planned daily audit-retention job. |
| `scheduler_run` | Existing | Scheduler | Records execution of that retention job. |

The new PostgreSQL enum types are database types, not tables:
`audit_event_type`, `audit_event_source`, `audit_event_outcome`,
`audit_event_result_code`, `audit_page_code`, `audit_operation_code`,
`audit_resource_type`, and `audit_actor_kind`.

## Logical relationship diagram

```text
                     existing user
                  +----------------+
                  | id (UUID)      |
                  +----------------+
                         . . . actor_user_id (no FK)
                         . . . resource_id when resource_type=iam_user (no FK)

 existing iam_role             +------------------------------+
 +----------------+            | new audit_event              |
 | id (BIGINT)    | . . . . .> | id (BIGINT identity)         |
 +----------------+ resource_id| occurred_at (UTC)            |
                                | actor_user_id (UUID, null)   |
 existing iam_permission        | event/source/outcome (enums) |
 +----------------+            | page/permission/operation    |
 | code (TEXT)    | . . . . .> | resource_type/resource_id     |
 +----------------+ permission | request_id/result_code        |
                                | change_summary (JSONB)       |
 existing iam_user_role         +------------------------------+
 +----------------+                 . . . no row-level FK
 | user_id        |                 . . . summary contains role IDs only
 | role_id        |
 +----------------+

 planned row in existing         existing scheduler_run
 scheduler_job
 +----------------+              +----------------+
 | class_path =   | 1 ------ *   | job_id (FK)    |
 | AuditRetention |              +----------------+
 +----------------+
          |
          | invokes cleanup_expired_events()
          v
    DELETE FROM audit_event WHERE occurred_at < cutoff
```

Dashed links are logical evidence references, not physical foreign keys.
The only physical relationship shown above is the existing
`scheduler_run.job_id -> scheduler_job.id` foreign key.

## `audit_event` column contract

| Column | Type | Null | Physical relation | Logical relation / purpose |
| --- | --- | --- | --- | --- |
| `id` | `BIGINT GENERATED ALWAYS AS IDENTITY` | No | Primary key | Stable audit-event identifier. |
| `occurred_at` | `TIMESTAMPTZ` | No | None | UTC evidence time and retention cutoff key. |
| `actor_user_id` | `UUID` | Yes | No FK by design | Current actor maps logically to `user.id`; null for anonymous denials. |
| `actor_kind` | `audit_actor_kind` | No | Enum type | Distinguishes `anonymous`, `user`, and `system`. |
| `event_type` | `audit_event_type` | No | Enum type | Page access, authorization, or privileged operation. |
| `source` | `audit_event_source` | No | Enum type | Frontend guard, backend permission, or backend operation. |
| `outcome` | `audit_event_outcome` | No | Enum type | `succeeded`, `denied`, or `failed`; never a boolean. |
| `page_code` | `audit_page_code` | Yes | Enum type | Stable IAM page identifier, not a browser URL. |
| `permission_code` | `TEXT` | Yes | No FK by design | Historical code maps logically to `iam_permission.code`. |
| `operation_code` | `audit_operation_code` | Yes | Enum type | Stable IAM mutation identifier. |
| `resource_type` | `audit_resource_type` | Yes | Enum type | Selects the meaning of `resource_id`. |
| `resource_id` | `TEXT` | Yes | No FK by design | Historical ID maps to `iam_role.id` or `user.id` by `resource_type`. |
| `request_id` | `TEXT` | Yes | None | Correlates to the structured-observability request context. |
| `result_code` | `audit_event_result_code` | Yes | Enum type | Stable success, denial, validation, conflict, or transaction result. |
| `change_summary` | `JSONB` | Yes | None | Whitelist-only committed-change summary; never raw request data. |

`audit_event` is append-only. It has no `created_by`, `updated_by`,
`is_deleted`, or soft-delete state because the row itself is the immutable
evidence record and expiration is a permanent 365-day deletion policy.

## Relationship rules

### Actor to user

`audit_event.actor_user_id` is intentionally not an FK to `user.id`. A user
may be deleted after an audit event is created, but the audit event must keep
the UUID that identified the actor at the time. Query code may enrich a current
user display name when the row still exists, but cannot require it.

### Resource to IAM objects

`resource_type` determines the target of `resource_id`:

| Resource type | `resource_id` format | Logical target |
| --- | --- | --- |
| `iam_page` | Audit page enum value | IAM users or roles page. |
| `iam_role` | Decimal BIGINT encoded as text | `iam_role.id`. |
| `iam_user` | UUID encoded as text | `user.id`. |

The writer validates these mappings before insertion. No FK is used because
role or user deletion must not delete, null, or block historic evidence.

`permission_code` records the code evaluated at the time, rather than a
permission ID, because historical events must remain interpretable if the
permission catalogue changes. `iam_user_role` is not referenced by event ID;
user-role replacement stores the affected user as the resource and role IDs in
the allowlisted summary.

### Audit retention to scheduler

The planned `AuditRetentionTask` is an application class, not a new database
table. Its planned default row in the existing `scheduler_job` table invokes
`cleanup_expired_events()` daily, and the existing `scheduler_run` table
retains operational execution history through its current FK to
`scheduler_job`. Neither scheduler table has an FK to `audit_event`; cleanup
must be able to delete expired events independently and idempotently.

## Indexes and query paths

| Index | Key | Primary use |
| --- | --- | --- |
| `ix_audit_event_occurred_at` | `occurred_at DESC` | Default newest-first audit timeline and expiry scan. |
| `ix_audit_event_actor_time` | `actor_user_id, occurred_at DESC` | Investigate one actor's actions. |
| `ix_audit_event_resource_time` | `resource_type, resource_id, occurred_at DESC` | Investigate a role or user resource. |
| `ix_audit_event_type_outcome_time` | `event_type, outcome, occurred_at DESC` | Filter page access, denial, and operation outcomes. |

All new object names use the `audit_` domain prefix, and the migration must add
the required Chinese comments to the table, columns, enum types, indexes, and
constraints.

## Migration and deletion order

Upgrade creates the enum types first, then `audit_event`, indexes, and
comments. The guarded downgrade first verifies that `audit_event` is empty;
only then may it drop the table and its enum types. It must refuse rather than
discard evidence when rows exist.

Normal record deletion happens only through the 365-day cleanup service. It
deletes expired `audit_event` rows in bounded batches and does not cascade to
or from any existing table.
