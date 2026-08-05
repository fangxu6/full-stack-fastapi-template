# JWT Session Revocation Design

## Decisions

- Access JWT lifetime is 24 hours. There is no refresh token in this release.
- JWT remains `HS256`, with dedicated access and password-token secrets plus
  configured issuer and audience values.
- `sid` identifies a persisted login session. The existing database lookup of
  the user is extended with an active-session check, giving immediate revoke
  semantics at the current request volume.
- The browser continues storing the access token in `localStorage`; this is a
  compatibility decision and leaves XSS exposure documented as residual risk.

## Data Model

Add `AuthSession`/`auth_session` with:

- UUID primary key `id` (`sid` in the JWT)
- UUID `user_id` foreign key to `user.id`, cascading on user deletion
- UTC `created_at` and `expires_at`
- nullable UTC `revoked_at`

Add `User.password_reset_version` as a non-null integer defaulting to `0`.
Add nullable `EmailOutbox.password_reset_version` for link-email rows. New
link rows require a version snapshot; rendered and pre-release rows remain
nullable. The outbox stores only the version snapshot, never reset-token
plaintext.

## Token Contracts

Access JWT payload:

```json
{
  "sub": "<user_uuid>",
  "sid": "<session_uuid>",
  "typ": "access",
  "iss": "<configured-issuer>",
  "aud": "<configured-audience>",
  "iat": 0,
  "nbf": 0,
  "exp": 0
}
```

Password tokens use the separate password-token secret and the same issuer,
with `typ` set to `password_reset` or `password_setup`, `sub` set to the user
UUID, and `version` set to the user's current reset version. Verification must
validate purpose, issuer, audience, signature, time claims, user state, and
version. The reset endpoint accepts either password purpose, since both
existing email flows use the same endpoint.

Issuing a link uses one database `UPDATE ... SET version = version + 1
RETURNING version` in the same transaction as the recovery/setup request and
stores that returned value on the link outbox row. This prevents simultaneous
requests receiving the same version. Deferred outbox retries use the stored
snapshot and therefore do not invalidate an earlier rendered link. Consumption
uses a conditional update on `(user_id, version)` and increments the version
only when the comparison succeeds, in the same transaction as the password
update. This makes links both latest-only and single-use without a reset-token
table.

## Request Flow

1. Login authenticates the user, creates an active `auth_session`, signs an
   access JWT containing its ID, and returns the existing bearer response.
2. `get_current_user` strictly decodes required access claims, loads the user,
   rejects system/inactive users, then rejects missing, expired, or revoked
   sessions before returning the user.
3. Logout validates the access token signature and required claims but does not
   require an active session or active user. It revokes the referenced `sid`
   when present and returns success for missing, expired, or already-revoked
   sessions.
4. Password/account services call one shared `revoke_all_user_sessions`
   operation for all sensitive transitions. Role changes do not revoke sessions
   because effective permissions are read from the database on each request.
   Password changes, deactivation, and deletion revoke or remove sessions in
   the same write transaction as the user mutation.

## Frontend Flow

Keep the current generated login contract and local-storage token. Configure
the generated client token resolver to read that value. On 401, remove the
token, invalidate current-user/effective-permission queries, and redirect to
login. Logout calls the new backend endpoint before performing the same local
cleanup; cleanup still happens if the call fails.

## Compatibility And Rollout

Create one Alembic migration for the session table, user reset version, and
outbox version snapshot field.
Deploy migration, backend, and frontend together. New claim requirements and
the new access secret make every legacy token unusable, so all users log in
again. Pause email workers for the migration and mark all non-terminal
pre-release link-email rows as failed with `TOKEN_SUPERSEDED`; their legacy
tokens must not be rendered after cutover. No dual-token compatibility branch
is allowed.

## Explicit Non-Goals

Refresh tokens, refresh blacklists, HttpOnly-cookie auth, device-management
screens, JWT key rotation, and unrelated IAM/RBAC redesign are deferred.
