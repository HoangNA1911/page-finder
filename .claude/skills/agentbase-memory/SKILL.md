---
name: agentbase-memory
description: Add memory and conversation persistence to AI agents. Use when user wants to give their agent memory, persist conversation history, remember things across sessions, create memory stores, store and retrieve context between conversations, add long-term memory, extract facts from conversations via semantic search, or integrate LangChain/LangGraph checkpointer with memory service. Also trigger when user says "agent needs memory", "remember conversations", "conversation history", "persist state", "store conversations", "remember across sessions", "add memory to my agent", "long-term memory", "my agent should remember", "context persistence", "create memory", "search memories", "fact extraction", or wants their agent to retain context between interactions. DO NOT use for runtime logs (use /agentbase-observe) or agent registration (use /agentbase-identity).
argument-hint: <create|list|get|delete|events|records|search|generate|integrate> [memory-id]
user-invocable: true
---

# AgentBase Memory Service

The Memory Service provides conversation history (short-term events) and semantic fact extraction (long-term memory records) for AI agents.

- **Base URL**: `https://agentbase.api.vngcloud.vn/memory`
- **Console**: https://aiplatform.console.vngcloud.vn/memory

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
- `CUSTOM` - Custom fact extraction with a user-defined prompt (`customFactExtractionPrompt`). **When using `customFactExtractionPrompt`, the type MUST be `CUSTOM`** — using `SEMANTIC` or `USER_PREFERENCE` with a custom prompt is not valid.

### Namespace Template

Controls how memory records are partitioned. Default: `/strategies/{memoryStrategyId}/actors/{actorId}`

Available variables: `{memoryStrategyId}`, `{actorId}`, `{sessionId}`

> **Note on `actorId`**: The `actorId` represents the **end-user** (the person interacting with the agent), not the agent itself. Use any string that uniquely identifies the user (e.g. a user ID like `alice`, `user-123`). This allows the memory system to partition and recall facts per user. Do not confuse `actorId` with the agent's identity — for agent identity management, see `/agentbase-identity`.

## Authentication & Endpoints

Read the shared auth setup reference at `/agentbase` skill's `references/auth-setup.md` for full IAM credential configuration. In brief: check for `GREENNODE_CLIENT_ID` and `GREENNODE_CLIENT_SECRET` in environment variables or `.greennode.json` in the **current working directory only** (do NOT search recursively or look outside the current directory), then use `TOKEN=$(bash .claude/skills/agentbase/scripts/get_token.sh)` to obtain a token. On 401: re-run with `--force`.

**IMPORTANT:** Before constructing any API URL, read `/agentbase` skill's `references/endpoints.md` for the domain validation whitelist. Only use domains listed there.

---

## Interaction Guidelines

- **Guide first, act only when asked** — if the user asks "how to" create/manage memory or events, respond with instructions and guidance only. Do NOT execute API calls or create resources unless they explicitly ask you to do it for them.
- **Confirm before executing (HARD GATE)** — before performing any action (create, delete, generate, search), present a clear summary of what will be done (including all parameters and values) and ask the user to confirm. Do NOT auto-execute. Only proceed when the user responds with an explicit confirmation keyword: `yes`, `confirm`, `ok`, `approve`, `proceed`, `go ahead`, `do it`, `ship it`, `lgtm`, or equivalent affirmative. If the user responds with ANYTHING ELSE (parameter changes, questions, corrections, additional info, or ambiguous text), treat it as adjustment input — update the plan and re-present the full summary for confirmation again. NEVER interpret a non-confirmation response as approval. For destructive operations (delete memory, delete event, delete memory record), additionally warn that the action is irreversible.
- **Never auto-decide parameters** — when an action requires parameters (e.g., memory name, strategy type, event expiry, namespace, actorId, sessionId), always ask the user for each required value. You may recommend sensible defaults or examples, but never auto-select or impose values without the user's explicit agreement.
- **Present options, let user choose** — when there are multiple choices (e.g., strategy types SEMANTIC/USER_PREFERENCE, operations), list the available options and let the user pick. Do not make the choice for them.
- **Dry-run support**: When user requests `--dry-run` or preview, show the exact API request (method, URL, headers, payload) and explain the expected outcome WITHOUT executing. Let user review before proceeding.

