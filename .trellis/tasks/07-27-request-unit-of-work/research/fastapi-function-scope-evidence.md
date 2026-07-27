# FastAPI Function-Scope Evidence

## Verified Runtime Facts

- The backend pins `fastapi[standard]>=0.138.1,<1.0.0`; the installed version is `0.138.1`.
- `Depends` supports `scope="function"` and `scope="request"` for yield dependencies.
- FastAPI's function scope exits a yield dependency before sending the response; request scope exits after the response cycle.
- FastAPI's dependency cache key includes the dependency callable and scope. A request-scope `get_db` used by authentication and a function-scope `get_db` used by a write dependency do not share one Session.
- A local dependency-tree probe confirmed that mixed scopes create two cache keys for `get_db`; identical function scopes create one cache key and one Session.
- A local `TestClient` probe confirmed the target dependency shape: a successful request executes `open -> auth -> endpoint -> commit -> close`; an `HTTPException(409)` executes `open -> auth -> endpoint -> rollback -> close`. Each request observed exactly one Session identity.

## Required Shape

```python
SessionDep = Annotated[Session, Depends(get_db, scope="function")]

def get_write_db(
    session: Annotated[Session, Depends(get_db, scope="function")],
) -> Generator[Session]:
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise

WriteSessionDep = Annotated[Session, Depends(get_write_db, scope="function")]
```

`get_write_db()` belongs beside `get_db`; it must not import `SessionDep` from the
authentication module. The code is a target shape, not an implementation
copy-paste instruction. Tests must prove the authenticated/permission dependency
and endpoint share this exact Session.

Expected domain-level integrity failures must be triggered with `flush()` before
the endpoint returns, so existing `409`/`422` error mappings remain available.
The final dependency commit is only the transaction finalizer, not the first
place a predictable constraint error is discovered.

## HTTP Write Route Baseline

The current application has 38 route handlers using `POST`, `PUT`, `PATCH`, or `DELETE`:

| Module | Count |
| --- | ---: |
| `api/routes/items.py` | 3 |
| `api/routes/login.py` | 5 |
| `api/routes/private.py` | 1 |
| `api/routes/users.py` | 7 |
| `api/routes/utils.py` | 1 |
| `modules/iam/router.py` | 5 |
| `modules/inventory/router.py` | 8 |
| `modules/scheduler/router.py` | 8 |

ADR-0006 requires all 38 to use `WriteSessionDep`. The five login handlers and
the test-email handler are included even when their current code only reads or
performs an external side effect.

## Explicit Non-HTTP Transaction Owners

These paths must not receive an HTTP dependency and need an explicit short
transaction owner after service-level commits are removed:

- `app/core/db.py:init_db`
- `app/modules/inventory/importer.py:import_workbooks`
- `app/modules/inventory/daily_report.py`
- `app/modules/scheduler/tasks.py`
- `app/modules/inventory/scheduled_tasks.py`
- `app/initial_data.py`

Their database transactions must end before SMTP, broker, or other external
operations. This task does not redesign those flows; it preserves explicit
ownership while the HTTP boundary changes.
