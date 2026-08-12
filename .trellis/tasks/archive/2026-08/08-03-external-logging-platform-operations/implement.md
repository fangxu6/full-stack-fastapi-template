# Implementation Plan: External Logging-Platform Operations

## Preconditions

Do not start implementation until the four promotion inputs in `prd.md` are
approved. The chosen platform is an operational dependency, so its exact
configuration and access commands cannot be safely invented in this plan.

## Execution Order After Approval

1. Record the selected platform, accountable owner, runtime topology, reader
   group, break-glass path, and retention authority in the revised PRD.
2. Configure one operations-owned collector against a non-production runtime.
   Parse only stdout NDJSON; do not modify application code or add an
   application credential.
3. Prove collector health, malformed-line handling, and collection from every
   applicable backend, worker, and beat runtime.
4. Configure production 30-day and staging 14-day retention, then capture
   platform-native evidence that scheduled deletion is enabled.
5. Provision the operations reader group and prove allow, deny, and
   break-glass audit behavior.
6. Save the two minimal incident views: request-ID lookup and
   error/dependency-failure triage. Do not add alert rules or extra dashboards.
7. When a public API proxy is actually deployed, test request-ID overwrite,
   response header, and collected-event lookup end to end.
8. Write the platform-specific operations runbook: health checks, access
   request/revocation, request-ID investigation, collector failure response,
   retention evidence, and rollback.

## Validation Matrix

| Case | Expected result |
| --- | --- |
| Valid NDJSON event | One searchable event with the existing approved fields. |
| Malformed stdout line | Collector records/reports parse failure; application remains unaffected. |
| Collector unavailable | Operations detects the failure; application request/task outcome is unchanged. |
| Authorized reader | Can run both saved incident views. |
| Unauthorized reader | Cannot query or export operational records. |
| Retention cutoff | Production records older than 30 days and staging records older than 14 days are deleted by the platform; records at or inside the cutoff remain. |
| Deployed API proxy | Spoofed inbound ID is not returned or indexed; response ID is present and matches the collected event. |

## Rollback

Remove the collector/export configuration and revoke the new reader group.
Keep the application deployment unchanged. Do not create a second sink,
re-enable raw Uvicorn logs, or relax the D-002 data allowlist as a workaround.

## Review Gate Before Start

- [ ] Operations has supplied every promotion input and approved the revised,
  platform-specific PRD.
- [ ] The collector covers all deployed NDJSON producers.
- [ ] Access, break-glass, retention, and collector-failure behavior have
  platform-native validation steps.
- [ ] The API proxy test is either included for an actual proxy deployment or
  explicitly deferred because no public API proxy is being released.
- [ ] A user has reviewed this revised plan and explicitly approved starting
  implementation.
