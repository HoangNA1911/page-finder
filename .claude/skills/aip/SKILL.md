---
name: aip
description: Manage GreenNode AI Platform API keys and LLM models (MAAS). Use when user wants to create/list/delete API keys for AI Platform, browse available LLM models, check model rate limits, get an OpenAI-compatible endpoint and key for their AI agent, or find out which models are available on GreenNode. Also trigger when user mentions "AI Platform", "MAAS", "GreenNode LLM", "GreenNode model", or wants to set up LLM access for their agent. DO NOT use for AgentBase runtime management (use /agentbase-runtime) or agent identity registration (use /agentbase-identity).
argument-hint: <api-keys|models> <list|create|get|delete> [name-or-uuid]
---

# GreenNode AI Platform — API Keys & LLM Models

Manage API keys and browse LLM models on the GreenNode AI Platform (MAAS). API keys created here are OpenAI-compatible and can be used with the LLM endpoint to power AI agents.

**LLM Endpoint (OpenAI-compatible):** `https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1`

## Authentication & Endpoints

Read the shared auth setup reference at `/agentbase` skill's `references/auth-setup.md` for full IAM credential configuration. In brief: check for `GREENNODE_CLIENT_ID` and `GREENNODE_CLIENT_SECRET` in environment variables or `.greennode.json` in the **current working directory only** (do NOT search recursively or look outside the current directory), then use `TOKEN=$(bash .claude/skills/agentbase/scripts/get_token.sh)` to obtain a token. On 401: re-run with `--force`.

**IMPORTANT:** Before constructing any API URL, read `/agentbase` skill's `references/endpoints.md` for the domain validation whitelist. Only use domains listed there.

**This skill uses TWO different domains — do NOT confuse them:**

| Purpose | Base URL |
|---------|----------|
| Management API (API key CRUD, model listing) | `https://aiplatform-hcm.api.vngcloud.vn` |
| LLM Endpoint (OpenAI-compatible inference) | `https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1` |

- To list/create/delete API keys → `https://aiplatform-hcm.api.vngcloud.vn/v1/api-keys`
- To list/inspect models → `https://aiplatform-hcm.api.vngcloud.vn/v1/models`
- To call LLM at runtime → `https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1`

## Interaction Guidelines

- **Guide first, act only when asked** — if the user asks "how to" manage API keys or browse models, respond with instructions and guidance only. Do NOT execute API calls or create resources unless they explicitly ask you to do it for them.
- **Confirm before executing (HARD GATE)** — before performing any action (create, delete, enable/disable model, list), present a clear summary of what will be done (including all parameters and values) and ask the user to confirm. Do NOT auto-execute. Only proceed when the user responds with an explicit confirmation keyword: `yes`, `confirm`, `ok`, `approve`, `proceed`, `go ahead`, `do it`, `ship it`, `lgtm`, or equivalent affirmative. If the user responds with ANYTHING ELSE (parameter changes, questions, corrections, additional info, or ambiguous text), treat it as adjustment input — update the plan and re-present the full summary for confirmation again. NEVER interpret a non-confirmation response as approval. For destructive operations (delete API key), additionally warn that the action is irreversible.
- **Never auto-decide parameters** — when an action requires parameters (e.g., API key name, model UUID), always ask the user for each required value. You may recommend sensible defaults or examples, but never auto-select or impose values without the user's explicit agreement.
- **Present options, let user choose** — when there are multiple choices (e.g., existing API keys, available models), list the available options and let the user pick. Do not make the choice for them.
- **Dry-run support**: When user requests `--dry-run` or preview, show the exact API request (method, URL, headers, payload) and explain the expected outcome WITHOUT executing. Let user review before proceeding.

---

## API Key Management

API keys grant access to LLM models through the OpenAI-compatible endpoint. Once you have a key, you can use it like an OpenAI API key.

### api-keys list
List all API keys for the current account.

- **API:** `GET /v1/api-keys`
- **Query params:** `name` (filter by name), `page` (starts from 1), `size`

**Note**: AI Platform uses 1-indexed pagination (page=1 is first page).

```bash
curl -X GET "https://aiplatform-hcm.api.vngcloud.vn/v1/api-keys?page=1&size=20" \
  -H "Authorization: Bearer $TOKEN"
```

Response contains a paginated list with fields: `listData` (array of keys), `page`, `pageSize`, `totalPage`, `totalItem`. Each key has: `id`, `name`, `key`, `status`, `isDefault`, `models`, `createdAt`.

### api-keys create [name]
Create a new API key. **This operation is async** — poll until status is `ACTIVE`.

- **API:** `POST /v1/api-keys`
- **Body:** `{"name": "my-api-key", "isDefault": false}`
- **Name constraints:** 5-50 chars, pattern `^[a-z0-9\-]{5,50}$` (lowercase letters, digits, hyphens only)

**Step 1 — Submit creation:**
```bash
curl -X POST "https://aiplatform-hcm.api.vngcloud.vn/v1/api-keys" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-agent-key"}'
```

