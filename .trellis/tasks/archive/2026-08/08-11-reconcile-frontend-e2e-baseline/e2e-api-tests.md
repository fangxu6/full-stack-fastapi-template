# E2E/API Contract Checks

These checks were used to classify the browser setup against a live isolated
backend. The remaining runtime and UI failures are transferred to
`08-11-resolve-frontend-baseline-defects`; this archived task does not claim a
full-suite pass.

1. `GET /api/v1/utils/health-check/` returns `200` and `true`.
2. The authenticated setup user can read current permissions and includes
   `scheduler.jobs.manage` for scheduler specs.
3. Creating the inventory fixture through the documented API returns `2xx`, and
   the finished balance used by shipment is visible from
   `GET /api/v1/inventory/balances/finished`.
4. Submitting password recovery returns the established success response and
   eventually produces a delivered message in the ephemeral mailbox.
5. The mailbox accepts no external recipient or non-loopback bind; teardown
   leaves its ports closed.

Use the exact isolated database, backend environment, and Celery worker
described in the Playwright guide. A missing runtime service is a failed
environment check, not a passing product result.
