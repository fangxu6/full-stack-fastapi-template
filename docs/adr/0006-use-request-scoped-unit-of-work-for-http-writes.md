# Use Request-Scoped Unit Of Work For HTTP Writes

HTTP write requests own one database transaction through `WriteSessionDep`: it reuses the request-cached `get_db` session, commits after a successful endpoint, and rolls back on any exception. `SessionDep` remains the read-session dependency. Services and CRUD helpers may `flush` or `refresh` but must not commit or roll back. This replaces the item-specific transaction rule so multi-step HTTP commands are atomic without each service inventing its own transaction boundary.

## Consequences

- Background tasks, CLI commands, startup, and migration work are outside the HTTP Unit of Work; they retain explicit, short transaction phases and must not hold database transactions across SMTP, HTTP, or Celery calls.
- Existing direct service callers outside HTTP must adopt an explicit transaction owner before their internal commits are removed.
- Every HTTP `POST`, `PUT`, `PATCH`, and `DELETE` endpoint uses `WriteSessionDep`, including endpoints that currently only authenticate or read. Authentication dependencies continue to use `SessionDep` and receive the same cached request session.
- Services flush where they need generated identities or to translate an integrity error, but never commit or roll back; the Unit of Work owns the final transaction outcome.
- HTTP endpoints do not publish a Celery task before their transaction commits. Manual scheduler runs remain `QUEUED` and the existing once-per-minute scheduler scan dispatches them after commit.
- This is a platform boundary change; migrate every HTTP write path and its tests before declaring the old model unavailable.
