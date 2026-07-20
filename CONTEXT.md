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

## Relationships

- A **Business Identifier** may identify an operational document to people but
  never replaces that document's **Technical Primary Key**.
- A **Technical Primary Key** locates a resource; its **Resource Access Domain**
  decides whether the requesting user may access it.

## Example Dialogue

> **Developer:** "Can I use the receipt number as its database ID?"
> **Domain expert:** "No. The receipt has a technical primary key for relations;
> its business identifier is a separate field defined by the inventory domain."

## Flagged Ambiguities

- "ID" was previously used for both database keys and human-readable numbers.
  Resolved: use **Technical Primary Key** for the former and **Business
  Identifier** for the latter.