**Step 2 — Poll until ACTIVE** (retry every 3s, up to ~30s):
```bash
# Repeat until .data.status == "ACTIVE"
curl -X GET "https://aiplatform-hcm.api.vngcloud.vn/v1/api-keys/my-agent-key" \
  -H "Authorization: Bearer $TOKEN"
```

The `key` field in the response is the actual API key value. Save it immediately as it may not be retrievable later.

**If creation fails with a quota error** (e.g. 400/409 indicating quota exhausted), do NOT retry. Instead:
1. List all existing API keys using `GET /v1/api-keys`.
2. Present the list to the user and explain that their API key quota is full.
3. Suggest the user **delete an unused key** to free up quota. Ask which key they want to delete.
4. After deletion completes (poll until 404), retry creating the new key.

After creating a key, remind the user:
> Your API key can be used as an OpenAI-compatible key:
> - **Base URL:** `https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1`
> - **API Key:** *(the key from the response)*

### api-keys get [name]
Get details of a specific API key.

- **API:** `GET /v1/api-keys/{apiKeyName}`

```bash
curl -X GET "https://aiplatform-hcm.api.vngcloud.vn/v1/api-keys/my-agent-key" \
  -H "Authorization: Bearer $TOKEN"
```

### api-keys update [name]
Update an API key (currently supports setting default status).

- **API:** `PUT /v1/api-keys/{apiKeyName}`
- **Body:** `{"isDefault": true}`

```bash
curl -X PUT "https://aiplatform-hcm.api.vngcloud.vn/v1/api-keys/my-agent-key" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"isDefault": true}'
```

### api-keys delete [name]
Delete an API key. Confirm with the user before proceeding. **This operation is async** — poll until the key no longer exists (404).

- **API:** `DELETE /v1/api-keys/{apiKeyName}`

**Step 1 — Submit deletion:**
```bash
curl -X DELETE "https://aiplatform-hcm.api.vngcloud.vn/v1/api-keys/my-agent-key" \
  -H "Authorization: Bearer $TOKEN"
```

**Step 2 — Poll until 404** (retry every 3s, up to ~30s):
```bash
# Repeat until HTTP 404 is returned (key no longer exists)
curl -s -o /dev/null -w "%{http_code}" \
  -X GET "https://aiplatform-hcm.api.vngcloud.vn/v1/api-keys/my-agent-key" \
  -H "Authorization: Bearer $TOKEN"
```

Confirm deletion to the user only after receiving 404.

---

## LLM Model Management

Browse, inspect, and enable/disable available LLM models. These models are accessible via the OpenAI-compatible endpoint using an API key from above.

### models list
List available models with optional filters.

- **API:** `GET /v1/models`
- **Query params:**
  - `name` — filter by model name
  - `modelTypes` — filter by type (array, e.g. `modelTypes=chat&modelTypes=embedding`)
  - `providers` — filter by provider (array)
  - `useCases` — filter by use case (array)
  - `status` — filter by status
  - `resourceType` — filter by resource type
  - `zone` — filter by zone
  - `page` (starts from 1), `size` — pagination

```bash
# List all models
curl -X GET "https://aiplatform-hcm.api.vngcloud.vn/v1/models?page=1&size=20" \
  -H "Authorization: Bearer $TOKEN"

# Filter by provider
curl -X GET "https://aiplatform-hcm.api.vngcloud.vn/v1/models?providers=openai&page=1&size=20" \
  -H "Authorization: Bearer $TOKEN"
```

Response contains: `listData` (array of models), `page`, `pageSize`, `totalPage`, `totalItem`. Key fields in each model: `uuid`, `name`, `code`, `path`, `description`, `modelStatus`, `isFree`, `provider`, `types`.

### models detail [modelUuid]
Get detailed information about a specific model.

- **API:** `GET /v1/models/detail/{modelUuid}`

```bash
curl -X GET "https://aiplatform-hcm.api.vngcloud.vn/v1/models/detail/MODEL_UUID" \
  -H "Authorization: Bearer $TOKEN"
```

### models metadata
Get available filter options (providers, types, use cases) for model listing.

- **API:** `GET /v1/models/metadata`

```bash
curl -X GET "https://aiplatform-hcm.api.vngcloud.vn/v1/models/metadata" \
  -H "Authorization: Bearer $TOKEN"
```

This is useful to discover what providers, model types, and use cases are available before filtering the model list.

### models enable [modelUuid]
Enable or disable an LLM model for your account. **This operation is async (v2)** — the API initiates a workflow and returns immediately.

- **API:** `POST /v2/models/user-settings`
- **Body:** Array of `{ "modelUuid": "...", "enabled": true|false }`

```bash
# Enable a model
curl -X POST "https://aiplatform-hcm.api.vngcloud.vn/v2/models/user-settings" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '[{"modelUuid": "MODEL_UUID", "enabled": true}]'
```

