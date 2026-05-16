# Backend Development Guidelines

> Actual conventions for this repository's FastAPI + SQLModel backend.

---

## Overview

The backend is a FastAPI application under `backend/app` with SQLModel, Alembic, PostgreSQL, and a layered structure across `api`, `services`, `crud`, `models`, and `schemas`.

Use this index as the backend entry point for local Trellis guidance. The root `AGENTS.md` no longer carries backend operational detail; backend-specific commands and guardrails live here.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Module organization and file layout | In progress |
| [Database Guidelines](./database-guidelines.md) | ORM patterns, queries, migrations | In progress |
| [Error Handling](./error-handling.md) | Error types, handling strategies | In progress |
| [Quality Guidelines](./quality-guidelines.md) | Code standards, forbidden patterns | Customized |
| [Logging Guidelines](./logging-guidelines.md) | Structured logging, log levels | In progress |

---

## Read Order

1. Start with [Directory Structure](./directory-structure.md) before placing files.
2. Read [Database Guidelines](./database-guidelines.md) before touching models, migrations, or persistence logic.
3. Use [Error Handling](./error-handling.md), [Logging Guidelines](./logging-guidelines.md), and [Quality Guidelines](./quality-guidelines.md) as the implementation checklist.

---

## Local Dev Defaults

- Install deps from `backend/`: `uv sync`
- Local tests from `backend/`: `uv run pytest tests/`
- Lint: `bash backend/scripts/lint.sh`
- Format: `bash backend/scripts/format.sh`
- Docker test flow from repo root: `bash ./scripts/test.sh`
- Running stack tests from repo root: `docker compose exec backend bash scripts/tests-start.sh`
- Single test from repo root: `docker compose exec backend bash scripts/tests-start.sh tests/api/routes/test_users.py::test_read_users`

Assume backend local verification uses `http://127.0.0.1:8000` unless the task explicitly says otherwise.

---

## Scope Notes

- Main backend code lives under `backend/app/**`.
- Layering should stay explicit: `api -> services -> crud -> models/schemas`.
- Operational scripts live under `backend/scripts/**` and top-level `scripts/**`.

---

## Skill and Rule Hooks

- Python work should activate `python-patterns`.
- If `docs/skills/SKILL.md` adds stricter project rules, treat those as repo-local overrides.
- Root safety rule still applies: do not modify `.env` or secrets.

---

## Migration Notes

- When backend API schemas change, regenerate the frontend client with `bash ./scripts/generate-client.sh`.
- Keep diffs focused; avoid backend-wide reformatting unrelated to the task.
