---
name: agentbase-auth
description: Store secrets and configure external service authentication for AI agents. Use when user wants to store an API key or secret securely, connect their agent to external APIs (e.g. OpenAI, Google, Slack), manage credentials for third-party services, set up bring-your-own-key flows, configure OAuth2 providers, manage delegated keys, store environment variables for their agent, or retrieve stored credentials at runtime. Also trigger when user says "store API key", "add secret", "manage credentials", "connect to external API", "store OpenAI key", "agent needs to call external service", "secure my API keys", "manage agent secrets", "store credentials securely", "outbound auth", "create API key for [service name]", "set environment variable", "env vars for my agent", "store env var", or wants their agent to securely access third-party services. When user mentions a specific external service name (OpenAI, Google, Slack, Stripe, etc.) alongside "API key" or "credentials", trigger this skill — not /aip. Requires an agent identity (created via /agentbase-identity) for retrieving secrets. DO NOT use for registering the agent itself on the platform — use /agentbase-identity instead. DO NOT use for platform LLM API keys — use /aip instead.
argument-hint: <apikey|delegated|oauth2> <create|list|get|update|delete> [name]
user-invocable: true
---

# AgentBase Outbound Authentication

Manage outbound authentication providers on the GreenNode AgentBase Identity Service. These providers allow agents to authenticate with external services (LLM APIs, SaaS tools, etc.).

> **Note**: This skill manages outbound authentication for external services (API keys, OAuth2). For platform IAM credentials (client_id/client_secret for accessing GreenNode APIs), see `/agentbase-wizard` Step 1 or the `/agentbase` reference skill.

## Authentication & Endpoints

Read the shared auth setup reference at `/agentbase` skill's `references/auth-setup.md` for full IAM credential configuration. In brief: check for `GREENNODE_CLIENT_ID` and `GREENNODE_CLIENT_SECRET` in environment variables or `.greennode.json` in the **current working directory only** (do NOT search recursively or look outside the current directory), then use `TOKEN=$(bash .claude/skills/agentbase/scripts/get_token.sh)` to obtain a token. On 401: re-run with `--force`.

**IMPORTANT:** Before constructing any API URL, read `/agentbase` skill's `references/endpoints.md` for the domain validation whitelist. Only use domains listed there.

---

## Interaction Guidelines

- **Guide first, act only when asked** — if the user asks "how to" set up authentication or manage credentials, respond with instructions and guidance only. Do NOT execute API calls or create resources unless they explicitly ask you to do it for them.
- **Confirm before executing (HARD GATE)** — before performing any action (create, update, delete, retrieve), present a clear summary of what will be done (including all parameters and values) and ask the user to confirm. Do NOT auto-execute. Only proceed when the user responds with an explicit confirmation keyword: `yes`, `confirm`, `ok`, `approve`, `proceed`, `go ahead`, `do it`, `ship it`, `lgtm`, or equivalent affirmative. If the user responds with ANYTHING ELSE (parameter changes, questions, corrections, additional info, or ambiguous text), treat it as adjustment input — update the plan and re-present the full summary for confirmation again. NEVER interpret a non-confirmation response as approval. For destructive operations (delete provider), additionally warn that the action is irreversible.
- **Never auto-decide parameters** — when an action requires parameters (e.g., provider name, apikey value, OAuth2 fields), always ask the user for each required value. You may recommend sensible defaults or examples, but never auto-select or impose values without the user's explicit agreement.
- **Present options, let user choose** — when there are multiple choices (e.g., provider type, operation), list the available options and let the user pick. Do not make the choice for them.
- **For create operations involving secrets** (apikey, clientSecret), remind the user not to commit secrets to source control.
- **Dry-run support**: When user requests `--dry-run` or preview, show the exact API request (method, URL, headers, payload) and explain the expected outcome WITHOUT executing. Let user review before proceeding.
- **Always read full API response body** — when calling platform APIs, capture and read the full JSON response (not just status codes). This avoids misidentifying field names or data structures, ensures correct field extraction, and enables better error handling and debugging.

## Provider Type 1: Static API Key (`apikey`)

Store a static API key (e.g., an OpenAI key) that agents can retrieve at runtime.

### apikey create [name]
- **API**: `POST /api/v1/outbound-auth/api-key-providers`
- **Body**: `{"name": "...", "apikey": "sk-..."}`
- Name constraints: 3-50 chars, `^[a-zA-Z0-9_-]+$`
- Ask for `name` and `apikey`. The apikey value is the actual secret key to store.

