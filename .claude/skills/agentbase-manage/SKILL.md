---
name: agentbase-manage
description: Register agent identities, manage outbound authentication providers, and add memory to AI agents. Use when user wants to register an agent, create/list/update/delete agent identities, store API keys or secrets for external services (OpenAI, Google, Slack, etc.), configure OAuth2 providers, manage delegated keys, give their agent memory, persist conversation history, extract facts via semantic search, or integrate LangChain/LangGraph with memory. Also trigger for "register my agent", "create agent identity", "store API key", "manage credentials", "outbound auth", "agent needs memory", "remember conversations", "long-term memory", "search memories", "fact extraction". When user mentions a specific external service name alongside "API key" or "credentials", trigger this skill — not /aip. DO NOT use for creating agent source code — use /agentbase-wizard init instead. DO NOT use for platform LLM API keys — use /aip instead. DO NOT use for runtime logs — use /agentbase-monitor instead.
argument-hint: <identity|auth|memory> <operation> [name]
user-invocable: true
---

# AgentBase Identity, Auth & Memory Management

Manage agent identities, outbound authentication providers, and memory on the GreenNode AgentBase platform. Parse the user's arguments to determine the part (`identity`, `auth`, or `memory`), the operation, and optional name/ID.

> **Note**: Outbound auth manages authentication for external services (API keys, OAuth2). For platform IAM credentials (client_id/client_secret for accessing GreenNode APIs), see `/agentbase-wizard` Step 1 or run `bash .claude/skills/agentbase/scripts/check_credentials.sh iam`.

## Base URLs

- **Identity & Auth**: `https://agentbase.api.vngcloud.vn/identity/api/v1`
- **Memory**: `https://agentbase.api.vngcloud.vn/memory`
- **Console (Identity)**: https://aiplatform.console.vngcloud.vn/identity
- **Console (Memory)**: https://aiplatform.console.vngcloud.vn/memory

## Authentication & Endpoints

Read the shared auth setup reference at `/agentbase` skill's `references/auth-setup.md` for full IAM credential configuration. In brief: run `bash .claude/skills/agentbase/scripts/check_credentials.sh iam` to verify credentials are configured, then use `TOKEN=$(bash .claude/skills/agentbase/scripts/get_token.sh)` to obtain a token. **NEVER read `.greennode.json` or `.env` directly** — always use the helper scripts. On 401: re-run with `--force`. If `check_credentials.sh iam` returns MISSING, **STOP — you MUST read** the **"If Credentials Are Not Found"** section in `/agentbase` skill's `references/auth-setup.md` and follow it exactly. Do NOT skip this or provide your own credential setup instructions.

**IMPORTANT:** Before constructing any API URL, read `/agentbase` skill's `references/endpoints.md` for the domain validation whitelist. Only use domains listed there.

---

## Interaction Guidelines

