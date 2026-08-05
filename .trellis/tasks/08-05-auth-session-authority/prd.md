# Deepen auth-session authority

## Goal

Make access-session behavior one explicit backend module so token issuance,
session validation, logout, and global revocation have one authoritative
implementation and one focused test surface.

## Background

The current access-session policy is split between
`backend/app/core/security.py:60-86`,
`backend/app/api/dependencies/auth.py:29-51`, and
`backend/app/services/auth.py:28-75`. User password changes, deactivation,
and deletion also call session revocation through
`backend/app/services/user.py:119,150,157`. The recent session-revocation
feature is behaviorally covered by route tests, but the session policy itself
has no module-local interface.

## Requirements

### R1. Own the access-session lifecycle

Add `backend/app/modules/auth/session.py` as the single owner for:

- issuing an access token and its `AuthSession` row;
- validating an access token against JWT claims, the `User`, and `AuthSession`;
- revoking the current session during logout;
- revoking all active sessions for a user.

Password hashing, password-reset/setup tokens, and recovery email behavior stay
outside this module.

### R2. Preserve the transaction contract

The module receives a SQLModel `Session` and may flush for generated
identifiers, but never commits or rolls back. HTTP write requests keep
`WriteSessionDep` as the transaction owner; current-user validation uses the
read session; non-HTTP callers retain explicit transaction ownership.

### R3. Preserve security and HTTP behavior

Keep the existing public login, logout, current-user, password-change,
deactivation, and deletion behavior. Invalid access-session states continue to
produce the same generic `AuthenticationError` outcome without revealing
whether a user or session exists. Logout remains idempotent for a valid token,
including an expired access token whose signature and claims remain valid.

### R4. Migrate all current callers

`api/dependencies/auth.py`, `services/auth.py`, and `services/user.py` must use
the new module. No parallel access-session policy remains in those callers.

### R5. Keep storage and transport contracts stable

Keep `backend/app/models/auth_session.py`, the existing database table and
indexes, API schemas, OpenAPI output, generated frontend client, and runtime
dependencies unchanged.

### R6. Test the module interface

Add focused tests under `backend/tests/modules/auth/test_session.py` for issue,
validation, mismatch, expiry, revocation, current-session logout, and global
revocation. Keep the existing login, logout, password-change, and user
deactivation route tests as integration coverage.

## Acceptance Criteria

- [x] `backend/app/modules/auth/session.py` owns all four access-session operations.
- [x] The module accepts `Session`, only flushes when needed, and never commits or rolls back.
- [x] `get_current_user` delegates session policy to the module and retains only dependency/request-context behavior.
- [x] Login, logout, password-change, user-deactivation, and user-deletion callers all delegate to the module.
- [x] Existing `AuthenticationError`, token, response, and idempotent-logout behavior is unchanged.
- [x] No `AuthSession` schema, migration, OpenAPI, dependency, or frontend-client change is introduced.
- [x] Focused module tests and existing auth/user route tests pass.
- [x] Backend lint and `git diff --check` pass.

## Out Of Scope

- Password hashing or password-reset/setup token changes.
- New Repository, Port, adapter, or dependency-injection abstraction.
- Auth-session database or migration changes.
- Frontend changes and generated-client regeneration.
- Session listing, device metadata, refresh tokens, or concurrent-session limits.

## Open Questions

None. Scope, ownership, interface, failure semantics, transaction ownership,
storage compatibility, caller migration, and test strategy were confirmed
before implementation planning.