**SDK**:
```python
from greennode_agentbase import IdentityClient, IAMCredentials
from greennode_agentbase.identity import CreateApikeyProviderRequest

client = IdentityClient(iam_credentials=IAMCredentials())
provider = await client.create_api_key_provider_async(
    request=CreateApikeyProviderRequest(name="openai-key", apikey="sk-...")
)
print(f"Created: {provider.name} (status: {provider.status})")
```

**curl**:
```bash
# Get IAM token first (see authentication section below)
curl -X POST https://agentbase.api.vngcloud.vn/identity/api/v1/outbound-auth/api-key-providers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "openai-key", "apikey": "sk-..."}'
```

### apikey list
- **API**: `GET /api/v1/outbound-auth/api-key-providers`
- **Query params**: `page` (0-indexed), `size`, `sortBy`, `sortDirection`

**SDK**:
```python
client = IdentityClient(iam_credentials=IAMCredentials())
result = await client.list_api_key_providers_async(page=0, size=20)
for p in result.content:
    print(f"{p.name} (status: {p.status}, id: {p.id})")
```

**curl**:
```bash
curl -X GET "https://agentbase.api.vngcloud.vn/identity/api/v1/outbound-auth/api-key-providers?page=0&size=20" \
  -H "Authorization: Bearer $TOKEN"
```

### apikey get [name]
- **API**: `GET /api/v1/outbound-auth/api-key-providers/{name}`

**SDK**:
```python
provider = await client.get_api_key_provider_async(name="openai-key")
print(f"Name: {provider.name}, Status: {provider.status}")
```

**curl**:
```bash
curl -X GET "https://agentbase.api.vngcloud.vn/identity/api/v1/outbound-auth/api-key-providers/openai-key" \
  -H "Authorization: Bearer $TOKEN"
```

### apikey update [name]
Update an existing API key provider (e.g., rotate the stored key).

- **API**: `PUT /api/v1/outbound-auth/api-key-providers/{name}`
- **Body**: `{"apikey": "sk-new-..."}`

**SDK**:
```python
from greennode_agentbase.identity import UpdateApikeyProviderRequest

provider = await client.update_api_key_provider_async(
    name="openai-key",
    request=UpdateApikeyProviderRequest(apikey="sk-new-...")
)
print(f"Updated: {provider.name}")
```

**curl**:
```bash
curl -X PUT "https://agentbase.api.vngcloud.vn/identity/api/v1/outbound-auth/api-key-providers/openai-key" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"apikey": "sk-new-..."}'
```

### apikey delete [name]

**Before deleting**: Consider exporting or noting the resource configuration, as deletion is irreversible. There is no undo.

- **API**: `DELETE /api/v1/outbound-auth/api-key-providers/{name}`
- Confirm with the user before proceeding.

**SDK**:
```python
await client.delete_api_key_provider_async(name="openai-key")
```

**curl**:
```bash
curl -X DELETE "https://agentbase.api.vngcloud.vn/identity/api/v1/outbound-auth/api-key-providers/openai-key" \
  -H "Authorization: Bearer $TOKEN"
```

### apikey retrieve-key [providerName] [agentName]
Retrieve the stored API key for a specific agent identity.

- **API**: `GET /api/v1/outbound-auth/api-key-providers/{providerName}/agent-identities/{agentName}/api-key`

**SDK**:
```python
result = await client.get_api_key_for_agent_identity_async(
    provider_name="openai-key",
    agent_identity_name="my-agent",
)
print(f"API Key: {result.apikey}")
```

**curl**:
```bash
curl -X GET "https://agentbase.api.vngcloud.vn/identity/api/v1/outbound-auth/api-key-providers/openai-key/agent-identities/my-agent/api-key" \
  -H "Authorization: Bearer $TOKEN"
```

For decorator usage examples (`@requires_api_key`), see `references/usage.md`.

---

## Provider Type 2: Delegated API Key (`delegated`)

Delegated keys enable user-federation flows where end-users provide their own API keys through a consent flow.

### delegated create [name]
- **API**: `POST /api/v1/outbound-auth/delegated-api-key-providers`
- **Body**: `{"name": "..."}`
- Only requires a name (no key stored upfront -- keys come from end-users).

**SDK**:
```python
from greennode_agentbase.identity import CreateDelegatedApiKeyProviderRequest

provider = await client.create_delegated_api_key_provider_async(
    request=CreateDelegatedApiKeyProviderRequest(name="user-openai-key")
)
print(f"Created: {provider.name} (status: {provider.status})")
```

