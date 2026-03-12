---
name: agentbase-identity
description: Register and manage agent identities on the platform. Use when user wants to register an agent, create an agent identity, give an agent a name and profile, list registered agents, update agent metadata, delete an agent registration, or manage how their agent is known to the platform. Agent identity is a prerequisite for retrieving secrets (API keys, OAuth2 tokens, delegated keys) — all auth retrieval APIs require an agent identity name. Also trigger when user says "register my agent", "create agent identity", "give my agent an identity", "agent registration", "create agent profile", "who is my agent", "list my agents", or wants to set up their agent's identity before configuring secrets. To manage the auth providers themselves (create/store API keys, configure OAuth2), use /agentbase-auth. DO NOT use for creating agent source code — use /agentbase-init instead.
argument-hint: <create|list|get|update|delete> [name]
user-invocable: true
---

# AgentBase Identity Management

Manage agent identities on the GreenNode AgentBase Identity Service. Parse the user's arguments to determine the operation and optional identity name.

- **Base URL**: `https://agentbase.api.vngcloud.vn/identity/api/v1`
- **Console**: https://aiplatform.console.vngcloud.vn/identity

## Authentication & Endpoints

Read the shared auth setup reference at `/agentbase` skill's `references/auth-setup.md` for full IAM credential configuration. In brief: check for `GREENNODE_CLIENT_ID` and `GREENNODE_CLIENT_SECRET` in environment variables or `.greennode.json` in the **current working directory only** (do NOT search recursively or look outside the current directory), then use `TOKEN=$(bash .claude/skills/agentbase/scripts/get_token.sh)` to obtain a token. On 401: re-run with `--force`.

**IMPORTANT:** Before constructing any API URL, read `/agentbase` skill's `references/endpoints.md` for the domain validation whitelist. Only use domains listed there.

---

## Interaction Guidelines

- **Guide first, act only when asked** — if the user asks "how to" register or manage agent identities, respond with instructions and guidance only. Do NOT execute API calls or create resources unless they explicitly ask you to do it for them.
- **Confirm before executing (HARD GATE)** — before performing any action (create, update, delete, get), present a clear summary of what will be done (including all parameters and values) and ask the user to confirm. Do NOT auto-execute. Only proceed when the user responds with an explicit confirmation keyword: `yes`, `confirm`, `ok`, `approve`, `proceed`, `go ahead`, `do it`, `ship it`, `lgtm`, or equivalent affirmative. If the user responds with ANYTHING ELSE (parameter changes, questions, corrections, additional info, or ambiguous text), treat it as adjustment input — update the plan and re-present the full summary for confirmation again. NEVER interpret a non-confirmation response as approval. For destructive operations (delete identity), additionally warn that the action is irreversible.
- **Never auto-decide parameters** — when an action requires parameters (e.g., identity name, description, allowedReturnUrls), always ask the user for each required value. You may recommend sensible defaults or examples, but never auto-select or impose values without the user's explicit agreement.
- **Present options, let user choose** — when there are multiple choices, list the available options and let the user pick. Do not make the choice for them.
- **Dry-run support**: When user requests `--dry-run` or preview, show the exact API request (method, URL, headers, payload) and explain the expected outcome WITHOUT executing. Let user review before proceeding.
- **Always read full API response body** — when calling platform APIs, capture and read the full JSON response (not just status codes). This avoids misidentifying field names or data structures, ensures correct field extraction, and enables better error handling and debugging.

## Operations

### create [name]
Create a new agent identity.

- **API**: `POST /agent-identities`
- **Body**: `{"name": "...", "description": "...", "allowedReturnUrls": [...]}`
- Name constraints: 3-50 chars, alphanumeric plus `_` and `-` only (`^[a-zA-Z0-9_-]+$`)
- Ask for `name` if not provided. Optionally ask for `description` and `allowedReturnUrls`.

**SDK (recommended)**:
```python
from greennode_agentbase import IdentityClient, IAMCredentials
from greennode_agentbase.identity import CreateAgentIdentityRequest

creds = IAMCredentials(client_id="...", client_secret="...")
client = IdentityClient(iam_credentials=creds)

# Async
identity = await client.create_agent_identity_async(
    request=CreateAgentIdentityRequest(
        name="my-agent",
        description="My agent identity",
        allowed_return_urls=["https://example.com/callback"],
    )
)
print(identity.name, identity.id)

# Sync
identity = client.create_agent_identity(
    request=CreateAgentIdentityRequest(name="my-agent")
)
```

Note: `IAMCredentials()` with no args will auto-load from env vars `GREENNODE_CLIENT_ID` / `GREENNODE_CLIENT_SECRET` or `.greennode.json`.

**curl**:
```bash
curl -X POST https://agentbase.api.vngcloud.vn/identity/api/v1/agent-identities \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-agent", "description": "My agent", "allowedReturnUrls": []}'
```

### list
List all agent identities (paginated).

- **API**: `GET /agent-identities`
- **Query params**: `page` (0-indexed), `size`, `sortBy`, `sortDirection`

**Note**: Identity Service uses 0-indexed pagination (page=0 is first page). This differs from Runtime Service and Memory Service which use 1-indexed pagination.

**SDK**:
```python
from greennode_agentbase import IdentityClient, IAMCredentials

client = IdentityClient(iam_credentials=IAMCredentials())
result = await client.list_agent_identities_async(page=0, size=20)
for identity in result.content:
    print(f"{identity.name} (id: {identity.id}, created: {identity.created_at})")
print(f"Total: {result.total_elements}, Pages: {result.total_pages}")
```

