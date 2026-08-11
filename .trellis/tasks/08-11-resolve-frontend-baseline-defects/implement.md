# Implementation Plan: Resolve Frontend Baseline Runtime and UI Defects

## 1. Establish Reproductions

- Start the documented isolated backend, Redis, Celery worker, and mailbox.
- Capture recovery outbox state, worker logs, SMTP connection result, IAM
  catalog, and browser network/DOM evidence for the three UI interactions.
- Confirm every repair is a product/runtime defect rather than a stale test
  locator before changing source.

## 2. Repair Runtime Contracts

- Correct the smallest configuration, startup, or worker defect that prevents
  recovery delivery.
- Reconcile scheduler permission seed state through the canonical backend
  bootstrap or a forward-only migration, then test the administrator's normal
  authorized path.

## 3. Repair UI Contracts

- Fix the proven inventory feedback/select lifecycle issue and add focused
  regressions using visible controls.
- Fix the proven user-delete feedback/list-refresh lifecycle issue and add a
  focused regression.

## 4. Verify

- Run focused backend tests for IAM bootstrap and email delivery behavior.
- Run focused Playwright password recovery, scheduler, inventory, and admin
  specs against the documented local stack.
- Run relevant TypeScript, Biome, frontend build, backend quality checks,
  task validation, spec lint, and `git diff --check`.

## Risky Files and Rollback Points

- Backend bootstrap/migration and Celery configuration: protect existing users,
  roles, outbox retry semantics, and deployment startup.
- Inventory Select and mutation feedback: protect normal document pagination
  and correction routing.
- User-delete mutation feedback: protect confirmation, error handling, and
  table invalidation.
- Do not start implementation until this plan receives explicit approval.