## Operations

### 1. create - Create a New Memory

Creates a memory container with long-term memory strategies.

**API:** `POST /memories`

**Required fields**:
- `name` (string, 0-50 chars, pattern `^[a-zA-Z0-9._-]*$`)
- `description` (string)
- `eventExpiryDuration` (int, 1-365 days)
- `longTermMemoryStrategies` (array of strategy objects, each with):
  - `name` (string, min 1 char)
  - `type` (string, min 1 char) -- `SEMANTIC`, `USER_PREFERENCE`, or `CUSTOM`
  - `namespaceTemplate` (string, 0-50 chars, pattern `^[a-zA-Z0-9{}/._-]*$`)
  - `enableAutomaticMemoryRecordGeneration` (bool)
  - `customFactExtractionPrompt` (string, optional) -- custom prompt for fact extraction. **Requires `type: "CUSTOM"`**

> **Note**: The `name` field is required by the v3 API but may not be present in the SDK's `LongTermMemoryStrategy` model. When using the SDK, pass `name` as an extra keyword argument or use curl for full API field support.

**curl:**
```bash
curl -X POST "https://agentbase.api.vngcloud.vn/memory/memories" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "my-memory", "description": "Agent memory", "eventExpiryDuration": 30,
    "longTermMemoryStrategies": [{"name": "semantic-facts", "type": "SEMANTIC",
      "namespaceTemplate": "/strategies/{memoryStrategyId}/actors/{actorId}",
      "enableAutomaticMemoryRecordGeneration": true}]}'
```

**SDK:**
```python
from greennode_agentbase.memory.models import MemoryCreateRequest, LongTermMemoryStrategy

request = MemoryCreateRequest(
    name="my-memory", description="Agent memory", eventExpiryDuration=30,
    longTermMemoryStrategies=[
        LongTermMemoryStrategy(name="semantic-facts", type="SEMANTIC",
            namespaceTemplate="/strategies/{memoryStrategyId}/actors/{actorId}",
            enableAutomaticMemoryRecordGeneration=True),
    ],
)
memory = await client.create_async(request=request)
```

Strategy types: `SEMANTIC` (general facts), `USER_PREFERENCE` (user habits), `CUSTOM` (custom extraction with `customFactExtractionPrompt`). Add multiple strategies by repeating in the array. **If user provides `customFactExtractionPrompt`, always set `type` to `CUSTOM`.**

---

### 2. list - List All Memories

**API:** `GET /memories?page=1&size=10`

**Note**: Memory Service uses 1-indexed pagination (page=1 is first page).

**curl:**
```bash
curl "https://agentbase.api.vngcloud.vn/memory/memories?page=1&size=10" \
  -H "Authorization: Bearer $TOKEN"
```

**SDK:**
```python
result = await client.list_async(page=1, size=10)
for memory in result.list_data:
    print(f"{memory.id}: {memory.name} ({memory.status})")
```

---

### 3. get - Get Memory Details

Fetches memory info AND its long-term memory strategies in a single view. **Always call both APIs** to give the user the complete configuration they set during creation.

**APIs:**
1. `GET /memories/{id}` — basic info (name, description, eventExpiryDuration, status)
2. `GET /memories/{id}/long-term-memory-strategies` — strategies configured for this memory

**curl:**
```bash
# Step 1: Get memory basic info
curl "https://agentbase.api.vngcloud.vn/memory/memories/mem_abc123" \
  -H "Authorization: Bearer $TOKEN"

# Step 2: Get long-term memory strategies
curl "https://agentbase.api.vngcloud.vn/memory/memories/mem_abc123/long-term-memory-strategies" \
  -H "Authorization: Bearer $TOKEN"
```

