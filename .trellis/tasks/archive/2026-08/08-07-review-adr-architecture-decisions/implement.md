# Implementation Plan

1. Add the migration round-trip test for ADR-0008 and run it against the
   isolated test database.
2. Revise ADR-0001 through ADR-0009 for current status, scope, exceptions,
   historical context, and cross-references.
3. Keep ADR-0010 accepted for task context and cleanup, supersede only its
   exception-detail prohibition, and keep ADR-0013 as the current restricted
   detailed task-failure logging boundary.
4. Revise ADR-0011 and ADR-0012, then add the ADR status index.
5. Validate Markdown links, task artifacts, the focused migration test, and
   the backend quality gate. Do not run code generators because no API schema
   changes.
