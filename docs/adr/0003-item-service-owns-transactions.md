# Item Service Owns Transactions

The `items` CRUD flow makes `services/item.py` responsible for commit and refresh while `crud/item.py` performs database operations without committing. This keeps simple CRUD lightweight while preserving a clear transaction owner.

## Consequences

- Item route handlers call service-level operations.
- Item CRUD callers must explicitly commit or use the item service.
- This transaction contract applies only to items until later tasks migrate users/auth or other modules.
