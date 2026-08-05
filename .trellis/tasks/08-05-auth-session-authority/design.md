# Auth-session authority design

## Boundary

Create `backend/app/modules/auth/` with one `session.py` module. This is a
deliberate module boundary for a cross-route, multi-operation platform
capability, not a new generic persistence layer.

The module exposes four typed functions:

```text
issue_access_token(session, user_id) -> str
validate_access_token(session, token) -> User
logout(session, token) -> None
revoke_all_user_sessions(session, user_id) -> None
```

The module returns domain values and raises the existing
`app.core.exceptions.AuthenticationError`; HTTP `Token` and `Message` schemas
remain route/service concerns.

## Ownership

- `auth/session.py`: access-session lifecycle, `AuthSession` persistence, and
  access-token policy.
- `core/security.py`: JWT encoding/decoding primitives, password hashing, and
  password-token primitives. It does not query users or sessions.
- `api/dependencies/auth.py`: OAuth2/FastAPI dependency wiring and request
  actor-context updates. It delegates all token/session validity checks.
- `services/auth.py`: credential authentication and password recovery
  orchestration. It wraps the module's token string in the existing `Token`
  schema and the module's logout result in the existing `Message` schema.
- `services/user.py`: user lifecycle orchestration. It delegates session
  revocation when passwords change, users are deactivated, or users are
  deleted.
- `models/auth_session.py`: unchanged SQLModel table definition.

## Data flow

### Login

1. The login route passes credentials to `services.auth`.
2. Existing user authentication and active/system-actor checks remain there.
3. `services.auth` calls `session.issue_access_token` with the authenticated
   user's UUID.
4. The module inserts and flushes `AuthSession`, then calls the existing JWT
   encoder with the generated session ID.
5. The service returns the existing `Token` schema.
6. `WriteSessionDep` commits the row after the successful endpoint.

### Protected request

1. `get_current_user` calls `session.validate_access_token` using its existing
   read session.
2. The module decodes a strict access token, loads the User, rejects system,
   inactive, missing, or mismatched users, loads the AuthSession, and rejects
   missing, mismatched, revoked, or expired sessions.
3. The dependency sets the existing authenticated actor request context and
   returns the User.

### Logout

1. The logout route delegates through `services.auth` to `session.logout`.
2. The module decodes a structurally valid token with expiration verification
   disabled, then updates only the matching active AuthSession.
3. Missing or already-revoked matching rows do not fail, preserving current
   idempotent logout behavior.
4. `WriteSessionDep` commits the revocation.

### Global revocation

`services.auth` and `services.user` call
`session.revoke_all_user_sessions`. The module updates active rows only; the
caller-owned HTTP transaction commits the change.

## Error contract

The module catches JWT invalid-token and payload-validation failures and raises
the existing `AuthenticationError`. It uses the same error for every failed
access-session condition so callers cannot distinguish missing users, missing
sessions, revocation, inactivity, or expiry.

`logout` permits an expired access token only for revocation, while signature,
issuer, audience, required claims, token type, session ID, and user ID remain
validated by the existing decoder and payload schema.

## Transaction and compatibility

No function in the new module commits or rolls back. `flush` is required after
creating `AuthSession` so its UUID can be embedded in the access token. No
model, migration, API schema, OpenAPI, frontend, or dependency change is
expected.

The existing route-level behavior is the compatibility contract. A rollback
can remove the new module and restore the old imports/calls without changing
database state or generated artifacts.

## Test seam

`backend/tests/modules/auth/test_session.py` exercises the four module
functions against the existing database fixture. It verifies the module's
interface and session policy directly. Existing route tests remain the
integration seam for HTTP response codes, response bodies, and transaction
behavior. No Repository mock or new adapter is introduced.
