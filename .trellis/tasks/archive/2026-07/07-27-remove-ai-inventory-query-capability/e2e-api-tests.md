# API removal verification cases

| ID | Setup / action | Expected result | Side effects to verify |
| --- | --- | --- | --- |
| AI-REMOVE-001 | Start the backend after removing AI route registration and inspect OpenAPI. | `/api/v1/ai/inventory/query` and `/api/v1/internal/ai/**` are absent. | No AI schemas or generated `AiService` remain. |
| AI-REMOVE-002 | `POST /api/v1/ai/inventory/query` against the running backend. | The request is a normal 404, not an AI-specific 503/403 response. | No `ai_run` row is created. |
| AI-REMOVE-003 | Apply the removal migration in an isolated database containing the prior AI revision. | Upgrade succeeds and both AI tables/enums are absent. | Existing non-AI tables and rows remain available. |
| AI-REMOVE-004 | Downgrade from the removal revision to `8c4d1e7a2b5f`. | Empty `ai_run`/`ai_tool_call` schema and enum types are recreated. | No historical AI rows are restored. |
| AI-REMOVE-005 | Upgrade the same database back to head. | Removal migration succeeds again. | AI tables/enums are absent; IAM, scheduler, and inventory schema remains intact. |
