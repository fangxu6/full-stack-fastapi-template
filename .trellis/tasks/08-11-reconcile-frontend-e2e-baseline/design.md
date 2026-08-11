# Technical Design: Reconcile Frontend E2E Baseline

## Boundaries

This task owns Playwright test infrastructure, E2E fixtures, and assertions
that disagree with current documented behavior. It does not alter the
production email outbox, SMTP worker, scheduler authorization, inventory
ledger rules, or the completed frontend directory migration unless a focused
reproduction proves a product defect.

## Mailbox Lifecycle

Add a small Node/Bun standard-library test mailbox under `frontend/tests/utils`.
It will:

1. accept the SMTP commands emitted by the existing `emails` client on a
   configurable loopback port (`E2E_SMTP_PORT`, with a deterministic default);
2. retain messages in memory and expose only the existing helper contract:
   `GET /messages` and `GET /messages/:id.html`;
3. decode the minimal nested multipart shape (including Base64 and
   quoted-printable transfer encodings) needed to return the reset-link HTML;
   and
4. report its chosen HTTP/SMTP endpoints to the Playwright process.

`globalSetup` starts the mailbox before workers begin; `globalTeardown` closes
the HTTP and SMTP listeners and kills the child only if startup succeeded.
Tests continue to use `findLastEmail`, so the mailbox is a test-only transport
replacement, not a product API. The E2E run documents matching backend
`SMTP_HOST`, `SMTP_PORT`, `SMTP_TLS=False`, `SMTP_SSL=False`, and a local
`MAILCATCHER_HOST`. The existing Celery worker remains the delivery process;
the setup guide will state that it must use the same isolated environment.

## Deterministic Fixtures

- Keep unique-value helpers, but create every required processing/receiving
  unit through the existing inventory API helper.
- Replace the finished-shipment dependency on an arbitrary pre-existing
  balance with a fixture sequence that creates the smallest valid finished
  ledger balance through the existing document contract, then uses that exact
  returned identity for shipment and balance assertions.
- Create scheduler jobs with a user whose bootstrap roles include
  `scheduler.jobs.manage`. The setup path must verify the permission through the
  current permissions API rather than bypassing the route guard or hard-coding
  a database row in the browser test.
- Keep the high-cardinality processing-unit test scoped to its own unique
  prefix and clean up via the existing isolated database lifecycle.

## Assertion Reconciliation

Re-run each of the five account/settings failures serially. For each case,
compare the visible notification/form state with the current page component and
API response contract. Update only the test locator or wait condition when the
product behavior is correct. If a component/API defect is proven, add the
smallest production fix and a focused regression test, preserving existing
toast provider behavior.

## Compatibility And Rollback

- The mailbox is test-only and has no runtime import path from `backend/app` or
  production frontend code.
- Existing `MAILCATCHER_HOST` users can override the mailbox URL for debugging,
  while the default test command starts the local fixture.
- Roll back by removing the mailbox lifecycle/helper changes and fixture
  changes together; no schema or migration rollback is expected.

## Risks And Deferred Items

- A minimal SMTP parser must reject malformed input cleanly and bound message
  size; it is not a general-purpose mail server. The implementation should
  state this test-only ceiling in a short `ponytail:` comment.
- Full 78-case verification still needs PostgreSQL, Redis, the backend, and the
  existing Celery worker. This task removes the Docker/mailbox prerequisite but
  does not replace those runtime services.
