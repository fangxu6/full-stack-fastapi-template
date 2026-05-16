# Logging Guidelines

> How logging is done in this project.

---

## Overview

This backend currently uses the standard `logging` module instead of a custom structured logger. Logging is concentrated in startup helpers, utility functions, and the global exception handlers.

---

## Log Levels

- `info` for normal operational milestones such as service initialization and email send results.
- `error` for unexpected failures and unhandled exceptions.
- Retry and prestart scripts also use warn/error-style logging through standard logging helpers.

---

## Structured Logging

- There is a placeholder central entrypoint at [`backend/app/core/logging.py`](../../../backend/app/core/logging.py), but the current codebase still relies mostly on plain module loggers.
- The strongest consistency rule today is request correlation via `request_id`, which is attached to error responses and logged on unhandled exceptions in [`backend/app/core/exceptions.py`](../../../backend/app/core/exceptions.py).
- If you add new logging around request failures, include enough context to correlate with `request_id` and the request path.

---

## What to Log

- Service startup and initialization checkpoints, as in `backend_pre_start.py`, `tests_pre_start.py`, and `initial_data.py`.
- Unhandled exception traces via the centralized exception handler.
- Important side effects such as email delivery outcomes in [`backend/app/utils.py`](../../../backend/app/utils.py).

---

## What NOT to Log

- Do not log passwords, raw auth tokens, or secret configuration values.
- Avoid dumping entire request bodies for auth and user-management flows unless there is a very specific debugging need.
- Do not add noisy per-request info logging without a clear operational purpose; the current backend is relatively sparse on routine request logs.
