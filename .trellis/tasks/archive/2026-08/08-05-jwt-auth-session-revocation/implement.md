# JWT Session Revocation Implementation Plan

1. Add the `AuthSession` SQLModel, `User.password_reset_version`, and
   `EmailOutbox.password_reset_version`, model exports, indexes, and one
   Alembic migration. Keep foreign-key deletion behavior consistent with
   existing models and never add a plaintext-token column. The migration
   cancels non-terminal pre-release link-email rows as `TOKEN_SUPERSEDED`.
2. Add JWT configuration for 24-hour access lifetime, issuer/audience, access
   secret, and password-token secret. Update token creation/decoding helpers to
   enforce the new claims and purpose.
3. Extend the shared auth dependency to strictly validate all access claims and
   `sid` against an active session. Add an idempotent logout route that uses
   claim validation without requiring an active session. Add one
   `revoke_all_user_sessions` service used by password, reset, setup,
   deactivate, and delete paths.
4. Replace reset-token generation/verification with versioned, purpose-bound
   tokens. Atomically increment-and-return the version when queuing/directly
   issuing a link, persist the returned version snapshot on the outbox row,
   render retries from that snapshot, and consume via an atomic version check
   plus increment. Preserve both password-recovery and new-account setup email
   links.
5. Update the frontend auth hook, client token resolver, logout flow, and 401
   cleanup. Do not add refresh or cookie behavior.
6. Add backend unit/API tests and frontend tests from `e2e-api-tests.md`,
   including malformed/wrong-issuer/audience/type claims and repeated logout.
7. Regenerate the OpenAPI client if the logout endpoint changes generated types;
   run formatting, type checks, and isolated backend tests with `POSTGRES_DB`
   ending in `_test` or `_pytest`.

## Review Gates

- Before migration: verify all protected routes use the shared dependency and
  no route relies on `is_superuser` for this task.
- Before rollout: verify old tokens fail, active sessions survive ordinary
  requests, and all sensitive transitions revoke sessions transactionally.
- Before migration: pause email workers so no legacy link email is rendered
  while pre-release link-email rows are being cancelled.
- Rollback requires rolling back backend and frontend together; do not accept
  new and legacy JWT formats in the same deployment.
