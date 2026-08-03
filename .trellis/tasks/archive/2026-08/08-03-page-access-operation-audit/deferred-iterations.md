# Semantic Change Audit Deferred Iterations

## Purpose

The current delivery is limited to durable successful IAM semantic changes.
This register preserves confirmed follow-up scope without expanding the
current task's acceptance criteria.

## Traceability Rules

- Deferred items do not fail the current task's acceptance criteria.
- Each item needs an independent task before implementation.
- A future writer reuses `audit_event` only after defining action codes,
  summary allowlists, reader exposure, and proportionate tests.

## Deferred Items

| ID | Deferred Scope | Reason | Dependencies | Future Deliverables |
| --- | --- | --- | --- | --- |
| D-001 | Page-access and frontend route-guard events | Browser navigation is not the current internal accountability need. | Reusable event table | PRD, capture contract, API/client flow, UI and tests. |
| D-002 | Backend authorization-denial and failed-mutation events | Failed transaction persistence has different transaction and failure semantics. | Reusable event table, explicit failure policy | PRD, result taxonomy, capture boundary, tests. |
| D-003 | Application reader API, audit UI, and export | V1 has no approved reader role or operational workflow for this sensitive data. | Reader authorization and redaction policy | PRD, API/UI design, pagination, export controls, tests. |
| D-004 | Database triggers, privilege separation, or external immutable sink | Raw-row capture and tamper resistance require a defined threat/compliance model. | Security owner and operational database design | Threat model, privilege design or sink contract, migrations, tests, runbook. |
| D-005 | Inventory, scheduler, and future-module writers | Each domain needs its own action vocabulary and summary allowlists. | Proven IAM writer pattern | Domain PRD, actions, capture boundary, tests. |

## Suggested Iteration Order

1. D-005 only when a concrete high-value domain change needs attribution.
2. D-003 when an approved internal reader workflow needs application access.
3. D-001 or D-002 when investigation needs page/denial evidence.
4. D-004 only when the stated application-level immutability boundary is
   insufficient for a documented threat or compliance requirement.

## Carry-Forward Acceptance Notes

- Browser-reported events must remain distinct from server-authoritative events.
- A reader or export proposal must explicitly prohibit sensitive summaries and
  define authorization, pagination, and retention behavior.
- A trigger or external sink proposal must show how it obtains application actor
  identity and avoids raw sensitive data.

## Remaining Work In Current Scope

The current task remains in planning until the product owner approves the
revised PRD, design, implementation plan, and E2E cases, then explicitly
requests `task.py start`.
