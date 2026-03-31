# ADR-xxxx: Decision Title

## Purpose

Use this file as the template for an Architecture Decision Record (ADR).

ADR is optional in this repository and should only be created for decisions that are:

- architecture-level
- long-lived
- cross-cutting across multiple modules or teams
- expensive to reverse later
- likely to be questioned again without written rationale

For ordinary feature work, bugfixes, or local implementation choices, update `docs/decisions/AI_CHANGELOG.md` instead.

In most cases:

- `AI_CHANGELOG.md` is the default decision log
- ADR is only added when the decision changes the long-term architecture or delivery model
- If you write an ADR, you should usually also add a short entry to `AI_CHANGELOG.md`

## How To Use

1. Copy this file to a real ADR name, for example `ADR-0001-query-strategy.md`
2. Replace `xxxx` and `Decision Title`
3. Fill the sections below with repository-specific details
4. Link the ADR from related specs, rules, or changelog entries when relevant

## Status

One of:

- Proposed
- Accepted
- Superseded
- Deprecated

Status: Proposed

## Date

YYYY-MM-DD

## Context

Describe the problem, pressure, or recurring ambiguity that requires a durable decision.

Include:

- current repository state
- constraints
- rejected assumptions
- operational or delivery impact

## Decision

State the decision clearly and concretely.

Prefer wording that is testable in future reviews, for example:

- "Frontend server-state must use TanStack Query"
- "Backend API changes must continue to flow through generated OpenAPI client regeneration"
- "Production deployment uses Traefik + Docker Compose on a single host"

## Scope

List the areas affected by this decision.

- code paths
- docs
- workflows
- CI/CD
- infra
- testing expectations

## Alternatives Considered

List the main alternatives and why they were not chosen.

### Alternative 1

- Option:
- Why not chosen:

### Alternative 2

- Option:
- Why not chosen:

## Consequences

Describe both benefits and trade-offs.

### Benefits

- 

### Trade-offs

- 

### Risks / Follow-ups

- 

## Implementation Notes

Describe what must be updated or enforced because of this decision.

- affected files or directories
- migration or rollout notes
- review guidance
- compatibility constraints

## Validation

How will we know this decision is being followed?

- tests
- lint/build checks
- review rules
- spec updates
- operational checks

## Related Docs

- `docs/decisions/AI_CHANGELOG.md`
- Related spec docs under `docs/specs/...`
- Related rules under `docs/rules/...`
- Related team guidance under `docs/skills/...`
