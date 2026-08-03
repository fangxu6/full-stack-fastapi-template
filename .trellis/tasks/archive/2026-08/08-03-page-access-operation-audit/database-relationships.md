# Semantic change audit database relationships

## Status and scope

This is the target schema for D-003. `audit_event` does not exist yet. It is
one reusable application-level semantic-change table; this IAM slice is its
first writer. It does not create a page-access store, authorization-decision
store, query API, reader UI, audit-specific scheduler job, or database trigger.

## Table inventory

| Object | Status | Ownership | Purpose |
| --- | --- | --- | --- |
| `audit_event` | New | Audit module | Append-only application evidence for successful semantic changes. |
| `user` | Existing | Core identity | Supplies an actor or user-resource identifier. |
| `iam_role` | Existing | IAM | Supplies role resources referenced by IAM actions. |
| `iam_permission` | Existing | IAM | Supplies permission codes summarized by a role-permission replacement. |
| `iam_user_role` | Existing | IAM | Supplies before/after role IDs for a user-role replacement. |

## Logical relationship diagram

```text
                     existing user
                  +----------------+
                  | id (UUID)      |
                  +----------------+
                         . . . actor_user_id (no FK)
                         . . . resource_id for iam_user (no FK)

 existing iam_role              +--------------------------------+
 +----------------+             | new audit_event                |
 | id (BIGINT)    | . . . . .>  | id, occurred_at                |
 +----------------+ resource_id | actor_user_id, request_id      |
                                | action, resource_type/id       |
 existing iam_permission        | changes (allowlisted JSONB)    |
 +----------------+ . . . . .>  +--------------------------------+
 | code (TEXT)    | changes
 +----------------+

 existing iam_user_role
 +----------------+
 | user_id, role_id| . . . . .> changes.role_ids before/after
 +----------------+
```

All dashed links are logical references, not physical foreign keys. Deleting a
user or role must not erase, null, or block its prior semantic-change event.

## `audit_event` column contract

| Column | Type | Null | Physical relation | Purpose |
| --- | --- | --- | --- | --- |
| `id` | `BIGINT GENERATED ALWAYS AS IDENTITY` | No | Primary key | Stable event identifier. |
| `occurred_at` | `TIMESTAMPTZ` | No | None | UTC event time and retention key. |
| `actor_user_id` | `UUID` | Yes | No FK | Authenticated actor UUID; null is reserved for a future non-user writer. |
| `request_id` | `TEXT` | Yes | None | Server-generated HTTP correlation ID; null is reserved for a future non-HTTP writer. |
| `action` | `VARCHAR(128)` | No | None | Namespaced semantic action owned by code. |
| `resource_type` | `VARCHAR(64)` | No | None | Namespaced primary-resource kind. |
| `resource_id` | `VARCHAR(128)` | No | No FK | UUID or BIGINT resource identifier stored as text. |
| `changes` | `JSONB` | No | JSONB-object check | Per-action allowlisted change summary. |

`action` and `resource_type` are not PostgreSQL enums or lookup tables. They
are code-owned, extensible vocabulary rather than user-managed persisted
states. Each new writer supplies stable strings and a focused test for its
summary allowlist.

## IAM action and summary contract

| Action | Resource | Summary |
| --- | --- | --- |
| `iam.role.created` | `iam_role` / role ID | `code`, `permission_codes` |
| `iam.role.updated` | `iam_role` / role ID | `changed_fields` only |
| `iam.role.activated` | `iam_role` / role ID | `is_active` before/after |
| `iam.role.deactivated` | `iam_role` / role ID | `is_active` before/after |
| `iam.role.permissions_replaced` | `iam_role` / role ID | permission-code lists before/after |
| `iam.role.deleted` | `iam_role` / role ID | empty object |
| `iam.user.roles_replaced` | `iam_user` / user UUID | role-ID lists before/after |

The summary never contains a request body, free-text role description,
password, token, email address, full name, or generic row snapshot.

## Indexes, retention, and rollback

| Index | Key | Primary use |
| --- | --- | --- |
| `ix_audit_event_occurred_at` | `occurred_at DESC` | Retention deletion and timeline inspection. |
| `ix_audit_event_actor_time` | `actor_user_id, occurred_at DESC` | Investigate one actor. |
| `ix_audit_event_resource_time` | `resource_type, resource_id, occurred_at DESC` | Investigate one role or user. |

The direct Celery Beat cleanup deletes rows where `occurred_at` is older than
365 days. It has no database relationship to scheduler tables. The migration
adds Chinese comments to the table and columns only. Downgrade refuses while
the table contains rows; normal application rollback leaves records intact.
