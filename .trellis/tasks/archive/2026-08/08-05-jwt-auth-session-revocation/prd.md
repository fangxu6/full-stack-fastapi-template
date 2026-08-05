# JWT authentication session revocation refactor

## Goal

Replace the current long-lived, non-revocable JWT behavior with a 24-hour
access JWT bound to a server-side session, so logout and sensitive account
changes take effect immediately without introducing refresh tokens.

## Requirements

- Keep `POST /api/v1/login/access-token` and its bearer token response shape.
- Issue access JWTs with `sub`, `sid`, `typ`, `iss`, `aud`, `iat`, `nbf`, and `exp`.
- Validate the JWT signature, time claims, issuer, audience, token type, user,
  and active `sid` session on every protected request.
- Persist only the session identity, user, creation/expiry timestamps, and
  revocation timestamp; never persist an access token.
- Allow multiple concurrent user sessions. Add an idempotent
  `POST /api/v1/login/logout` that revokes only the current `sid`.
- Revoke all sessions after self/admin password changes, successful password
  reset or initial password setup, user deactivation, and user deletion.
- Make password reset/setup links latest-only and single-use with a `User`
  version counter: atomic issuance invalidates older links, and atomic
  consumption invalidates the consumed link; keep the existing email flows and
  48-hour link lifetime.
- Keep the frontend `localStorage.access_token` contract for this iteration;
  clear it and cached identity/permissions on 401 or logout.
- Reject legacy JWTs during the cutover because they lack the new claims and
  are signed by the old access-token configuration.
- Do not add refresh tokens, refresh-token blacklists, cookie authentication,
  device-management UI, or unrelated IAM/RBAC changes.

## Acceptance Criteria

- [ ] A revoked session's access token receives 401 immediately.
- [ ] Logout revokes only the current session; another active device remains
  usable, and repeated logout is a successful no-op.
- [ ] Every listed password/account state transition revokes all sessions.
- [ ] A password reset/setup link succeeds once and fails on reuse or after a
  newer link is issued.
- [ ] Malformed access claims and access tokens with the wrong issuer,
  audience, or token type receive 401 without database mutation.
- [ ] Existing login, bearer authorization, frontend route guards, permission
  checks, and first-time password setup continue to work.
- [ ] Legacy tokens cannot access protected endpoints after deployment.
- [ ] Backend, frontend, and API-level tests cover the acceptance cases.
