# Implementation Plan: Reconcile Frontend E2E Baseline

## 1. Mailbox Test Infrastructure

- Add the ephemeral SMTP + HTTP mailbox and its Playwright global setup/teardown.
- Preserve the current `findLastEmail` API and reset-link HTML behavior.
- Add startup failure, bounded message size, port collision, and teardown
  handling without touching production email code.

## 2. E2E Environment And Fixtures

- Update the Playwright guide with the no-Docker mailbox configuration and the
  matching backend/Celery worker environment.
- Add deterministic scheduler permission/bootstrap verification.
- Build the minimal finished-inventory fixture through existing inventory
  endpoints and make the three inventory cases independent of shared rows and
  ordering.

## 3. Assertion Reconciliation

- Reproduce the admin delete, signup existing-email, and user-settings failures
  serially against the current UI/API contract.
- Correct stale or timing-sensitive test assertions only; add a focused product
  regression test only for a proven implementation defect.

## 4. Validation

- Run focused mailbox, reset-password, inventory, scheduler, admin, signup, and
  user-settings specs while the isolated backend, PostgreSQL, Redis, and Celery
  worker are running.
- Run `bunx playwright test --project=chromium` and record all 78 cases.
- Run frontend Biome/build, relevant backend tests, quality hooks, task checks,
  `git diff --check`, and spec lint. Do not rerun unrelated full E2E variants.

## Risky Files And Rollback Points

- `frontend/playwright.config.ts` and `frontend/tests/*setup*`: process
  lifecycle and environment propagation.
- `frontend/tests/utils/*mail*` and `frontend/tests/reset-password.spec.ts`:
  SMTP/MIME parsing and token extraction.
- `frontend/tests/inventory.spec.ts` and `frontend/tests/scheduler.spec.ts`:
  fixture isolation and authorization assumptions.
- `docs/rules/Playwright E2E 配置与运行教程.md`: operator contract.
- Production files are changed only after a failing assertion is proven to be a
  real product defect.

## Verification Record (2026-08-11)

- TypeScript (`bunx tsc -p tsconfig.json --noEmit`) passes.
- Targeted Biome passes for the mailbox, setup, inventory, signup, auth, and
  `UserProfileCard` changes; frontend production build passes.
- The mailbox self-check sends a complete SMTP DATA payload in one socket
  chunk, verifies `/messages` and nested multipart Base64 HTML decoding, and
  confirms loopback listener cleanup.
- Playwright lists all 78 Chromium cases; the full run is blocked by the
  unavailable isolated PostgreSQL/backend/Redis/Celery environment and has not
  been claimed as passing.
- Quality-hook tests pass (`19 passed`), task context validation passes, spec
  lint reports 0 errors and 0 warnings, and `git diff --check` passes apart from
  existing CRLF normalization warnings.
- The user-settings baseline exposed a real async form-initialization defect:
  `UserProfileCard` now resets its form when `currentUser` arrives. Existing
  profile save/cancel E2E cases cover the regression; they remain runtime-gated
  until the isolated stack is available.

## Follow-up Verification (2026-08-11)

- The scheduler bootstrap now probes the permission catalog before creating the
  temporary `e2e_scheduler` role. On the current local database the catalog is
  still the older ten-permission seed, so non-scheduler tests continue instead
  of failing during global setup; scheduler failures remain visibly tied to
  this task.
- Serial account/settings rerun: `37 passed / 1 failed`. The remaining admin
  delete toast assertion is the pre-existing baseline case; the production
  component still calls the established success-toast contract.
- Focused reset-password, inventory, and scheduler rerun: `7 passed / 7
  failed`. Failures are the documented Celery/SMTP delivery gap, stale/shared
  inventory UI/data baseline, and absent scheduler permissions. The repository
  mailbox started and tore down successfully for this run.
- Per the parent-task decision, the full 78-case browser suite was not rerun.
  Full-suite acceptance remains pending an isolated PostgreSQL, Redis,
  backend, and Celery environment with the current permission seed.
- Quick final checks pass: TypeScript no-emit, targeted Biome, frontend build,
  mailbox startup/HTTP self-check/teardown, quality hooks (`19 passed`),
  frontend component policy, task validation, spec lint (`0 errors, 0
  warnings`), and `git diff --check` (only existing CRLF normalization
  warnings).