- **Never assume API response structure** — always inspect the actual response first before extracting or filtering data. Do not guess field names.
- **Guide first, act only when asked** — if the user asks "how to" register identities, manage credentials, or create memory, respond with instructions and guidance only. Do NOT execute API calls or create resources unless they explicitly ask you to do it for them.
- **Confirm before executing (HARD GATE)** — before performing any action (create, update, delete, retrieve, generate, search), present a clear summary of what will be done (including all parameters and values) and ask the user to confirm. Do NOT auto-execute. Only proceed when the user responds with an explicit confirmation keyword: `yes`, `confirm`, `ok`, `approve`, `proceed`, `go ahead`, `do it`, `ship it`, `lgtm`, or equivalent affirmative. If the user responds with ANYTHING ELSE (parameter changes, questions, corrections, additional info, or ambiguous text), treat it as adjustment input — update the plan and re-present the full summary for confirmation again. NEVER interpret a non-confirmation response as approval. For destructive operations (delete identity, delete provider, delete memory, delete event, delete memory record), additionally warn that the action is irreversible.
- **Never auto-decide parameters** — when an action requires parameters (e.g., identity name, provider name, apikey value, OAuth2 fields, memory name, strategy type, event expiry, namespace, actorId, sessionId), always ask the user for each required value. You may recommend sensible defaults or examples, but never auto-select or impose values without the user's explicit agreement.
- **Present options, let user choose** — when there are multiple choices (e.g., provider type, strategy type, operations), list the available options and let the user pick. Do not make the choice for them.
- **For create/update operations involving secrets** (apikey, clientSecret), **NEVER ask the user to paste raw secrets into the chat** — secrets typed in chat are loaded into the LLM context, which is a security risk. Instead, always guide the user to provide secrets via one of these safe methods (in order of preference):
  1. **Environment variable**: Ask the user to `export MY_KEY=sk-...` in their shell first, then use `--apikey-env MY_KEY` or `--client-secret-env MY_SECRET_VAR`
  2. **File**: Ask the user to save the secret to a file (e.g., `.secrets/openai.key`), then use `--apikey-file .secrets/openai.key` or `--client-secret-file .secrets/oauth.key`. Remind them to add the file/directory to `.gitignore`.
  - If the user insists on providing a raw secret directly, warn them that it will be visible in the conversation context, then use `--apikey` or `--client-secret` as a fallback.
  - Also remind the user not to commit secrets to source control.
- **Dry-run support**: When user requests `--dry-run` or preview, show the exact API request (method, URL, headers, payload) and explain the expected outcome WITHOUT executing. Let user review before proceeding.
- **Always read full API response body** — when calling platform APIs, capture and read the full JSON response (not just status codes). This avoids misidentifying field names or data structures, ensures correct field extraction, and enables better error handling and debugging.

## Runtime Auto-Injection

When an agent is deployed on AgentBase Runtime, the IAM service account and Agent Identity are managed by the runtime system and automatically injected into the container as `GREENNODE_CLIENT_ID`, `GREENNODE_CLIENT_SECRET`, and `GREENNODE_AGENT_IDENTITY`. The SDK automatically uses these — no manual credential configuration needed in agent code. Auth decorators, credential retrieval, memory operations, and LangGraph bridge integrations all work automatically.

The IAM credentials and identity/auth/memory management described in this skill are for **local development** and **platform management** (creating/listing/updating resources from outside the runtime). See `/agentbase-deploy runtime` for details on runtime environment management.

---

# Part 1: Identity Management

Manage agent identities on the GreenNode AgentBase Identity Service. An agent identity is a named registration that represents your agent on the platform and is a prerequisite for retrieving secrets from auth providers.

## Identity Operations Summary

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Create | `POST` | `/agent-identities` |
| List | `GET` | `/agent-identities?page=0&size=20` |
| Get | `GET` | `/agent-identities/{name}` |
| Update | `PUT` | `/agent-identities/{name}` |
| Delete | `DELETE` | `/agent-identities/{name}` |

Read `references/identity-ops.md` for full API details, SDK examples, curl commands, and the Identity Response Model.

## Relationship between Identity and Auth

Agent identity is a **required prerequisite** for retrieving secrets from auth providers. All secret retrieval APIs require an `agentIdentityName` parameter:

- `GET /outbound-auth/api-key-providers/{providerName}/agent-identities/{agentName}/api-key` — retrieve stored API key
- `POST /outbound-auth/delegated-api-key-providers/{providerName}/agent-identities/{agentName}/api-key` — request delegated key
- `POST /outbound-auth/oauth2-providers/{providerName}/agent-identities/{agentName}/tokens/m2m` — get M2M token
- `POST /outbound-auth/oauth2-providers/{providerName}/agent-identities/{agentName}/tokens/3lo` — get 3LO token

**Workflow**: Create an agent identity first (identity operations), then create auth providers and retrieve secrets using that identity (auth operations).

## Identity Instructions

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

---

# Part 2: Outbound Authentication