**SDK:**
```python
import asyncio
from greennode_agentbase.memory import MemoryClient

client = MemoryClient()

# Fetch both in parallel for efficiency
memory, strategies = await asyncio.gather(
    client.get_async(id="mem_abc123"),
    client.listLongTermMemoryStrategies_async(id="mem_abc123"),
)

# Display complete memory detail
print(f"Name: {memory.name}")
print(f"Description: {memory.description}")
print(f"Status: {memory.status}")
print(f"Event expiry: {memory.event_expiry_duration} days")
print(f"Created: {memory.created_at}")
print(f"\nLong-Term Memory Strategies ({len(strategies)} configured):")
for s in strategies:
    print(f"  - ID: {s['id']}, Name: {s.get('name')}, Type: {s['type']}")
    print(f"    Namespace: {s.get('namespaceTemplate')}")
    print(f"    Auto-generate: {s.get('enableAutomaticMemoryRecordGeneration')}")
    if s.get('customFactExtractionPrompt'):
        print(f"    Custom prompt: {s['customFactExtractionPrompt']}")
```

**IMPORTANT:** When the user asks to "get", "show", "detail", or "inspect" a memory, ALWAYS present both the basic info and the strategies together. Do NOT show only the basic info without strategies — that gives an incomplete picture compared to what was configured at creation time.

---

### 4. delete - Delete a Memory

**Before deleting**: Consider exporting or noting the resource configuration, as deletion is irreversible. There is no undo.

**API:** `DELETE /memories/{id}`

**curl:**
```bash
curl -X DELETE "https://agentbase.api.vngcloud.vn/memory/memories/mem_abc123" \
  -H "Authorization: Bearer $TOKEN"
```

**SDK:**
```python
await client.delete_async(id="mem_abc123")
```

---

### 5. events - Manage Conversation Events

Events are individual conversation turns (user message, assistant response) stored in a memory.

#### List Events

**API:** `GET /memories/{memoryId}/actors/{actorId}/sessions/{sessionId}/events?page=1&size=10`

Optional query params: `fromTimestamp`, `toTimestamp`

> **Note:** Results are sorted by **descending** order (newest first) by default. Keep this in mind when processing sequential conversation data — you may need to reverse the list to get chronological order.

**curl:**
```bash
curl "https://agentbase.api.vngcloud.vn/memory/memories/mem_abc123/actors/user-1/sessions/session-1/events?page=1&size=20" \
  -H "Authorization: Bearer $TOKEN"
```

**SDK:** See `references/advanced-operations.md` for SDK examples.

#### Create Event

**API:** `POST /memories/{memoryId}/actors/{actorId}/sessions/{sessionId}/events`

**curl:**
```bash
curl -X POST "https://agentbase.api.vngcloud.vn/memory/memories/mem_abc123/actors/user-1/sessions/session-1/events" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "payload": {
      "type": "CONVERSATIONAL",
      "role": "user",
      "message": "What is the weather in Saigon?"
    }
  }'
```

**SDK:** See `references/advanced-operations.md` for SDK examples.

#### List Actors

**API:** `GET /memories/{memoryId}/actors?page=1&size=10`

**curl:**
```bash
curl "https://agentbase.api.vngcloud.vn/memory/memories/mem_abc123/actors?page=1&size=10" \
  -H "Authorization: Bearer $TOKEN"
```

**SDK:** See `references/advanced-operations.md` for SDK examples.

For additional event operations (list sessions, delete event), see `references/advanced-operations.md`.

---

### 6. records - Browse Memory Records

Memory records are distilled long-term facts extracted from conversation events.

**API:** `GET /memories/{memoryId}/memory-records?namespace=/strategies/{strategyId}/actors/{actorId}&limit=100`

**curl:**
```bash
curl "https://agentbase.api.vngcloud.vn/memory/memories/mem_abc123/memory-records?namespace=%2Fstrategies%2Fstrat_1%2Factors%2Fuser-1&limit=100" \
  -H "Authorization: Bearer $TOKEN"
```

**SDK:** See `references/advanced-operations.md` for SDK examples.

---

