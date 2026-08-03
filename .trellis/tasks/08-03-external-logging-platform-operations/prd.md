# External logging-platform operations

## Goal

D-009: plan operations-owned collection, reader access, retention, and
dashboards for structured logs.

## Confirmed Context

- D-002 emits privacy-safe, exporter-ready JSON to stdout but does not operate
  a collector, log search, dashboard, reader-access model, or retention
  enforcement.
- This task changes operations deployment and access boundaries, not ordinary
  application behavior.

## Requirements

- Operations selects the logging platform and its deployment ownership model.
- Define collector/export configuration, authenticated reader access, query
  access, dashboards, and 30-day production / 14-day staging retention.
- Verify the Nginx request-ID overwrite and response-header contract through
  the selected collection path.

## Acceptance Criteria

- [ ] Operations approves the platform choice, owner, and access model.
- [ ] PRD defines collection, reader authorization, retention, dashboards,
  failure handling, and request-correlation verification.
- [ ] Design, implementation plan, deployment/rollback plan, and operational
  validation scope are reviewed before `task.py start`.

## Out of Scope

- Changing application log schemas or provisioning a logging platform before
  operations selects and owns it.
