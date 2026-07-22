# API E2E Test Plan Template

> Use for API-facing or cross-layer complex Trellis tasks. Persist the completed
> copy as `<task>/e2e-api-tests.md` before implementation begins.

## Environment

- Target backend: `http://localhost:8000` or `http://127.0.0.1:8000`
- Health check: `/api/v1/utils/health-check/`
- Browser target when applicable: `http://localhost:5173`
- Isolation: identify the test database or other isolated environment; do not
  write test fixtures to a development database.

## Cases

| ID | Endpoint / Flow | Setup Data | Request | Expected Response | Persistence / Side Effects | Failure Assertions |
| --- | --- | --- | --- | --- | --- | --- |
| E2E-001 | `<method> <path>` | `<fixtures>` | `<payload>` | `<status/body>` | `<rows/events/files>` | `<rejection and unchanged state>` |

## Execution

- Start or verify the selected isolated test environment.
- Run each listed case after implementation.
- Record command output and any concrete environment blocker in `implement.md`
  or the task's validation notes.
