# Technical Design: Resolve Frontend Baseline Runtime and UI Defects

## Boundaries

This task repairs four independently meaningful behaviors. Playwright remains
the regression observer, not the owner of the production behavior. The
existing repository mailbox and directory migration remain unchanged unless a
focused regression requires its existing public endpoint.

| Area | Source of truth | Required outcome |
| --- | --- | --- |
| Password recovery | `email_outbox`, Celery worker, SMTP settings | A documented local worker delivers the queued recovery message to loopback SMTP. |
| Scheduler access | IAM constants and `ensure_bootstrap_state()` | The database catalog and built-in administrator role contain the current scheduler permissions. |
| Inventory UI | page mutations and `useUnitSelectOptions` | Success feedback and a searched unit are visibly usable after their requests settle. |
| User deletion | delete mutation, Sonner, user query invalidation | Feedback and refreshed row state are observable after a successful deletion. |

## Repair Approach

1. Reproduce recovery delivery with an isolated backend, Redis, worker, and
   mailbox. Trace configuration from process startup through outbox claim and
   SMTP connection. Repair the configuration/startup contract or a proven
   worker defect, while preserving durable outbox retries.
2. Reproduce the permission catalog mismatch against a database that was
   initialized before scheduler permissions existed. Use the existing IAM
   bootstrap reconciliation boundary or a forward-only migration where
   startup reconciliation cannot cover deployed databases. Confirm built-in
   role permissions are replaced idempotently.
3. Reproduce inventory mutations and remote Select search from a fresh
   fixture. Fix only a proven page/control lifecycle defect, otherwise assert
   the stable visible control transition rather than implementation timing.
4. Reproduce user deletion with network and DOM evidence. Keep the existing
   toast provider if it is mounted and functional; change the mutation/control
   lifecycle only if the notification is lost in the real product path.

## Compatibility and Rollback

- No new mail transport, production test endpoint, or browser authorization
  bypass is introduced.
- IAM reconciliation must be safe to run repeatedly and retain custom-role
  assignments.
- UI repairs keep existing Chinese inventory feedback and English system-user
  feedback unless product evidence establishes a different contract.
- Roll back each repair independently: runtime documentation/configuration,
  IAM reconciliation, inventory UI, and user-delete UI do not require a shared
  release switch.
