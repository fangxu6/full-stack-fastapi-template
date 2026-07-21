# AI inventory Yaak guide

Use Yaak to call the public FastAPI BFF. Yaak must not call the sidecar or
internal inventory endpoints directly.

## Before you send a request

Confirm that these checks return `200 OK`:

```powershell
curl.exe --noproxy "*" -i http://127.0.0.1:8000/api/v1/utils/health-check/
curl.exe --noproxy "*" -i http://127.0.0.1:3000/health
```

The caller must be an active superadmin. A normal user, inactive user, or
anonymous request cannot use the AI BFF.

If Yaak uses a system proxy, add `127.0.0.1` and `localhost` to its proxy bypass
list. A proxy-generated `502` is not a FastAPI response.

## Get an access token

Create a Yaak HTTP request with these settings:

| Field | Value |
| --- | --- |
| Method | `POST` |
| URL | `http://127.0.0.1:8000/api/v1/login/access-token` |
| Authentication | None |
| Body type | Form URL Encoded |

Add these form fields:

| Key | Value |
| --- | --- |
| `username` | Superadmin email address |
| `password` | Superadmin password |

Send the request. The response contains `access_token` and `token_type`.
Store only `access_token` in Yaak's private environment or the Bearer Auth token
field. Do not place it in a shared request body or export.

## Send an inventory question

Create a second Yaak HTTP request:

| Field | Value |
| --- | --- |
| Method | `POST` |
| URL | `http://127.0.0.1:8000/api/v1/ai/inventory/query` |
| Authentication | Bearer Token |
| Token | The `access_token` from the login response |
| Body type | JSON |

Use a bounded question:

```json
{
  "question": "请查询当前成品库存余额，并说明数据来源。"
}
```

Yaak creates this header through its Bearer authentication setting:

```http
Authorization: Bearer <access_token>
```

Do not add these fields or headers:

- `run_id`
- `X-AI-Orchestrator-Token`
- `X-AI-Actor-Grant`
- `X-AI-Service-Token`
- `AI_PROVIDER_API_KEY`

FastAPI creates the run ID and actor grant, then supplies the internal service
credentials server-to-server.

## Read a successful response

A successful request returns `200 OK`:

```json
{
  "run_id": "<uuid>",
  "answer": "<Chinese inventory answer>",
  "citations": [
    {
      "source": "inventory:balances",
      "summary": "<source summary>"
    }
  ]
}
```

Treat citations as the answer's inventory evidence. The public response does
not expose provider keys, actor grants, service tokens, raw tool payloads, or
provider request IDs.

## Interpret error responses

| HTTP status | Example detail | Meaning | Check |
| --- | --- | --- | --- |
| `401` or `403` | Authorization error | Token is missing, invalid, inactive, or not a superadmin | Login with an active superadmin |
| `422` | Validation error | Request body is invalid or the question length is outside the contract | Send only a non-empty `question` |
| `500` | `Internal Server Error` | The database schema may be missing `ai_run` | Check Alembic revision before retrying |
| `503` | `AI inventory query is unavailable` | FastAPI did not receive a completed sidecar envelope | Check sidecar health, provider compatibility, and the audit row using `request_id` |

Every response includes `X-Request-ID` and usually a matching `request_id` in
the error body. Record that value when reporting a problem. It correlates the
Yaak request with `ai_run` and sidecar operational logs without recording the
full question.

## Known provider limitation

The current provider responds to ordinary Chat Completions but does not produce
the JSON Schema structured object required by the Mastra sidecar. Until it
supports structured output and tool calling for the fixed model, Yaak receives
the expected `503` response after authentication succeeds. This is a provider
compatibility failure, not a Yaak request configuration failure.
