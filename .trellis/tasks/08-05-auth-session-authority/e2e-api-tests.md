# Auth-session authority API E2E test plan

## Environment

- Target backend: `http://127.0.0.1:8000`
- Health check: `/api/v1/utils/health-check/`
- Isolation: use the existing isolated PostgreSQL database ending in `_test`
  or `_pytest`; never use the development database.

## Cases

| ID | Endpoint / Flow | Setup Data | Request | Expected Response | Persistence / Side Effects | Failure Assertions |
| --- | --- | --- | --- | --- | --- | --- |
| E2E-001 | `POST /api/v1/login/access-token` | Active human User with valid password | OAuth2 form `username`, `password` | `200`, existing `access_token` response shape | One `AuthSession` row exists with the token `sid`, user ID, future expiry, and no `revoked_at` | Invalid credentials still return the existing failure response and create no session row |
| E2E-002 | `POST /api/v1/login/logout` then `POST /api/v1/login/test-token` | One valid access token | Logout with Bearer token, then reuse the same token | Logout `200` with existing message; protected request `401` | Matching session has `revoked_at`; repeated logout remains `200` | A token for another session is not revoked; invalid token remains `401` |
| E2E-003 | `PATCH /api/v1/users/{user_id}` password change | User with two active access tokens and an authorized administrator | Patch `password` with a new valid password | `200`; both old protected requests return `401` | All active sessions for the target user are revoked | No old session remains usable; unrelated user sessions are unchanged |
| E2E-004 | `PATCH /api/v1/users/{user_id}` deactivation | Active target User with one access token and authorized administrator | Patch `is_active: false` | `200`; old protected request returns `401` | Target session is revoked and target User is inactive | No authentication detail reveals whether inactivity or revocation caused the 401 |
| E2E-005 | Protected request with malformed, mismatched, or expired access token | Existing user/session fixtures plus altered JWT claims | `POST /api/v1/login/test-token` with each token | `401` with the unified error shape | No new `AuthSession` row or mutation | Response does not distinguish missing user, missing session, mismatch, revocation, or expiry |

## Execution

- Verify the health endpoint and isolated backend environment before running the
  cases.
- Execute focused pytest coverage first, then run these cases against the local
  backend if it is available.
- Record any concrete environment blocker in the task validation notes; do not
  substitute the development database.
