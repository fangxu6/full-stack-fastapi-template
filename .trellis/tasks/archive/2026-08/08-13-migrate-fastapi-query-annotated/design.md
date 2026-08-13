# Technical Design

## Boundary

This is a route-signature-only refactor in the backend. The four identified
routers remain the owners of their query declarations; services, schemas,
dependencies, frontend code, and persistence are untouched.

## Declaration Pattern

Use the existing repository pattern:

```python
from typing import Annotated

from fastapi import Query

skip: Annotated[int, Query(ge=0)] = 0
limit: Annotated[int, Query(ge=1, le=100)] = 20
cron_expression: Annotated[str, Query(min_length=1, max_length=128)]
```

The `Query` metadata retains only validation and documentation options. The
function signature retains each old Python default. A parameter that was
required remains without a Python default.

## Affected Files

- `backend/app/api/routes/items.py`
- `backend/app/modules/inventory/correction_router.py`
- `backend/app/modules/inventory/router.py`
- `backend/app/modules/scheduler/router.py`
- `backend/tests/api/test_fastapi_query_annotations.py` (new structural guard)

## Regression Strategy

The new test parses the four source files with Python `ast` and checks route
function arguments. It rejects a `Query(...)` call used as an argument default
and rejects a `Query(...)` annotation that is not nested in `Annotated`.
Existing route tests cover runtime validation and permissions. A direct
OpenAPI serialization check compares the targeted parameter metadata before
and after the edit using the repository's current route schema output; the
implementation should also run the client generator and keep any generated
diff out of the commit when none is produced.

## Compatibility And Rollback

No endpoint URL, request payload, response payload, or database behavior changes.
If OpenAPI or focused tests show a contract change, revert the declaration in
the affected route and inspect requiredness/default placement before proceeding.