**curl**:
```bash
curl -X GET "https://agentbase.api.vngcloud.vn/identity/api/v1/agent-identities?page=0&size=20" \
  -H "Authorization: Bearer $TOKEN"
```

### get [name]
Get details of a specific agent identity.

- **API**: `GET /agent-identities/{name}`
- Ask for `name` if not provided.

**SDK**:
```python
client = IdentityClient(iam_credentials=IAMCredentials())
identity = await client.get_agent_identity_async(name="my-agent")
print(f"Name: {identity.name}")
print(f"ID: {identity.id}")
print(f"Description: {identity.description}")
print(f"Allowed Return URLs: {identity.allowed_return_urls}")
print(f"Created: {identity.created_at}")
```

**curl**:
```bash
curl -X GET https://agentbase.api.vngcloud.vn/identity/api/v1/agent-identities/my-agent \
  -H "Authorization: Bearer $TOKEN"
```

### update [name]
Update an existing agent identity.

- **API**: `PUT /agent-identities/{name}`
- **Body**: `{"description": "...", "allowedReturnUrls": [...]}`
- Ask for `name` if not provided. Ask which fields to update.

**SDK**:
```python
from greennode_agentbase import IdentityClient, IAMCredentials
from greennode_agentbase.identity import UpdateAgentIdentityRequest

client = IdentityClient(iam_credentials=IAMCredentials())
identity = await client.update_agent_identity_async(
    name="my-agent",
    request=UpdateAgentIdentityRequest(
        description="Updated description",
        allowed_return_urls=["https://example.com/callback"],
    )
)
print(f"Updated: {identity.name}")
```

**curl**:
```bash
curl -X PUT "https://agentbase.api.vngcloud.vn/identity/api/v1/agent-identities/my-agent" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"description": "Updated description", "allowedReturnUrls": ["https://example.com/callback"]}'
```

### delete [name]

**Before deleting**: Consider exporting or noting the resource configuration, as deletion is irreversible. There is no undo.

Delete an agent identity. This is irreversible -- confirm with the user before proceeding.

- **API**: `DELETE /agent-identities/{name}`
- Ask for `name` if not provided.

**SDK**:
```python
client = IdentityClient(iam_credentials=IAMCredentials())
await client.delete_agent_identity_async(name="my-agent")
```

**curl**:
```bash
curl -X DELETE https://agentbase.api.vngcloud.vn/identity/api/v1/agent-identities/my-agent \
  -H "Authorization: Bearer $TOKEN"
```

## Response Model

`AgentIdentityResponse` fields:
- `id` (str) - Unique identifier
- `name` (str) - Identity name
- `description` (str, optional)
- `allowed_return_urls` (list[str], optional) - OAuth2 callback URLs
- `created_at` (datetime)
- `updated_at` (datetime)

## Relationship with Auth (Secrets Retrieval)

Agent identity is a **required prerequisite** for retrieving secrets from auth providers. All secret retrieval APIs require an `agentIdentityName` parameter:

- `GET /outbound-auth/api-key-providers/{providerName}/agent-identities/{agentName}/api-key` — retrieve stored API key
- `POST /outbound-auth/delegated-api-key-providers/{providerName}/agent-identities/{agentName}/api-key` — request delegated key
- `POST /outbound-auth/oauth2-providers/{providerName}/agent-identities/{agentName}/tokens/m2m` — get M2M token
- `POST /outbound-auth/oauth2-providers/{providerName}/agent-identities/{agentName}/tokens/3lo` — get 3LO token

**Workflow**: Create an agent identity first (this skill), then create auth providers and retrieve secrets using that identity (`/agentbase-auth`).

## Runtime Auto-Injection

When an agent is deployed on AgentBase Runtime, the IAM service account and Agent Identity are managed by the runtime system and automatically injected into the container. The SDK automatically uses these — no manual credential configuration needed in agent code.

The IAM credentials and identity management described in this skill are for **local development** and **platform management** (creating/listing/updating identities from outside the runtime).

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| 401 Unauthorized | Expired or invalid IAM token | Re-obtain token with valid credentials |
| 403 Forbidden | Service account lacks identity permissions | Check IAM roles at https://iam.console.vngcloud.vn |
| 409 Conflict | Identity name already exists | Choose a different name or update existing identity |
| Name validation error | Name doesn't match `^[a-zA-Z0-9_-]+$` | Use only alphanumeric, underscore, and hyphen. 3-50 chars. |
| `.greennode.json` not found | Config file missing or wrong directory | Create `.greennode.json` with `client_id`, `client_secret` fields |

## Instructions

1. Parse the user's argument to determine the operation (`create`, `list`, `get`, `update`, `delete`).
2. If credentials are not configured, present the user with the two options (Auto create / I already have) as described in the Authentication section above.
3. For **create**:
   a. **Always list existing identities first** — call `GET /agent-identities?page=0&size=100` and show the user what already exists on the platform.
   b. If identities exist, **ask the user**: "You have these existing identities: [list]. Do you want to use one of these, or create a new one?"
   c. If the user wants to create a new one, ask for each parameter individually:
      - `name` (required) — suggest a sensible default if context is available, but **always ask for confirmation**
      - `description` (optional) — ask if they want to add one
      - `allowedReturnUrls` (optional) — ask if they want to configure callback URLs
   d. **Show a confirmation summary** with all parameters before executing the API call. Wait for explicit user approval.
   e. If the API returns 409 Conflict (name already exists), inform the user and ask whether to use the existing identity or choose a different name.
4. For other operations (`list`, `get`, `update`, `delete`): if a name is needed and not provided, ask for it.
5. Show the appropriate SDK or curl example based on the user's context.
