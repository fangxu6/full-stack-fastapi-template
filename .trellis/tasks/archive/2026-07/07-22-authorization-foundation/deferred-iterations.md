# RBAC Deferred Iterations

## Purpose

This register preserves RBAC extensions that are valuable but cannot be
defined safely from the current system's roles, resources, and data model.
They are outside D-001's functional, system-wide inventory authorization
release.

## Traceability Rules

- Deferred items do not fail D-001 acceptance criteria.
- Each item requires its own Trellis task before implementation.
- A dependent item may start only after its stated prerequisite or an approved
  replacement design is complete.

## Deferred Items

| ID | Deferred Scope | Reason | Dependencies | Future Deliverables |
| --- | --- | --- | --- | --- |
| D-001 | Organization and department data scopes | No organization or department model currently defines a trustworthy inventory visibility boundary. | Stable D-001 permission service; product-defined organization model | Scope model, migrations, query predicates, ownership rules, E2E tests. |
| D-002 | Row-level and field-level inventory restrictions | Processing-unit and creator fields exist, but no approved policy says which role may see or change which rows or fields. | D-001; D-001 scope model where applicable | Policy matrix, redaction contract, service enforcement, tests. |
| D-003 | Role hierarchy, static/dynamic separation of duties, and role activation | The first three roles have no approved inheritance or mutually exclusive duties. | Stable role administration and a concrete conflicting-duty workflow | Constraint model, assignment/session rules, migration, tests. |
| D-004 | Tenant, environmental, and external-consumer policy | The deployment is not a multi-tenant or external-consumer authorization product. | D-005 External API boundary from the parent backlog | Tenant/client identity model, policy contract, operational validation. |
| D-005 | Template Items, AI query, and `is_superuser` retirement | These existing paths use the legacy superuser and ownership rules and have no approved permission matrix in this release. | Stable D-001 RBAC service and a product-approved Item/AI access matrix | Permission migration, compatibility removal, API/client changes, tests, rollback. |

## Suggested Iteration Order

1. D-001 Organization and department data scopes
2. D-002 Row-level and field-level inventory restrictions
3. D-003 Role hierarchy and separation of duties
4. D-004 Tenant and external-consumer policy
5. D-005 Legacy Items and AI migration

## Carry-Forward Acceptance Notes

- A data-scope task must identify the business owner of each scoped inventory
  record and define allowed versus denied query and mutation cases.
- A role-constraint task must name a real conflicting-duty workflow before
  adding static or dynamic separation rules.
- A tenant/client-policy task must not reuse internal browser-session roles as
  an external API credential model.

## Remaining Work In Current Scope

The current task still needs decisions on administrator assignment rules, the
final permission matrix, and the user/role-management experience before its
design and implementation plan can converge.
