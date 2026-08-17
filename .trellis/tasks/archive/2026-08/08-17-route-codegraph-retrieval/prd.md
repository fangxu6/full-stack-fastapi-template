# Route CodeGraph retrieval guidance by task shape

## Goal

Replace unconditional CodeGraph-first wording with a smallest-sufficient-
retrieval policy. Preserve CodeGraph for uncertain call paths, cross-layer
ownership, and dynamic dispatch while avoiding unnecessary wide exploration
for known paths, exact literals, migrations, generated files, and specs.

## Confirmed Facts

- `.trellis/spec/guides/index.md`, `cross-layer-thinking-guide.md`, and
  `code-reuse-thinking-guide.md` each currently require CodeGraph first.
- A sampled `codegraph explore` for `request_id` returned 38 symbols across
  five source files, so broad exploration can add substantial context for a
  narrow investigation.
- The checked-in root `AGENTS.md` contains only its Trellis managed block; it
  has no CodeGraph guidance to change.
- `.trellis/spec/log.md` is append-only for durable changes under
  `.trellis/spec/**`.

## Requirements

- Define one consistent retrieval router across the three shared guides:
  known path or exact literal uses narrow search or direct reading; a known
  symbol that needs callers may use `codegraph node`; uncertain ownership,
  multi-hop paths, or dynamic dispatch may use `codegraph explore`.
- State that lower tool-call count is not sufficient evidence of an
  improvement; preserve answer quality and measure total cost when optimizing
  retrieval policy.
- Keep the existing CodeGraph command examples, but make `explore` conditional
  on the problem shape rather than mandatory for every modification.
- Append one concise maintenance-log entry for this specification change.

## Acceptance Criteria

- [ ] None of the three guides unconditionally requires CodeGraph as the first
      retrieval step.
- [ ] All three guides give compatible routing guidance and distinguish
      `codegraph node` from `codegraph explore`.
- [ ] Known paths, exact literals, migrations, generated files, and spec/docs
      lookups are explicitly allowed to use narrow retrieval.
- [ ] The maintenance log records the policy change without rewriting history.
- [ ] A focused search and diff review confirm only the intended guidance and
      task artifacts changed; the pre-existing deletion of `test_playwright.py`
      remains untouched.

## Out Of Scope

- Changing external or runtime-injected agent instructions that are not present
  in the checked-in `AGENTS.md`.
- Adding token telemetry, a benchmark harness, or cache-cost instrumentation.
- Changing CodeGraph itself, its index, or application source code.

## Notes

- This is a lightweight, documentation-only task; PRD-only planning is
  sufficient.
