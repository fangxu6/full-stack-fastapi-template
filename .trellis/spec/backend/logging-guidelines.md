# Logging Guidelines

> Logging expectations for backend operational and debugging paths.

---

## Overview

This repo does not yet have a rich structured-logging stack. The practical baseline today is smaller and stricter: whenever a failure needs debugging, logs must preserve enough context to correlate with the request ID returned to the client.

---

## Current Reality

- Standard Python `logging` is used.
- The most important logging contract is in the unhandled exception flow:
  - request id
  - request path
  - traceback
  - [`backend/app/core/exceptions.py`](../../../backend/app/core/exceptions.py)
- Utility and lifecycle paths also log operational events:
  - [`backend/app/utils.py`](../../../backend/app/utils.py)
  - [`backend/app/backend_pre_start.py`](../../../backend/app/backend_pre_start.py)
  - [`backend/app/initial_data.py`](../../../backend/app/initial_data.py)

---

## Minimum Logging Rules

- Log unhandled exceptions with traceback.
- Include `request_id` when logging request-scoped failures.
- Include path or action context when a request failed.
- Include resource identifiers or business identifiers when they materially help debugging.

---

## When to Log

- Unexpected exceptions
- External side-effect failures that need investigation
- Important startup or initialization checkpoints
- Important state transitions that are otherwise hard to reconstruct

---

## What Not to Log

- Passwords
- Raw auth tokens
- Secret configuration values
- Context-free noise such as `"error happened"` with no request or business correlation
- `print(...)` debugging in normal backend code paths

---

## Current Reality vs Recommended Direction

### Current reality

- Logging is light and mostly centralized around failures and startup.
- `request_id` correlation is the strongest repo-wide operational guarantee.

### Recommended direction

- If the repo later adopts more structured logging, keep `request_id` as the first-class correlation field.
- When adding logs around new modules or external integrations, preserve the same minimum correlation set instead of inventing a different format.

---

## Code Anchors

- Unhandled exception correlation: [`backend/app/core/exceptions.py`](../../../backend/app/core/exceptions.py)
- Operational helper logging: [`backend/app/utils.py`](../../../backend/app/utils.py)
- Startup logging: [`backend/app/backend_pre_start.py`](../../../backend/app/backend_pre_start.py), [`backend/app/initial_data.py`](../../../backend/app/initial_data.py)
