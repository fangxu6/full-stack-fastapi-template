# Item Service Owns Transactions

The `items` modularization pilot makes `modules/items/service.py` responsible for commit and refresh while `modules/items/repository.py` and the item `crud` compatibility functions perform database operations without committing. This keeps public `/api/v1/items/*` behavior stable while testing a transaction boundary that can later support multi-entity item use cases.

## Consequences

- Item route behavior remains unchanged because routes call service-level operations.
- Item repository and `crud.item` callers must explicitly commit or use the item service.
- This transaction contract applies only to items until later tasks migrate users/auth or other modules.