### 7. search - Semantic Search Memory Records

Search memory records using natural language queries. The service performs vector similarity search.

**API:** `POST /memories/{memoryId}/memory-records:search?namespace=...`

**Request body**:
- `query` (string, required, min 1 char) -- natural language search query
- `limit` (int, optional, 5-200) -- max results to return
- `scoreThreshold` (float, optional, 0-1) -- minimum similarity score

**curl:**
```bash
curl -X POST "https://agentbase.api.vngcloud.vn/memory/memories/mem_abc123/memory-records:search?namespace=%2Fstrategies%2Fstrat_1%2Factors%2Fuser-1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "user preferences about coffee",
    "limit": 10,
    "scoreThreshold": 0.5
  }'
```

**SDK:**
```python
from greennode_agentbase.memory import MemoryClient
from greennode_agentbase.memory.models import MemoryRecordSearchRequest

client = MemoryClient()

import asyncio
results = asyncio.run(
    client.searchMemoryRecords_async(
        id="mem_abc123",
        namespace="/strategies/strat_1/actors/user-1",
        request=MemoryRecordSearchRequest(query="user preferences about coffee", limit=10),
    )
)
for record in results:
    print(f"[{record.score:.2f}] {record.memory}")
```

---

### 8. generate - Generate Memory Records

Generate long-term memory records from conversation data using a configured strategy.

#### From Session (existing events)

**API:** `POST /memories/{memoryId}/memory-records:generate-from-session?actorId=...&sessionId=...&longTermMemoryStrategyId=...`

**curl:**
```bash
curl -X POST "https://agentbase.api.vngcloud.vn/memory/memories/mem_abc123/memory-records:generate-from-session?actorId=user-1&sessionId=session-1&longTermMemoryStrategyId=strat_1" \
  -H "Authorization: Bearer $TOKEN"
```

**SDK:**
```python
await client.generateMemoryRecordsFromSession_async(
    id="mem_abc123",
    actorId="user-1",
    sessionId="session-1",
    longTermMemoryStrategyId="strat_1",
)
```

For additional generation methods (from content, insert directly) and record deletion, see `references/advanced-operations.md`.

---

### 9. integrate - Framework Integration

#### Required Request Headers

When an agent uses AgentBase Memory, the following request headers are **required** and must be validated in the handler:

| Header | Maps to | Required for |
|--------|---------|-------------|
| `X-GreenNode-AgentBase-User-Id` | `context.user_id` → `actor_id` | Short-term memory (checkpointer) AND long-term memory (tool-based) |
| `X-GreenNode-AgentBase-Session-Id` | `context.session_id` → `thread_id` | Short-term memory (checkpointer) |

**The handler MUST return an error if these headers are missing** — do NOT fall back to default values like `"default-user"` or `"default-session"`. Silent defaults cause data mixing between users/sessions and are a source of hard-to-debug issues.

```python
@app.entrypoint
def handler(payload: dict, context: RequestContext) -> dict:
    # Validate required headers for memory integration
    if not context.user_id or not context.session_id:
        return {
            "status": "error",
            "error": "Missing required headers: X-GreenNode-AgentBase-User-Id and X-GreenNode-AgentBase-Session-Id are required when using memory.",
        }
    # ... proceed with agent invocation
```

#### Short-Term Memory (Conversation Persistence)

Short-term memory uses **checkpointing** via the `greennode-agent-bridge` package. This persists LangGraph state (conversation history) as events in AgentBase Memory.

```bash
pip install "greennode-agent-bridge[langgraph]"
```

**LangChain** (`create_agent` accepts `checkpointer`):
```python
from greennode_agent_bridge import AgentBaseMemoryEvents

checkpointer = AgentBaseMemoryEvents(memory_id="mem_abc123")
agent = create_agent(llm, tools=[...], checkpointer=checkpointer)
```

**LangGraph**:
```python
from greennode_agent_bridge import AgentBaseMemoryEvents

checkpointer = AgentBaseMemoryEvents(memory_id="mem_abc123")
graph = builder.compile(checkpointer=checkpointer)
```

