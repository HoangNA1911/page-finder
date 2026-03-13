---
name: agentbase-observe
description: Monitor, debug, and view logs for DEPLOYED (production) AI agents. View runtime logs, endpoint logs, and resource metrics (CPU/RAM). Use when user wants to check logs, view agent output, debug a running/deployed agent, troubleshoot production errors, see why a deployed agent is failing, check if the agent is running in production, monitor performance, view CPU/memory usage, or inspect what their deployed agent is doing. Also trigger when user says "show logs", "view logs", "check logs", "what's wrong with my agent", "agent crashed", "agent not working", "agent returning 500", "debug my deployed agent", "check if agent is running", "tail logs", "agent is slow", "why is it failing", or any debugging/monitoring scenario for an already-deployed agent. DO NOT use for managing runtime lifecycle (create/update/delete) — use /agentbase-runtime instead. DO NOT use for local testing or pre-deploy validation — use /agentbase-test instead.
argument-hint: <runtime-logs|endpoint-logs|metrics> [runtime-id] [endpoint-id]
user-invocable: true
---

# AgentBase Observability

Monitor and debug agents running on GreenNode AgentBase Runtime.

- **Base URL**: `https://agentbase.api.vngcloud.vn/runtime`
- **Console**: https://aiplatform.console.vngcloud.vn/runtime

## Authentication & Endpoints

Read the shared auth setup reference at `/agentbase` skill's `references/auth-setup.md` for full IAM credential configuration. In brief: check for `GREENNODE_CLIENT_ID` and `GREENNODE_CLIENT_SECRET` in environment variables or `.greennode.json` in the **current working directory only** (do NOT search recursively or look outside the current directory), then use `TOKEN=$(bash .claude/skills/agentbase/scripts/get_token.sh)` to obtain a token. On 401: re-run with `--force`.

**IMPORTANT:** Before constructing any API URL, read `/agentbase` skill's `references/endpoints.md` for the domain validation whitelist. Only use domains listed there.

---

## Interaction Guidelines

