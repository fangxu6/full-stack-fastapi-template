# JWT Session Revocation API Scenarios

All cases use an isolated test database and real API requests. Capture both
HTTP responses and database state.

| Case | Setup and request | Expected response/state |
| --- | --- | --- |
| Login | Active user posts valid form credentials to `/login/access-token`. | 200 with the existing bearer response; one active `auth_session`; JWT contains the required claims. |
| Legacy token | Call a protected endpoint with a token lacking `sid`/`typ` or signed with the old secret. | 401; no database mutation. |
| Session revoke | Login, call a protected endpoint, then POST `/login/logout` with that token and call the endpoint again. Repeat logout. | First logout succeeds; protected call is 401; session has `revoked_at`; repeated logout is a successful no-op. |
| Multi-device | Login twice, revoke the first token, then call with both tokens. | First is 401; second remains 2xx; only first session is revoked. |
| Password change | Create two sessions, call `/users/me/password`, then use both old tokens. | Password update succeeds; both old tokens are 401; both sessions revoked. |
| Account state | Create a session, deactivate or delete the user through the admin API, then call a protected endpoint. | State change succeeds when allowed; old token is 401; session is revoked or removed. |
| Reset one-time use | Request password recovery, consume the newest token once, then consume it again. | First reset is 200; second is 400/401; the conditional version update changes the version once and sessions are revoked. |
| Reset supersession | Issue two reset links, then consume the first/older link. | Older link fails because its outbox version is stale; newest link remains valid. |
| Concurrent reset issuance | Issue two recovery requests concurrently for one user and inspect their outbox version snapshots. | Snapshots are distinct and ordered; only the highest/current version can reset the password. |
| Reset token delivery retry | Force a link outbox delivery retry; decode both rendered token payloads. | Both carry the same outbox version; retry does not mutate the user version or invalidate the earlier rendered link. One successful use invalidates both. |
| Legacy queued link | Create a non-terminal pre-release link-email row, run the migration, then run delivery. | The row is terminally failed as `TOKEN_SUPERSEDED`; no legacy reset token is rendered. |
| Access claim rejection | Call a protected endpoint with missing claims or wrong `iss`, `aud`, or `typ`. | 401; no session or user mutation. |
| Initial setup | Create an active user and consume the account-setup link once. | Password is set; link cannot be reused; user can log in and receives a new session. |
| Permission continuity | Use an active session before and after role/permission changes. | Permission decisions follow current DB roles; no unnecessary session revoke. |