#### Long-Term Memory (Semantic Facts)

Long-term memory uses a **tool-based approach with MemoryClient SDK**. This approach is more stable than using the SDK's store adaptor and gives full control over memory record operations.

**Important — `actor_id` and `strategy_id` management:**
- `actor_id` — **MUST** be retrieved from `langgraph.config.get_config()["configurable"]["actor_id"]` at runtime (set via `configurable` in `graph.invoke`). **Do NOT expose as a tool parameter** — the LLM should not decide which user's memory to access.
- `strategy_id` — **MUST** be a fixed app-level config (e.g. `MEMORY_STRATEGY_ID` env var). **Do NOT expose as a tool parameter** — it's a deployment-time setting, not a per-call decision.

See the reference files for complete integration examples:
- **LangChain**: Read `references/langchain.md` for `@tool` functions that call the Memory API directly (remember, recall) and a full agent example with checkpointer.
- **LangGraph**: Read `references/langgraph.md` for checkpointer + tool-based long-term memory integration.

---

## Long-Term Memory Strategies

Strategies are automatically shown when getting memory details (see Operation 3 above). To list strategies independently, use:

**API:** `GET /memories/{memoryId}/long-term-memory-strategies`

See `references/advanced-operations.md` for curl and SDK examples.

---

## Common Workflows

1. **Auto-generation**: Create memory with `enableAutomaticMemoryRecordGeneration: true` → log events → records generated automatically
2. **Manual generation**: Create memory → log events → call `generate-from-session` or `generate-from-content` → search records
3. **Direct insertion**: Create memory → use `insert-directly` to add facts → search records

---

## Important: URL Encoding

When calling APIs with query parameters that contain special characters (e.g. namespace paths like `/strategies/{strategyId}/actors/{actorId}`), always **URL-encode** the values to avoid errors. For example:

```bash
# Correct — URL-encoded namespace
curl "https://agentbase.api.vngcloud.vn/memory/memories/mem_abc123/memory-records?namespace=%2Fstrategies%2Fstrat_1%2Factors%2Fuser-1&limit=100" \
  -H "Authorization: Bearer $TOKEN"
```

In Python, use `urllib.parse.quote` or let the SDK handle encoding automatically.

---

## Runtime Auto-Injection

When an agent is deployed on AgentBase Runtime, the IAM service account and Agent Identity are managed by the runtime system and automatically injected into the container as `GREENNODE_CLIENT_ID`, `GREENNODE_CLIENT_SECRET`, and `GREENNODE_AGENT_IDENTITY`. The SDK automatically uses these — memory operations and LangGraph bridge integrations work without any manual credential configuration in agent code. See `/agentbase-runtime` for details on runtime environment management.

The IAM credentials in this skill's Authentication section are for **local development** and **platform management** (creating/managing memories from outside the runtime).

## Multi-Memory Pattern

For using multiple memory stores simultaneously (separate stores for conversation history, domain knowledge, user preferences), see `references/multi-memory.md`.

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| 401 Unauthorized | Expired or invalid IAM token | Check IAM credentials. Ensure `GREENNODE_CLIENT_ID` and `GREENNODE_CLIENT_SECRET` are set correctly (on AgentBase Runtime, these are auto-injected) |
| Memory not found | Memory ID does not exist | Verify the memory ID exists with `GET /memories` |
| No records returned | Namespace mismatch or async delay | Check the namespace matches the strategy template. Records are generated asynchronously |
| Events not appearing | Events expired or filtered out | Events expire after `eventExpiryDuration` days. Check the timestamp filters |
| Auto-generation not working | Strategy misconfigured | Verify `enableAutomaticMemoryRecordGeneration` is `true` on the strategy |
| "Missing required headers" error | Request missing `X-GreenNode-AgentBase-User-Id` or `X-GreenNode-AgentBase-Session-Id` | Include both headers in the request. Short-term memory requires `user_id` + `session_id`; long-term memory requires `user_id` (maps to `actor_id`) |