Manage outbound authentication providers on the GreenNode AgentBase Identity Service. These providers allow agents to authenticate with external services (LLM APIs, SaaS tools, etc.).

Three provider types are available:
- **apikey** — Store a static API key (e.g., OpenAI key) that agents retrieve at runtime
- **delegated** — User-federation flow where end-users provide their own API keys
- **oauth2** — Register external OAuth2 providers (e.g., Google, GitHub, Slack)

## Auth Operations Summary

### Static API Key (`apikey`)

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Create | `POST` | `/outbound-auth/api-key-providers` |
| List | `GET` | `/outbound-auth/api-key-providers?page=0&size=20` |
| Get | `GET` | `/outbound-auth/api-key-providers/{name}` |
| Update | `PUT` | `/outbound-auth/api-key-providers/{name}` |
| Delete | `DELETE` | `/outbound-auth/api-key-providers/{name}` |
| Retrieve Key | `GET` | `/outbound-auth/api-key-providers/{providerName}/agent-identities/{agentName}/api-key` |

### Delegated API Key (`delegated`)

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Create | `POST` | `/outbound-auth/delegated-api-key-providers` |
| List | `GET` | `/outbound-auth/delegated-api-key-providers?page=0&size=20` |
| Get | `GET` | `/outbound-auth/delegated-api-key-providers/{name}` |
| Delete | `DELETE` | `/outbound-auth/delegated-api-key-providers/{name}` |
| Request Key | `POST` | `/outbound-auth/delegated-api-key-providers/{providerName}/agent-identities/{agentName}/api-key` |

### OAuth2 (`oauth2`)

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Create | `POST` | `/outbound-auth/oauth2-providers` |
| List | `GET` | `/outbound-auth/oauth2-providers?page=0&size=20` |
| Get | `GET` | `/outbound-auth/oauth2-providers/{name}` |
| Update | `PUT` | `/outbound-auth/oauth2-providers/{name}` |
| Delete | `DELETE` | `/outbound-auth/oauth2-providers/{name}` |
| M2M Token | `POST` | `/outbound-auth/oauth2-providers/{providerName}/agent-identities/{agentName}/tokens/m2m` |
| 3LO Token | `POST` | `/outbound-auth/oauth2-providers/{providerName}/agent-identities/{agentName}/tokens/3lo` |

Read `references/auth-ops.md` for full API details, SDK examples, curl commands, and credential rotation guides.

## Auth Prerequisites

Auth operations that retrieve keys or tokens (e.g., `auth apikey retrieve-key`, `auth delegated request-key`, `auth oauth2 m2m-token`, `auth oauth2 3lo-token`) require an **agent identity name**. On AgentBase Runtime, this is automatically managed and injected by the runtime system. For local development, if the user hasn't created one yet, help them create an agent identity inline (use `bash .claude/skills/agentbase/scripts/identity.sh create --name <name>`) before proceeding with the auth operation. Do NOT redirect to a separate skill invocation — handle identity creation within the current flow.

## Auth Instructions

1. Parse the user's arguments to determine provider type (`apikey`, `delegated`, `oauth2`) and operation.
2. If the operation requires an agent identity name and the user hasn't provided one, ask for it — and if they don't have an agent identity yet, direct them to `/agentbase-manage identity` to create one first.
3. If the provider type is unclear, ask the user:
   - **apikey**: "I have a static API key (e.g., OpenAI key) to store"
   - **delegated**: "I want end-users to provide their own API keys"
   - **oauth2**: "I need OAuth2 integration with an external service"
4. Ask for required fields not provided in the arguments.
5. Show SDK examples by default. Show curl examples if user specifically asks or if working outside Python.
6. If credentials are not configured, present the user with the two options (Auto create / I already have) as described in the Authentication section above.

---

# Part 3: Memory Service

The Memory Service provides conversation history (short-term events) and semantic fact extraction (long-term memory records) for AI agents.

## Core Concepts

