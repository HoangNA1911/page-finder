# Advanced Memory Operations

## Generate Memory Records from Content (ad-hoc messages)

**API:** `POST /memories/{memoryId}/memory-records:generate-from-content?longTermMemoryStrategyId=...&actorId=...&sessionId=...`

**curl:**
```bash
curl -X POST "https://agentbase.api.vngcloud.vn/memory/memories/mem_abc123/memory-records:generate-from-content?longTermMemoryStrategyId=strat_1&actorId=user-1&sessionId=session-1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "chatMessages": [
      {"role": "user", "content": "I always drink iced coffee in the morning"},
      {"role": "assistant", "content": "Noted! You prefer iced coffee for your morning routine."}
    ]
  }'
```

**Python (SDK):**
```python
import asyncio
from greennode_agentbase.memory import MemoryClient
from greennode_agentbase.memory.models import ChatMessage

client = MemoryClient()

result = asyncio.run(
    client.generateMemoryRecordsFromContent_async(
        id="mem_abc123",
        longTermMemoryStrategyId="strat_1",
        actorId="user-1",
        sessionId="session-1",
        request=[
            ChatMessage(role="user", content="I always drink iced coffee in the morning"),
            ChatMessage(role="assistant", content="Noted! You prefer iced coffee for your morning routine."),
        ],
    )
)
```

---

## Insert Memory Records Directly (manual facts)

**API:** `POST /memories/{memoryId}/memory-records:insert-directly?namespace=...`

**curl:**
```bash
curl -X POST "https://agentbase.api.vngcloud.vn/memory/memories/mem_abc123/memory-records:insert-directly?namespace=%2Fstrategies%2Fstrat_1%2Factors%2Fuser-1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "memoryRecords": [
      "User prefers Vietnamese coffee",
      "User is based in Ho Chi Minh City",
      "User works in software engineering"
    ]
  }'
```

**Python (SDK):**
```python
import asyncio
from greennode_agentbase.memory import MemoryClient

client = MemoryClient()

result = asyncio.run(
    client.insertMemoryRecordsDirectly_async(
        id="mem_abc123",
        namespace="/strategies/strat_1/actors/user-1",
        request=[
            "User prefers Vietnamese coffee",
            "User is based in Ho Chi Minh City",
        ],
    )
)
```

---

## Delete a Memory Record

**API:** `DELETE /memories/{memoryId}/memory-records/{memoryRecordId}`

```bash
curl -X DELETE "https://agentbase.api.vngcloud.vn/memory/memories/mem_abc123/memory-records/rec_789" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Delete an Event

**API:** `DELETE /memories/{memoryId}/actors/{actorId}/sessions/{sessionId}/events/{eventId}`

```bash
curl -X DELETE "https://agentbase.api.vngcloud.vn/memory/memories/mem_abc123/actors/user-1/sessions/session-1/events/evt_456" \
  -H "Authorization: Bearer $TOKEN"
```

---

## List Actors

**API:** `GET /memories/{memoryId}/actors?page=1&size=10`

```bash
curl "https://agentbase.api.vngcloud.vn/memory/memories/mem_abc123/actors?page=1&size=10" \
  -H "Authorization: Bearer $TOKEN"
```

**Python (SDK):** No direct method available. Use curl above.

---

## List Sessions for an Actor

**API:** `GET /memories/{memoryId}/actors/{actorId}/sessions?page=1&size=10`

```bash
curl "https://agentbase.api.vngcloud.vn/memory/memories/mem_abc123/actors/user-1/sessions?page=1&size=10" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Long-Term Memory Strategies

List strategies configured for a memory:

**API:** `GET /memories/{memoryId}/long-term-memory-strategies`

**curl:**
```bash
curl "https://agentbase.api.vngcloud.vn/memory/memories/mem_abc123/long-term-memory-strategies" \
  -H "Authorization: Bearer $TOKEN"
```

**Python (SDK):**
```python
import asyncio
from greennode_agentbase.memory import MemoryClient

client = MemoryClient()

result = asyncio.run(
    client.listLongTermMemoryStrategies_async(id="mem_abc123")
)
for s in result:
    print(f"ID: {s['id']}, Type: {s['type']}, Template: {s.get('namespaceTemplate')}")
```
