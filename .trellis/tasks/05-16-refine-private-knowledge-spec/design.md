# Design

## Scope

This task is a documentation-spec refinement task inside `.trellis/spec/`. It does not change application runtime behavior. The deliverable is a more executable local rule set for future AI sessions.

## Inputs

### Primary reality sources

- Current backend code under `backend/app/**`
- Current frontend code under `frontend/src/**`

### Supporting knowledge sources

- `docs/私域知识/01_架构概览.md`
- `docs/私域知识/02_数据模型.md`
- `docs/私域知识/05_开发规范.md`
- `docs/私域知识/06_常见问题.md`
- `docs/私域知识/07_异常与模块扩展规范.md`
- `docs/私域知识工程体系产出/系统架构分析.md`
- `docs/私域知识工程体系产出/知识沉淀/数据模型手册.md`
- `docs/私域知识工程体系产出/知识沉淀/开发规范与最佳实践.md`

## Approach

### 1. Preserve the existing spec topology

Keep the current `backend/`, `frontend/`, and `guides/` spec files. The task is refinement, not re-architecture.

### 2. Normalize each spec to the same information shape

Where useful, strengthen docs with:

- short overview
- repo-specific executable rules
- `Current reality`
- `Recommended direction`
- code references

This keeps transitional architecture legible and avoids pretending target-state patterns are already fully migrated.

### 3. Translate private docs into implementation rules

Only extract content that helps future implementation and review:

- layer ownership
- error contracts
- request tracing
- OpenAPI regeneration workflow
- data-model constraints
- state and permission boundaries
- review/test expectations

Do not copy FAQ or long architecture narratives verbatim.

### 4. Bias toward current code anchors

Every important rule should point at real code so future sessions can verify the guidance quickly.

## Major Decisions

### Current code outranks target architecture

If private docs describe a desired structure that is only partially migrated, spec wording must say so explicitly.

### Cross-layer rules stay centralized in existing files

No new guide file will be added. Cross-layer rules belong in `guides/index.md` plus the relevant backend/frontend spec files.

### Frontend layering is a strong guardrail

The strongest risk in this repo is structural regression back into thick route files and mixed shared/business code. The refined spec should treat those boundaries as strong constraints, not gentle suggestions.

## Risks

- Overstating future architecture as already implemented.
- Making spec too long to be practically injected and used.
- Duplicating the same rule in too many files and creating drift.

## Mitigations

- Use `Current reality` versus `Recommended direction`.
- Keep guides brief and concrete.
- Put each rule in its natural home and only echo it where it truly affects another layer.