**curl**:
```bash
curl -X POST https://agentbase.api.vngcloud.vn/identity/api/v1/outbound-auth/delegated-api-key-providers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "user-openai-key"}'
```

### delegated list
- **API**: `GET /api/v1/outbound-auth/delegated-api-key-providers`
- **Query params**: `page` (0-indexed), `size`, `sortBy`, `sortDirection`

**SDK**:
```python
result = await client.list_delegated_api_key_providers_async(page=0, size=20)
for p in result.content:
    print(f"{p.name} (status: {p.status})")
```

### delegated get [name]
- **API**: `GET /api/v1/outbound-auth/delegated-api-key-providers/{name}`

**SDK**:
```python
provider = await client.get_delegated_api_key_provider_async(name="user-openai-key")
```

**curl**:
```bash
curl -X GET "https://agentbase.api.vngcloud.vn/identity/api/v1/outbound-auth/delegated-api-key-providers/user-openai-key" \
  -H "Authorization: Bearer $TOKEN"
```

### delegated delete [name]

**Before deleting**: Consider exporting or noting the resource configuration, as deletion is irreversible. There is no undo.

- **API**: `DELETE /api/v1/outbound-auth/delegated-api-key-providers/{name}`
- Confirm with user before proceeding.

**SDK**:
```python
await client.delete_delegated_api_key_provider_async(name="user-openai-key")
```

**curl**:
```bash
curl -X DELETE "https://agentbase.api.vngcloud.vn/identity/api/v1/outbound-auth/delegated-api-key-providers/user-openai-key" \
  -H "Authorization: Bearer $TOKEN"
```

### delegated request-key [providerName] [agentIdentityName]
Request a delegated API key (triggers user-federation flow). For full API details, SDK examples, and decorator usage (`@requires_api_key` with `USER_FEDERATION` flow), see `references/usage.md`.

---

## Provider Type 3: OAuth2 (`oauth2`)

Register external OAuth2 providers (e.g., Google, GitHub, Slack) for agent-to-service authentication.

### oauth2 create [name]
- **API**: `POST /api/v1/outbound-auth/oauth2-providers`
- **Body**: `{"name": "...", "clientId": "...", "clientSecret": "...", "authorizationUrl": "...", "tokenUrl": "..."}`
- Ask for all required fields: name, clientId, clientSecret, authorizationUrl, tokenUrl.

**SDK**:
```python
from greennode_agentbase.identity import CreateOauth2ProviderRequest

provider = await client.create_oauth2_provider_async(
    request=CreateOauth2ProviderRequest(
        name="google-oauth",
        client_id="xxx.apps.googleusercontent.com",
        client_secret="GOCSPX-xxx",
        authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
    )
)
print(f"Created: {provider.name} (callback: {provider.callback_url})")
```

**curl**:
```bash
curl -X POST https://agentbase.api.vngcloud.vn/identity/api/v1/outbound-auth/oauth2-providers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "google-oauth",
    "clientId": "xxx.apps.googleusercontent.com",
    "clientSecret": "GOCSPX-xxx",
    "authorizationUrl": "https://accounts.google.com/o/oauth2/v2/auth",
    "tokenUrl": "https://oauth2.googleapis.com/token"
  }'
```

### oauth2 list
- **API**: `GET /api/v1/outbound-auth/oauth2-providers`
- **Query params**: `page` (0-indexed), `size`, `sortBy`, `sortDirection`

**SDK**:
```python
result = await client.list_oauth2_providers_async(page=0, size=20)
for p in result.content:
    print(f"{p.name} (status: {p.status}, callback: {p.callback_url})")
```

### oauth2 get [name]
- **API**: `GET /api/v1/outbound-auth/oauth2-providers/{name}`

**SDK**:
```python
provider = await client.get_oauth2_provider_async(name="google-oauth")
print(f"Name: {provider.name}")
print(f"Client ID: {provider.client_id}")
print(f"Authorization URL: {provider.authorization_url}")
print(f"Token URL: {provider.token_url}")
print(f"Callback URL: {provider.callback_url}")
print(f"Status: {provider.status}")
```

**curl**:
```bash
curl -X GET "https://agentbase.api.vngcloud.vn/identity/api/v1/outbound-auth/oauth2-providers/google-oauth" \
  -H "Authorization: Bearer $TOKEN"
```