| Concept | Description | Lifetime |
|---------|-------------|----------|
| **Memory** | Top-level container that holds events and records | Permanent until deleted |
| **Event** | Single conversation turn (role + content) | Expires after `eventExpiryDuration` days |
| **Actor** | Participant identifier (user ID or agent ID) | Created on first event |
| **Session** | Conversation thread within an actor | Created on first event |
| **Memory Record** | Distilled long-term fact extracted from events | Permanent until deleted |
| **Long-Term Memory Strategy (LTMS)** | Extraction rules for generating memory records | Permanent, configured at memory creation |

### Strategy Types

- `SEMANTIC` - General semantic fact extraction
- `USER_PREFERENCE` - Extract user preferences and habits
- `CUSTOM` - Custom fact extraction with a user-defined prompt (`customFactExtractionPrompt`). **When using `customFactExtractionPrompt`, the type MUST be `CUSTOM`** — using `SEMANTIC` or `USER_PREFERENCE` with a custom prompt will silently ignore the prompt without any error. **Always validate**: if user provides a custom prompt, auto-correct `type` to `CUSTOM` and warn the user about the change. The custom prompt is **prepended** to the built-in extraction prompt, not a replacement.

### Namespace Template

Controls how memory records are partitioned. Default: `/strategies/{memoryStrategyId}/actors/{actorId}`

Available variables: `{memoryStrategyId}`, `{actorId}`, `{sessionId}`

> **Note on `actorId`**: The `actorId` represents the **end-user** (the person interacting with the agent), not the agent itself. Use any string that uniquely identifies the user (e.g. a user ID like `alice`, `user-123`). This allows the memory system to partition and recall facts per user. Do not confuse `actorId` with the agent's identity — for agent identity management, see Part 1 (Identity) above.

## Memory Operations Summary

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Create | `POST` | `/memories` |
| List | `GET` | `/memories?page=1&size=10` |
| Get | `GET` | `/memories/{id}` + `/memories/{id}/long-term-memory-strategies` |
| Delete | `DELETE` | `/memories/{id}` |
| List Events | `GET` | `/memories/{memoryId}/actors/{actorId}/sessions/{sessionId}/events` |
| Create Event | `POST` | `/memories/{memoryId}/actors/{actorId}/sessions/{sessionId}/events` |
| List Actors | `GET` | `/memories/{memoryId}/actors` |
| Browse Records | `GET` | `/memories/{memoryId}/memory-records?namespace=...&limit=100` |
| Search Records | `POST` | `/memories/{memoryId}/memory-records:search?namespace=...` |
| Generate from Session | `POST` | `/memories/{memoryId}/memory-records:generate-from-session?actorId=...&sessionId=...&longTermMemoryStrategyId=...` |
| Generate from Content | `POST` | `/memories/{memoryId}/memory-records:generate-from-content` |
| Insert Directly | `POST` | `/memories/{memoryId}/memory-records:insert-directly` |
| Delete Memory Record | `DELETE` | `/memories/{memoryId}/memory-records/{memoryRecordId}` |
| List Sessions | `GET` | `/memories/{memoryId}/actors/{actorId}/sessions` |
| Delete Event | `DELETE` | `/memories/{memoryId}/actors/{actorId}/sessions/{sessionId}/events/{eventId}` |
| List Strategies | `GET` | `/memories/{memoryId}/long-term-memory-strategies` |

**Note**: Memory Service uses 1-indexed pagination (page=1 is first page). This differs from Identity Service which uses 0-indexed pagination.

Read `references/memory-ops.md` for full API details, SDK examples, curl commands, and framework integration guides.

## Memory Instructions

