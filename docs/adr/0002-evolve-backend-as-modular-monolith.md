# Evolve Backend as Modular Monolith

The backend will evolve as a modular monolith rather than a full Clean Architecture rewrite or microservice split. The current FastAPI, SQLModel, shared error handling, and generated-client contracts are valuable working infrastructure, so new bounded capabilities should grow under `backend/app/modules/<name>/` while preserving public API behavior and avoiding premature distributed-system costs.

## Considered Options

- Keep only the global `api -> services -> crud` layout: lowest short-term churn, but it keeps growing unbounded global files.
- Move gradually to module boundaries: preserves the working stack while giving new capabilities clearer ownership.
- Rewrite around strict use cases and ports/adapters: cleaner on paper, but too much migration risk for the current template-derived backend.
- Split into microservices: creates independent deployable units, but adds deployment, transaction, auth, observability, and data-ownership complexity before the repo has real service boundaries.