### oauth2 update [name]
Update an existing OAuth2 provider configuration.

- **API**: `PUT /api/v1/outbound-auth/oauth2-providers/{name}`
- **Body**: `{"clientId": "...", "clientSecret": "...", "authorizationUrl": "...", "tokenUrl": "..."}`

**SDK**:
```python
from greennode_agentbase.identity import UpdateOauth2ProviderRequest

provider = await client.update_oauth2_provider_async(
    name="google-oauth",
    request=UpdateOauth2ProviderRequest(
        client_id="new-xxx.apps.googleusercontent.com",
        client_secret="GOCSPX-new-xxx",
        authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
    )
)
print(f"Updated: {provider.name}")
```

**curl**:
```bash
curl -X PUT "https://agentbase.api.vngcloud.vn/identity/api/v1/outbound-auth/oauth2-providers/google-oauth" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "clientId": "new-xxx.apps.googleusercontent.com",
    "clientSecret": "GOCSPX-new-xxx",
    "authorizationUrl": "https://accounts.google.com/o/oauth2/v2/auth",
    "tokenUrl": "https://oauth2.googleapis.com/token"
  }'
```

### oauth2 delete [name]

**Before deleting**: Consider exporting or noting the resource configuration, as deletion is irreversible. There is no undo.

- **API**: `DELETE /api/v1/outbound-auth/oauth2-providers/{name}`
- Confirm with user before proceeding.

**SDK**:
```python
await client.delete_oauth2_provider_async(name="google-oauth")
```

**curl**:
```bash
curl -X DELETE "https://agentbase.api.vngcloud.vn/identity/api/v1/outbound-auth/oauth2-providers/google-oauth" \
  -H "Authorization: Bearer $TOKEN"
```

### oauth2 m2m-token [providerName] [agentIdentityName]
Get a machine-to-machine (M2M) OAuth2 token using client credentials flow. For full API details, SDK examples, and decorator usage (`@requires_access_token`), see `references/usage.md`.

### oauth2 3lo-token [providerName] [agentIdentityName]
Get a 3-legged OAuth (3LO) token via user authorization flow. For full API details, SDK examples, and decorator usage (`@requires_access_token`), see `references/usage.md`.

---

## Base URL

Production: `https://agentbase.api.vngcloud.vn/identity/api/v1`

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| 401 Unauthorized | Expired or invalid IAM token | Re-obtain token with valid `client_id`/`client_secret` |
| 403 Forbidden | Service account lacks permissions | Check IAM roles at https://iam.console.vngcloud.vn |
| 404 Not Found | Provider name does not exist | Verify the provider name with a `list` operation |
| 409 Conflict | Provider with same name already exists | Choose a different name or update the existing provider |
| Invalid apikey format | Key value rejected by validation | Check the key format matches the external service's requirements |

## Runtime Auto-Injection

When an agent is deployed on AgentBase Runtime, the IAM service account and Agent Identity are managed by the runtime system and automatically injected into the container. The SDK automatically uses these — auth decorators and credential retrieval work without any manual configuration in agent code.

The IAM credentials in this skill's Authentication section are for **platform management** (creating/managing auth providers from outside the runtime) and **local development**.

## Prerequisites

Auth operations that retrieve keys or tokens (e.g., `apikey retrieve-key`, `delegated request-key`, `oauth2 m2m-token`, `oauth2 3lo-token`) require an **agent identity name**. On AgentBase Runtime, this is automatically managed and injected by the runtime system. For local development, if the user hasn't created one yet, guide them to create an agent identity first using `/agentbase-identity` before proceeding with these operations.

## Credential Rotation

For detailed credential rotation guides (API keys, OAuth2, delegated, IAM), see `references/credential-rotation.md`.

## Instructions

1. Parse the user's arguments to determine provider type (`apikey`, `delegated`, `oauth2`) and operation.
2. If the operation requires an agent identity name and the user hasn't provided one, ask for it — and if they don't have an agent identity yet, direct them to `/agentbase-identity` to create one first.
3. If the provider type is unclear, ask the user:
   - **apikey**: "I have a static API key (e.g., OpenAI key) to store"
   - **delegated**: "I want end-users to provide their own API keys"
   - **oauth2**: "I need OAuth2 integration with an external service"
4. Ask for required fields not provided in the arguments.
5. Show SDK examples by default. Show curl examples if user specifically asks or if working outside Python.
6. If credentials are not configured, present the user with the two options (Auto create / I already have) as described in the Authentication section above.
