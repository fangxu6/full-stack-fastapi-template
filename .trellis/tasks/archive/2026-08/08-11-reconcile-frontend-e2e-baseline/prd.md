# Reconcile frontend E2E baseline failures

## Goal

Remove E2E-harness prerequisites and classify the baseline failures observed
while validating the legacy-directory migration. Product and runtime defects
discovered during that classification are owned by the independent
[`08-11-resolve-frontend-baseline-defects`](../08-11-resolve-frontend-baseline-defects/prd.md)
task, not by this archived harness task.

## Confirmed Facts

- The 2026-08-11 local run completed 65 of 78 cases. The path-only migration
  did not alter the moved toast implementation or the affected components'
  behavior; the failures remain this task's scope.
- Two recovery cases query `MAILCATCHER_HOST` directly
  (`frontend/tests/utils/mailcatcher.ts:16`), but the E2E guide starts neither
  SMTP nor a mailbox UI and local port `1080` is unavailable.
- Recovery HTTP success means a durable email outbox request was created; SMTP
  delivery is asynchronous and is not part of the HTTP contract
  (`docs/adr/0009-use-generic-email-outbox-for-non-report-mail.md:15-30`).
- Three inventory cases depend on pre-existing or high-cardinality master and
  balance data (`frontend/tests/inventory.spec.ts:46-64`, `167-197`), and
  three scheduler cases need `scheduler.jobs.manage`, which controls the page
  actions (`frontend/src/features/scheduler/pages/SchedulerJobsPage.tsx:137-140`).
- Five remaining failures are one admin delete notification, three user-settings
  notification/form-display assertions, and one existing-email signup assertion.
- The agreed mail strategy is a repository-owned ephemeral SMTP/mailbox
  fixture. Playwright starts it for the run, exposes only the Mailcatcher-shaped
  endpoints the recovery tests need, and stops it during teardown. No Docker or
  machine-global mail binary is required.

Detailed reproduction and anchors are in
[`research/e2e-baseline-evidence.md`](research/e2e-baseline-evidence.md).

## Outcome And Handoff

- A repository-owned loopback SMTP/HTTP mailbox now starts and stops with the
  Playwright run, keeps the existing Mailcatcher-shaped helper API, and handles
  the bounded MIME shape emitted by the current email client.
- Inventory tests create their own finished-balance fixture rather than relying
  on pre-seeded shipment data. Signup assertions were reconciled, and the
  `UserProfileCard` async initialization defect was fixed with existing profile
  regression coverage.
- The remaining two password-recovery delivery failures, three scheduler
  permission failures, two inventory UI failures, and one user-delete feedback
  failure were reproduced and transferred to
  [`08-11-resolve-frontend-baseline-defects`](../08-11-resolve-frontend-baseline-defects/prd.md).
  They require runtime/bootstrap or product UI repair; they are not defects in
  the E2E mailbox, fixture ownership, or frontend directory migration.

## Acceptance Criteria

- [x] Playwright starts and tears down a Docker-free, loopback-only temporary
      mailbox without changing production email behavior.
- [x] E2E inventory fixtures no longer require a pre-existing finished balance,
      and the auth setup does not block unrelated cases when an older database
      lacks scheduler permission rows.
- [x] The signup assertion and `UserProfileCard` initialization contract were
      reconciled through focused browser runs.
- [x] All remaining failures are recorded with reproduction evidence and
      explicitly owned by `08-11-resolve-frontend-baseline-defects`.
- [x] The parent migration's moved implementations remain unchanged except for
      the narrowly proven `UserProfileCard` defect.

## Closeout

This task is complete. Full-suite E2E success is deliberately not claimed:
the remaining defects are no longer this task's acceptance scope and will be
verified by the independent repair task after its approved implementation.
