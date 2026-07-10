# Evolve Backend as Modular Monolith

The backend will evolve as a modular monolith rather than a full Clean Architecture rewrite or microservice split. The current FastAPI, SQLModel, shared error handling, and generated-client contracts are valuable working infrastructure. Simple CRUD should stay on the lightweight `api/routes -> services -> crud -> ORM` path, while genuinely bounded capabilities can grow under `backend/app/modules/<name>/` when the business complexity justifies it.

## Considered Options

- Keep only the global `api -> services -> crud` layout: lowest short-term churn, but it keeps growing unbounded global files.
- Move gradually to module boundaries only for domains that earn the extra structure: preserves the working stack while avoiding module ceremony for simple CRUD.
- Rewrite around strict use cases and ports/adapters: cleaner on paper, but too much migration risk for the current template-derived backend.
- Split into microservices: creates independent deployable units, but adds deployment, transaction, auth, observability, and data-ownership complexity before the repo has real service boundaries.