After enabling, verify by fetching the model detail (`GET /v1/models/detail/{modelUuid}`) and checking `isEnabled == true`.

**Billing errors:** If the enable request fails with a billing-related error (e.g. 400/402/403 indicating unpaid balance, insufficient credits, or billing not activated), do NOT retry. Instead:
1. Inform the user that the operation failed due to a billing issue.
2. Explain that they need to check and resolve their billing status before enabling the model.
3. Direct them to the GreenNode AI Platform console at https://aiplatform.console.vngcloud.vn/models to review their account and billing status.
4. Once billing is resolved, they can retry enabling the model.

### models rate-limit [modelUuid]
Check rate limit configuration for a specific model.

- **API:** `GET /v1/models/rate-limit/{modelUuid}`

```bash
curl -X GET "https://aiplatform-hcm.api.vngcloud.vn/v1/models/rate-limit/MODEL_UUID" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Using with OpenAI SDK

Once you have an API key, you can use GreenNode LLM models with any OpenAI-compatible client:

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_GREENNODE_API_KEY",
    base_url="https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1",
)

response = client.chat.completions.create(
    model="MODEL_PATH",  # use the `path` field from model detail (not `code`)
    messages=[{"role": "user", "content": "Hello!"}],
)
print(response.choices[0].message.content)
```

```typescript
import OpenAI from "openai";

const client = new OpenAI({
  apiKey: "YOUR_GREENNODE_API_KEY",
  baseURL: "https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1",
});

const response = await client.chat.completions.create({
  model: "MODEL_PATH",  // use the `path` field from model detail (not `code`)
  messages: [{ role: "user", content: "Hello!" }],
});
```

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| 401 Unauthorized | Expired or invalid IAM token | Re-obtain token with valid `client_id`/`client_secret` |
| 403 Forbidden | Service account lacks permissions | Check IAM permissions at GreenNode IAM console https://iam.console.vngcloud.vn |
| 404 Not Found | API key name or model UUID not found | Verify with a `list` operation |
| 409 Conflict | API key name already exists | Choose a different name |
| Invalid name | Name doesn't match `^[a-z0-9\-]{5,50}$` | Use only lowercase letters, digits, and hyphens (5-50 chars) |
| 400/402/403 on model enable | Billing issue (unpaid balance, no credits, billing not activated) | Check and resolve billing at https://aiplatform.console.vngcloud.vn/models before retrying |

## Instructions

1. Parse the user's request to determine the resource type (`api-keys` or `models`) and operation.
2. If unclear, ask the user what they need:
   - **api-keys**: "I want to create/manage API keys for accessing LLM models"
   - **models**: "I want to see what LLM models are available and their details"
3. **When the user needs an API key, always let the user decide:**
   - First, list existing API keys using `GET /v1/api-keys`.
   - Present the existing keys to the user (if any) and explicitly ask them to choose one of the following options:
     - **Use an existing key** — let the user pick which one from the list
     - **Create a new key** — proceed to create a new API key
   - Do NOT auto-select or auto-use any existing key. The user must explicitly choose.
4. **When creating a new API key fails with a quota error:**
   - Do NOT retry the creation. Explain that the API key quota is full.
   - List all existing API keys and present them to the user.
   - Guide the user to **delete an unused key** to free up quota. Ask which key they want to delete.
   - After deletion completes (poll until 404), retry creating the new key.
5. For `api-keys create`, ask for the key name if not provided. Validate it matches `^[a-z0-9\-]{5,50}$`.
6. **api-keys create is async**: after POST, poll GET /v1/api-keys/{name} every 3s until `.data.status == "ACTIVE"` (timeout ~30s). Only show the key and OpenAI usage info after ACTIVE is confirmed.
7. **api-keys delete is async**: after DELETE, poll GET /v1/api-keys/{name} every 3s until HTTP 404 is returned (timeout ~30s). Only confirm deletion to the user after 404.
8. After creating an API key, always show the OpenAI-compatible usage info (base URL + key).
9. When listing or showing model details, highlight the model `path` field — this is what must be passed as the `model` parameter when calling the LLM API (not `code`). Do NOT show pricing/billing info (`inputPrice`, `outputPrice`) to the user.
10. When the user wants to set up LLM access for an agent, guide them through: (1) browse models to pick one, (2) list existing API keys and reuse one, or create a new key if needed, (3) use the key with the OpenAI SDK pointing to the GreenNode endpoint.
11. **When the user needs to pick a model**, list available models filtered by `status=ENABLED` and sorted by most recent first, then **let the user choose**. Do not auto-select or recommend a specific model unless the user explicitly asks for a recommendation.
12. **When enabling a model** via `POST /v2/models/user-settings`, if the request fails with a billing-related error (400/402/403 with messages about billing, credits, or payment), do NOT retry. Inform the user that the operation failed due to a billing issue and that they need to check and resolve their billing status at https://aiplatform.console.vngcloud.vn/models before retrying. Do not attempt workarounds — billing issues must be resolved by the user.
