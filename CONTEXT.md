# Internal Operations Domain

This context defines the durable language for internal operational records and
their identifiers.

## Language

**Technical Primary Key**:
The immutable database identifier used to locate a row and maintain relations.
_Avoid_: document number, business number, user-facing code

**Business Identifier**:
A domain-owned human-readable identifier whose generation and uniqueness scope
are defined by that domain.
_Avoid_: primary key, database ID

**Resource Access Domain**:
The explicit set of authenticated users allowed to read or mutate a resource.
_Avoid_: ID secrecy, implicit internal access

**Permission**:
A stable, server-verifiable code that grants an action on a protected resource.
_Avoid_: menu visibility, client-side flag

**Role**:
A named collection of Permissions assigned to one or more Users.
_Avoid_: job title, department

**Built-in Role**:
A system-seeded Role with a stable code and minimum permission baseline.
_Avoid_: user-deletable role, arbitrary custom role

**Custom Role**:
A Platform Administrator-managed Role composed only from the system-owned
Permission catalog.
_Avoid_: custom permission code, direct user permission

**Permission Prerequisite**:
An explicitly required Permission that must be present in a Role before a
dependent Permission can be assigned.
_Avoid_: hidden implied permission, runtime privilege escalation

**Governance Permission**:
A Permission in the `system.users.*` or `iam.roles.*` namespace, reserved for
the Built-in Platform Administrator Role.
_Avoid_: custom-role delegation, self-service privilege escalation

**Authorization Recovery**:
A controlled operational process that restores one active Platform
Administrator without bypassing normal authorization through application startup.
_Avoid_: automatic reactivation, bootstrap backdoor

**System-Wide Inventory Access**:
An inventory access domain where an allowed User may access every inventory
record of the permitted resource type, regardless of creator or import origin.
_Avoid_: own records only, department scope, implicit legacy lock

**Full Inventory Field Visibility**:
An inventory read contract that returns the current complete API field set to
an allowed User without role-based field redaction.
_Avoid_: UI-only masking, implied sensitive-field policy

**Operational Alert**:
A time-sensitive notification to an accountable operations or business owner
after an approved abnormal business condition. It is separate from application
user messaging and does not itself establish acknowledgement or escalation.
_Avoid_: ordinary user notification, audit record, unowned log event

**User Work Notification**:
A notification presented to an application User about a task they may need to
complete. It is not a substitute for an Operational Alert to a responsible
on-call group.
_Avoid_: on-call alert, delivery retry record

**System Actor**:
A non-interactive application-owned User that attributes an automated audited
write when no human User initiated it.
_Avoid_: fallback User, administrator account, service login

**Inventory Document**:
An operational record of an inventory receipt, return, or shipment, including
the dated document details and its inventory lines.
_Avoid_: ledger entry, spreadsheet row

**Inventory Ledger**:
The recorded inventory movement effects derived from Inventory Documents and
used to determine inventory balances.
_Avoid_: source document, current balance snapshot

**Inventory Unit**:
A processing or receiving organization managed only by the inventory domain
and referenced by Inventory Documents to identify where inventory moves.
_Avoid_: global organization, user department

## Relationships

- A **Business Identifier** may identify an operational document to people but
  never replaces that document's **Technical Primary Key**.
- A **Technical Primary Key** locates a resource; its **Resource Access Domain**
  decides whether the requesting user may access it.
- A **User** may hold multiple **Roles**; their effective **Permissions** are
  the union of permissions assigned to those roles.
- A **Role** grants functional access, while a **Resource Access Domain**
  constrains which records an allowed User may access.
- A Role assigned a dependent **Permission** also contains every declared
  **Permission Prerequisite**.
- A **Custom Role** cannot contain a **Governance Permission**.
- **Authorization Recovery** is required when no active User holds the active
  Built-in Platform Administrator Role.
- An active Role with an inventory Permission grants **System-Wide Inventory
  Access** until a later data-scope policy explicitly narrows it.
- An allowed inventory reader receives **Full Inventory Field Visibility**
  until a future field-level policy changes the API contract.
- An **Operational Alert** targets an accountable responder, while a **User
  Work Notification** targets an application User and has separate read-state
  and preference semantics.
- An audited action has either its initiating human **User** or the **System
  Actor** as its actor; the latter never represents a human-initiated action.
- An **Inventory Document** produces the corresponding **Inventory Ledger**
  effects that determine inventory balances.
- An **Inventory Unit** belongs to the inventory domain; its lifecycle and
  lookup rules are part of inventory operations.

## Example Dialogue

> **Developer:** "Can I use the receipt number as its database ID?"
> **Domain expert:** "No. The receipt has a technical primary key for relations;
> its business identifier is a separate field defined by the inventory domain."

> **Developer:** "The inventory menu is hidden for this user. Is that enough to
> deny the API call?"
> **Domain expert:** "No. The server must require the matching **Permission**;
> menu visibility only presents the effective permission set."

> **Developer:** "A scheduler creates an audited operational record. Which
> user created it?"
> **Domain expert:** "Use the **System Actor**. A record initiated by a person
> must instead name that person."

## Flagged Ambiguities

- "ID" was previously used for both database keys and human-readable numbers.
  Resolved: use **Technical Primary Key** for the former and **Business
  Identifier** for the latter.
