# Celery And Redis Runtime Implementation Plan

## Files And Order

1. Add the bounded Celery Redis dependency with `uv`, updating
   `backend/pyproject.toml` and `uv.lock` together.
2. Extend `app.core.config.Settings` and its tests with Redis credentials,
   derived broker/result URLs, positive timeout validation, and non-local
   default-secret rejection.
3. Add `app.core.celery` and `app.core.tasks` with JSON-only Celery settings,
   explicit task discovery, late acknowledgement, single-queue defaults, and
   the bounded `runtime.ping` task.
4. Add focused eager tests for configuration and the task; do not add an API
   route, database migration, model, schema, or frontend client change.
5. Add Redis, worker, and Beat to `compose.yml` and mirror the local runtime in
   `compose.override.yml`; wire AOF volume, passwords, health checks, service
   dependencies, fixed worker hostname, and `--concurrency=1`.
6. Extend the Docker Compose CI workflow to start the three services and run an
   in-container `runtime.ping` broker/worker assertion.
7. Update `.env`, deployment documentation, staging/production workflow
   secrets, and an ADR documenting why Celery/Redis is runtime transport while
   PostgreSQL outbox remains the future business-fact store.
8. Add the durable asynchronous-task contract to `.trellis/spec/backend/`,
   include it in the backend index, refresh the spec catalog/log, and run its
   link lint.

## Validation

- `uv lock --check`
- `docker compose config`
- `docker compose -f compose.yml config`
- `bash backend/scripts/lint.sh`
- Focused eager tests from `backend/`
- Isolated `docker compose` run that waits for Redis, worker, Beat, and the
  existing backend, then dispatches and retrieves `runtime.ping`
- Existing Docker Compose smoke workflow behavior for backend and frontend

## Review Points

- `REDIS_PASSWORD`, derived URLs, task payloads, task results, and logs never
  reveal credentials.
- Backend startup remains independent of Redis; only worker/Beat depend on it.
- Redis has no host port or Traefik exposure and retains AOF data in its named
  volume.
- The worker receives only JSON-serializable task arguments; no ORM/session
  objects cross the task boundary.
- No global automatic retries, task routes, outbox tables, alert adapters, or
  user-notification code is introduced.
- No OpenAPI or generated frontend client impact exists.

## Rollback Points

- Before production rollout, validate an authenticated Redis restart and a
  worker restart in staging using only `runtime.ping`.
- A runtime-only rollback stops worker and Beat while preserving Redis volume;
  existing HTTP API behavior stays unchanged.
- If a later task starts dispatching work, disable its caller before worker/Beat
  shutdown and retain PostgreSQL outbox records until its own recovery plan is
  complete.

Deferred capability boundaries are tracked in
[deferred-iterations.md](./deferred-iterations.md).