- **Guide first, act only when asked** — if the user asks "how to" view logs or metrics, respond with instructions and guidance only. Do NOT execute API calls unless they explicitly ask you to do it for them.
- **Read-only operations proceed directly** — for log and metric queries (runtime-logs, endpoint-logs, metrics), proceed directly once you have the required IDs. Ask the user to clarify only if the runtime ID or endpoint ID is ambiguous (e.g., multiple runtimes exist and the user hasn't specified which one).
- **Never auto-decide parameters** — when an action requires parameters (e.g., runtime ID, endpoint ID, log offset, limit), always ask the user for each required value. You may recommend sensible defaults (e.g., limit=100), but never auto-select or impose values without the user's explicit agreement.
- **Present options, let user choose** — when there are multiple runtimes or endpoints to choose from, list them and let the user pick. Do not make the choice for them.
- **Always read full API response body** — when calling platform APIs, capture and read the full JSON response (not just status codes). This avoids misidentifying field names or data structures, ensures correct field extraction, and enables better error handling and debugging.

## Operations

### runtime-logs [id] -- View runtime logs

Fetch logs from an agent runtime container.

**API**: `POST /agent-runtimes/{id}/logs`

**Body** (`LogSearchRequest`):
- `from` (int, max 5000) -- starting offset (0-based)
- `limit` (int, recommended max 500) -- number of log lines to return
- `fromTimestamp` (string, optional) -- start of time range filter (ISO 8601)
- `toTimestamp` (string, optional) -- end of time range filter (ISO 8601)
- `query` (string, optional) -- keyword search filter
- `order` (string, optional) -- log ordering

**Response** (`LogSearchResult`): `totalCount` (int), `logs` (array of `LogRecord` with `timestamp` (string) and `content` (string)).

> **Note**: Runtime Service pagination is **1-indexed** (first page = `page=1`).

**curl**:
```bash
curl -X POST "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID/logs" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "from": 0,
    "limit": 100
  }'

# With time range and keyword search
curl -X POST "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID/logs" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "from": 0,
    "limit": 100,
    "fromTimestamp": "2026-03-13T00:00:00Z",
    "toTimestamp": "2026-03-13T12:00:00Z",
    "query": "error"
  }'
```

*SDK: No dedicated SDK method for logs. Use curl.*

**Tips**:
- Use `from` to paginate through large log sets (e.g. `"from": 100` to skip first 100 entries)
- Recommended max `limit` is 500, max `from` is 5000
- Use `query` to filter logs by keyword server-side (e.g. `"query": "error"`)
- Use `fromTimestamp`/`toTimestamp` to narrow logs to a specific time window
- Each log entry has `timestamp` and `content` fields

---

### endpoint-logs [id] [endpointId] -- View endpoint logs

Fetch logs from a specific endpoint within a runtime.

**API**: `POST /agent-runtimes/{id}/endpoints/{endpointId}/logs`

**Body**: Same as runtime-logs (`from`, `limit`, `fromTimestamp`, `toTimestamp`, `query`, `order`).

**curl**:
```bash
curl -X POST "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID/endpoints/$ENDPOINT_ID/logs" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "from": 0,
    "limit": 100
  }'
```

*SDK: No dedicated SDK method for endpoint logs. Use curl.*

---

### metrics [id] [endpointId] -- View endpoint resource metrics

Get CPU and RAM usage metrics for a specific endpoint. Supports historical time range queries.

**API**: `GET /agent-runtimes/{id}/endpoints/{endpointId}/metrics`

**Query parameters**:
- `fromTimestamp` (string, optional) -- start of time range (ISO 8601)
- `toTimestamp` (string, optional) -- end of time range (ISO 8601)

**curl**:
```bash
# Current metrics
curl -s "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID/endpoints/$ENDPOINT_ID/metrics" \
  -H "Authorization: Bearer $TOKEN"

# Historical metrics with time range
curl -s "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID/endpoints/$ENDPOINT_ID/metrics?fromTimestamp=2026-03-13T00:00:00Z&toTimestamp=2026-03-13T12:00:00Z" \
  -H "Authorization: Bearer $TOKEN"
```

*SDK: No dedicated SDK method for metrics. Use curl.*

**Response** (`AgentRuntimeEndpointMetrics`):
- `cpuCoresUsage` -- array of `{timestamp (date-time), value (double)}` data points
- `memoryBytesUsage` -- array of `{timestamp (date-time), value (int64)}` data points

---

## Current Limitations

| Feature | Status |
|---------|--------|
| Log filtering by level (INFO/WARN/ERROR) | Not supported — all log levels are returned together |
| Log time range filter | Supported — use `fromTimestamp`/`toTimestamp` in request body |
| Log keyword search | Supported — use `query` field in request body |
| Historical metrics | Supported — use `fromTimestamp`/`toTimestamp` query params |
| Log streaming/tailing | Not supported — use polling as a workaround (see below) |
| Alerting/thresholds | Not supported |

**Pseudo-tailing pattern**: To approximate log tailing, poll the logs endpoint every 5-10 seconds with an increasing `from` offset. Note: frequent polling generates many API calls — be mindful of rate limits and avoid polling for extended periods:
```bash
OFFSET=0
while true; do
  RESULT=$(curl -s -X POST "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID/logs" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d "{\"from\": $OFFSET, \"limit\": 50}")
  COUNT=$(echo "$RESULT" | jq '.totalCount')
  echo "$RESULT" | jq -r '.logs[].content'
  OFFSET=$COUNT
  sleep 5
done
```

---

## Log Analysis Guide

### Common Error Signatures

When reviewing logs, look for these patterns:

| Pattern | Meaning | Next Step |
|---------|---------|-----------|
| `Traceback (most recent call last)` | Python exception — read the last line for the actual error | Check the exception type and message at the bottom of the traceback |
| `ModuleNotFoundError: No module named '...'` | Missing dependency | Add the module to `requirements.txt` and rebuild |
| `ImportError: cannot import name '...'` | Wrong package version or API change | Check package version compatibility |
| `ConnectionRefusedError` / `ConnectionError` | Cannot reach external service | Verify the service URL, check if auth credentials are injected correctly |
| `401 Unauthorized` / `403 Forbidden` | Authentication/authorization failure | Check IAM token, service account permissions, or external API key |
| `OSError: [Errno 98] Address already in use` | Port conflict (usually 8080) | Ensure only one process binds to port 8080 |
| `MemoryError` / `Killed` | Out of memory | Scale up flavor or optimize memory usage |
| `TimeoutError` / `ReadTimeout` | External API or LLM call timed out | Increase timeout, check LLM endpoint health |
| `KeyError: '...'` | Missing expected field in payload/response | Check payload format matches what handler expects |
| `Health check failed` | `/health` endpoint not returning 200 | Verify `@app.ping` is defined and returns `PingStatus.HEALTHY` |

### Debugging Decision Tree

Use this flow to diagnose common issues:

```
Agent not responding?
├─ Check runtime status (/agentbase-runtime get)
│  ├─ Status = FAILED → Check runtime logs for startup errors
│  ├─ Status = CREATING → Wait, then re-check
│  └─ Status = ACTIVE → Check endpoint logs
│     ├─ Logs show Python traceback → Fix the code error
│     ├─ Logs show "Health check failed" → Fix health endpoint
│     ├─ No recent logs → Container may have crashed silently, check metrics
│     └─ Logs look normal → Issue may be in request routing, check endpoint URL

Agent returns errors (4xx/5xx)?
├─ 500 Internal Server Error → Check endpoint logs for traceback
├─ 502 Bad Gateway → Container crashed or not ready, check runtime logs
├─ 503 Service Unavailable → Container starting up or overloaded, check metrics
└─ 401/403 → Check if agent's outbound auth is configured (/agentbase-auth)

Agent is slow?
├─ Check metrics for CPU/RAM
│  ├─ CPU near limit → CPU-bound (e.g., stuck loop, heavy computation)
│  │  └─ Scale up flavor or optimize code
│  ├─ RAM near limit → Memory-bound (e.g., large model in memory, data leak)
│  │  └─ Scale up flavor or fix memory leak
│  └─ Both low → Bottleneck is external (LLM API, database, network)
│     └─ Check logs for slow external calls, add request timing
```

### Correlating Logs with Metrics

- **High CPU + normal RAM** → CPU-bound workload (tight loops, heavy computation, synchronous LLM calls)
- **High RAM + normal CPU** → Memory leak or large data structures (loading entire datasets, caching without limits)
- **Both high** → Resource exhaustion — scale up the flavor or optimize both code paths
- **Both low + slow responses** → External dependency bottleneck (LLM API latency, database queries, network timeouts)

### Log Filtering

Use server-side filtering when possible, and client-side techniques for finer control:

```bash
# Server-side: keyword search via query field
curl -X POST "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID/logs" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"from": 0, "limit": 100, "query": "error"}'

# Server-side: time range filter
curl -X POST "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID/logs" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"from": 0, "limit": 100, "fromTimestamp": "2026-03-13T00:00:00Z", "toTimestamp": "2026-03-13T12:00:00Z"}'

# Client-side: filter fetched results locally
echo "$LOGS" | jq -r '.logs[].content' | grep -i "error\|traceback\|exception\|failed"

# Client-side: show only the last N lines
echo "$LOGS" | jq -r '.logs[].content' | tail -20

# Client-side: count errors
echo "$LOGS" | jq -r '.logs[].content' | grep -ci "error"
```

## Troubleshooting Guide

| Error | Cause | Fix |
|-------|-------|-----|
| Agent not responding | Runtime crashed or not started | Check runtime status (`/agentbase-runtime get`), then check runtime logs for crash messages |
| 502/503 errors on endpoint | Container startup failure | Check endpoint logs for startup failures, verify health endpoint returns 200 |
| High latency | Resource saturation | Check metrics for CPU/RAM saturation, consider scaling up flavor or replicas |
| OOM kills | Memory spikes exceeding limit | Check metrics for memory spikes, increase flavor size |
| Image pull errors | Wrong URL or missing credentials | Verify `imageUrl` and registry credentials in runtime config |
| Container crash loop | Code error or missing dependencies | Check runtime logs for Python tracebacks or missing dependencies |

## Instructions

1. Parse the user's argument to determine the operation (`runtime-logs`, `endpoint-logs`, `metrics`).
2. If a runtime ID is needed and not provided, list runtimes first (`/agentbase-runtime list`) and ask the user to pick one.
3. If an endpoint ID is needed, list endpoints for the runtime and ask the user to pick one.
4. For logs, default to `{"from": 0, "limit": 100}` to fetch the most recent entries. Use `from` to paginate if more logs are needed (max `from`: 5000, recommended max `limit`: 500). Use `query` for keyword filtering and `fromTimestamp`/`toTimestamp` for time range filtering when the user specifies these.
5. Present log output in a readable format, highlighting errors and warnings. Each log entry has `timestamp` and `content` fields.
6. For metrics, display CPU (`cpuCoresUsage`) and RAM (`memoryBytesUsage`, convert values to MB/GB) as time-series data points. Use `fromTimestamp`/`toTimestamp` query params for historical ranges. To show usage as percentages, cross-reference the runtime's flavor via `/agentbase-runtime get` to obtain the flavor's CPU/RAM limits.
