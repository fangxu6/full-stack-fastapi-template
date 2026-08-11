# Frontend E2E Baseline Evidence

## Reproduction

The 2026-08-11 run against the local backend on `localhost:8000` and the
Vite origin on `http://localhost:5173` completed 65 of 78 Playwright cases.
The remaining 13 failures are unrelated to the completed source-path-only
move in `08-10-refactor-frontend-legacy-directories`.

| Group | Cases | Evidence | Classification |
| --- | ---: | --- | --- |
| Password recovery | 2 | `frontend/tests/utils/mailcatcher.ts:16` requests the unstarted `MAILCATCHER_HOST`; local port `1080` is unavailable. | Missing test mail service |
| Inventory | 3 | Shipment expects a pre-existing finished balance and its processing unit (`frontend/tests/inventory.spec.ts:46-64`, `167-197`); the other cases assert a soft-delete feedback message and a remotely searched processing-unit option. | Shared fixture dependency and stale/browser-timing assertions |
| Scheduler | 3 | The page renders management controls only with `scheduler.jobs.manage` (`frontend/src/features/scheduler/pages/SchedulerJobsPage.tsx:137-140`); the E2E setup authenticates only the configured first superuser. | Bootstrap/permission contract drift |
| Account and settings | 5 | One admin delete toast, profile-save toast, two cancel/display assertions, and existing-email sign-up assertion fail. The moved toast and settings imports are unchanged in behavior. | Assertions need contract-level reproduction |

## Runtime Contract

- The root E2E guide provisions PostgreSQL and an initial superuser, then
  starts only FastAPI and Vite. It neither starts SMTP nor a mail inbox:
  `docs/rules/Playwright E2E 配置与运行教程.md:17-78`.
- Password recovery creates a durable `PASSWORD_RECOVERY` outbox row;
  delivery happens asynchronously through Celery and SMTP. HTTP success does
  not guarantee SMTP acceptance: `docs/adr/0009-use-generic-email-outbox-for-non-report-mail.md:15-30`.
- `.env_test` currently points SMTP to an external server while
  `frontend/.env` points the browser helper at `http://localhost:1080`; neither
  configuration creates the mail service the test reads.
- The project does not have a checked-in local mail-sink executable or an
  installed `mailpit`, `mailcatcher`, or `mailhog` command.
- The installed `emails` client emits nested multipart mail with the HTML part
  encoded as Base64. The fixture must decode that bounded MIME shape before
  serving `GET /messages/:id.html`; a raw-text token scan is insufficient.

## Implications

1. Do not change production recovery, inventory, scheduler, or notification
   behavior merely to make a browser assertion green.
2. Make every E2E prerequisite explicit and reproducible from the documented
   isolated test environment, including the correct first-superuser role
   bootstrap and inventory data creation.
3. The remaining design choice is how the full recovery flow obtains mail on a
   Docker-free workstation: a documented external local mail sink keeps a
   real SMTP-to-inbox test but adds a machine prerequisite; a repository-owned
   ephemeral fixture removes that prerequisite but adds test-infrastructure
   code.