1. Parse the user's argument to determine the operation.
2. If credentials are not configured, present the user with the two options (Auto create / I already have) as described in the Authentication section above.
3. For **create**: ask for each parameter individually — `name`, `description`, `eventExpiryDuration`, and strategy details (`name`, `type`, `namespaceTemplate`, `enableAutomaticMemoryRecordGeneration`, optionally `customFactExtractionPrompt`). If user provides `customFactExtractionPrompt`, always set `type` to `CUSTOM`.
4. For **get**: always fetch both basic info (`GET /memories/{id}`) and strategies (`GET /memories/{id}/long-term-memory-strategies`) to present a complete view.
5. For operations requiring `actorId`, `sessionId`, or `namespace`, ask the user for these values.
6. Show SDK examples by default. Show curl examples if user specifically asks or if working outside Python.
7. For framework integration (LangChain/LangGraph checkpointer, long-term memory tools): Quick start — for LangChain, use `AgentBaseMemoryEvents` as checkpointer via `create_agent(checkpointer=...)`. For LangGraph, use `builder.compile(checkpointer=...)`. For complete examples, **read `references/memory-ops.md`** for the integration section, and `references/langchain.md` / `references/langgraph.md` for complete examples. Do NOT provide integration code without reading these first.

---

# Troubleshooting (All Parts)

| Error | Cause | Fix |
|-------|-------|-----|
| 401 Unauthorized | Expired or invalid IAM token | Re-obtain token with valid credentials. Ensure `GREENNODE_CLIENT_ID` and `GREENNODE_CLIENT_SECRET` are set correctly (on AgentBase Runtime, these are auto-injected) |
| 403 Forbidden | Service account lacks permissions | Check IAM roles at https://iam.console.vngcloud.vn |
| 404 Not Found | Resource (provider, memory, identity) does not exist | Verify the name/ID with a `list` operation |
| 409 Conflict | Name already exists (identity or provider) | Choose a different name or update the existing resource |
| Name validation error | Name doesn't match `^[a-zA-Z0-9_-]+$` | Use only alphanumeric, underscore, and hyphen. 3-50 chars. |
| `.greennode.json` not found | Config file missing or wrong directory | Create `.greennode.json` with `client_id`, `client_secret` fields |
| Invalid apikey format | Key value rejected by validation | Check the key format matches the external service's requirements |
| Redirect URI mismatch (from OAuth2 provider) | Platform callback URL not whitelisted on external OAuth2 provider | Get `callbackUrl` from the provider API response (or `callback_url` in SDK) and add it as an authorized redirect URI in the external OAuth2 provider's settings (e.g., Google Cloud Console, GitHub OAuth App) |
| returnUrl rejected / not allowed | `returnUrl` not in agent identity's `allowedReturnUrls` | Update the agent identity via `/agentbase-manage identity update` to add the URL to `allowedReturnUrls` |
| Memory not found | Memory ID does not exist | Verify the memory ID exists with `GET /memories` |
| No records returned | Namespace mismatch or asynchronous processing | Check the namespace matches the strategy template. Records are generated asynchronously — wait a few seconds and retry |
| Events not appearing | Events expired or filtered out | Events expire after `eventExpiryDuration` days. Check the timestamp filters |
| Auto-generation not working | Strategy misconfigured | Verify `enableAutomaticMemoryRecordGeneration` is `true` on the strategy |
| "Missing required headers" error | Request missing `X-GreenNode-AgentBase-User-Id` or `X-GreenNode-AgentBase-Session-Id` | Include both headers in the request. Short-term memory requires `user_id` + `session_id`; long-term memory requires `user_id` (maps to `actor_id`) |

---

## Top-Level Instructions

1. Parse the user's arguments to determine the part (`identity`, `auth`, `memory`) and the operation.
2. If the part is unclear, ask the user which area they need:
   - **identity**: "I want to register/manage my agent's identity on the platform"
   - **auth**: "I want to store API keys, configure OAuth2, or manage credentials for external services"
   - **memory**: "I want to give my agent memory, persist conversations, or extract long-term facts"
3. If credentials are not configured, present the user with the two options (Auto create / I already have) as described in the Authentication section above.
4. Route to the appropriate part's instructions and operations.
5. Show SDK examples by default. Show curl examples if user specifically asks or if working outside Python.
