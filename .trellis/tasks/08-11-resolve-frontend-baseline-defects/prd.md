# Resolve frontend baseline runtime and UI defects

## Goal

Resolve four runtime and UI defects that were exposed by the frontend E2E
baseline but are not owned by its test-mailbox or fixture infrastructure. The
result is a supported local runtime contract and stable product feedback for
password recovery, scheduler management, inventory documents, and user
administration.

## Confirmed Facts

- Password recovery persists an outbox request and Celery delivers it through
  SMTP; the HTTP response is not a delivery guarantee. The repository-owned
  mailbox starts and stops correctly, but the current backend/worker process
  is not delivering to its loopback SMTP endpoint.
- The source permission catalog includes `scheduler.jobs.read` and
  `scheduler.jobs.manage` in
  [`backend/app/modules/iam/constants.py`](../../../backend/app/modules/iam/constants.py),
  while the current running database exposes only the older ten-code catalog.
  `init_db()` calls `ensure_bootstrap_state()`, which is the canonical seed
  reconciliation boundary.
- Inventory document deletion invokes Ant Design `message.success("单据已软删除")`
  in
  [`frontend/src/features/inventory/pages/InventoryDocumentsPage.tsx`](../../../frontend/src/features/inventory/pages/InventoryDocumentsPage.tsx).
  Its remote unit filter is driven by the debounced
  [`frontend/src/features/inventory/unit-select-options.ts`](../../../frontend/src/features/inventory/unit-select-options.ts).
- User deletion invokes Sonner through
  [`frontend/src/platform/system/components/users/DeleteUserMenuItem.tsx`](../../../frontend/src/platform/system/components/users/DeleteUserMenuItem.tsx),
  but the successful-delete feedback was not observed in the browser run.
- The previous task's evidence is retained in
  [`../08-11-reconcile-frontend-e2e-baseline/research/e2e-baseline-evidence.md`](../08-11-reconcile-frontend-e2e-baseline/research/e2e-baseline-evidence.md).

## Requirements

1. Preserve the durable email outbox design while making the documented local
   backend and Celery worker configuration deliver password-recovery mail to
   the repository mailbox.
2. Reconcile the live database's IAM seed state so scheduler permissions and
   the Platform Administrator role match the source catalog. Do not bypass
   route authorization or insert permissions from browser tests.
3. Make successful inventory document delete/restore feedback and remote unit
   selection reliable for a real user, then align the focused regression tests
   with that verified interaction contract.
4. Make successful user deletion give stable feedback and refresh the user list
   without weakening deletion safeguards; update the regression assertion only
   after the product contract is reproduced.

## Acceptance Criteria

- [ ] With the documented local backend, Redis, Celery worker, and loopback
      mailbox configuration, both password-recovery flows receive their email
      and complete without bypassing `email_outbox`.
- [ ] A database initialized or reconciled from the current application source
      exposes both scheduler permission codes; the configured administrator
      receives them through the Platform Administrator role and can use the
      scheduler UI/API normally.
- [ ] The inventory document delete/restore and remote processing-unit filter
      work through visible Ant Design controls, with focused browser regression
      coverage that does not depend on arbitrary sleeps or pre-existing rows.
- [ ] Deleting a managed user presents the established success feedback and
      removes that row from the refreshed list, with a focused regression test.
- [ ] Backend and frontend quality gates pass; no production mail bypass,
      scheduler authorization bypass, or manual generated-client edit is added.

## Out Of Scope

- Changing the repository-owned Playwright mailbox protocol or reopening the
  frontend directory migration.
- Replacing the generic outbox, adding a synchronous email-send path, or
  relaxing scheduler permissions to make a test pass.
- Unrelated inventory workflow, data-model, or visual redesign work.

## Planning Status

This is a complex cross-layer repair task. Its design and implementation plan
are prepared, but no implementation may start until the user explicitly
approves the final planning summary.
