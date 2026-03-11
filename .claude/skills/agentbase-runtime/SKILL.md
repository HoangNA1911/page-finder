---
name: agentbase-runtime
description: Manage GreenNode AgentBase agent runtimes (CRUD operations). Use when user wants to create a runtime from an existing image, list, inspect, update, or delete existing runtimes, manage endpoints and versions, set up canary deployments, check deployment status, configure autoscaling, scale up/down, change compute flavor, resize agent resources, or list available flavors. Also trigger when user says "list my runtimes", "check runtime status", "delete runtime", "update endpoint", "add canary", "what flavors are available", or wants to manage an already-deployed agent's infrastructure without rebuilding. DO NOT use for the full build-push-deploy workflow (use /agentbase-deploy) or for viewing logs and metrics (use /agentbase-observe).
argument-hint: <create|list|get|update|delete|endpoints|versions|status> [id-or-name]
user-invocable: true
---

# AgentBase Runtime Management

Manage agent runtimes on GreenNode AgentBase Runtime Service.

- **Base URL**: `https://agentbase.api.vngcloud.vn/runtime`
- **Console**: https://aiplatform.console.vngcloud.vn/runtime

## Authentication & Endpoints

Read the shared auth setup reference at `/agentbase` skill's `references/auth-setup.md` for full IAM credential configuration. In brief: check for `GREENNODE_CLIENT_ID` and `GREENNODE_CLIENT_SECRET` in environment variables or `.greennode.json` in the **current working directory only** (do NOT search recursively or look outside the current directory), then use `TOKEN=$(bash .claude/skills/agentbase/scripts/get_token.sh)` to obtain a token. On 401: re-run with `--force`.

**IMPORTANT:** Before constructing any API URL, read `/agentbase` skill's `references/endpoints.md` for the domain validation whitelist. Only use domains listed there.

---

## Interaction Guidelines

- **Guide first, act only when asked** — if the user asks "how to" create/update/manage a runtime, respond with instructions and guidance only. Do NOT execute API calls or create resources unless they explicitly ask you to do it for them.
- **Confirm before executing (HARD GATE)** — before performing any action (create, update, delete, manage endpoints/versions), present a clear summary of what will be done (including all parameters and values) and ask the user to confirm. Do NOT auto-execute. Only proceed when the user responds with an explicit confirmation keyword: `yes`, `confirm`, `ok`, `approve`, `proceed`, `go ahead`, `do it`, `ship it`, `lgtm`, or equivalent affirmative. If the user responds with ANYTHING ELSE (parameter changes, questions, corrections, additional info, or ambiguous text), treat it as adjustment input — update the plan and re-present the full summary for confirmation again. NEVER interpret a non-confirmation response as approval. For destructive operations (delete runtime, delete endpoint), additionally warn that the action is irreversible.
- **Never auto-decide parameters** — when an action requires parameters (e.g., runtime name, image URL, flavor, autoscaling settings, environment variables), always ask the user for each required value. You may recommend sensible defaults or options, but never auto-select or impose values without the user's explicit agreement.
- **Present options, let user choose** — when there are multiple choices (e.g., compute flavors, runtimes, endpoints, versions), list the available options and let the user pick. Do not make the choice for them.
- **When the user configures an LLM model** (e.g. via environment variables or agent config), use `/aip` skill to list available models and **let the user choose**. When listing, prioritize showing models with `modelStatus = ENABLED` and sort by most recent first.
- **Dry-run support**: When user requests `--dry-run` or preview, show the exact API request (method, URL, headers, payload) and explain the expected outcome WITHOUT executing. Let user review before proceeding.

## Operations

### create -- Create a new runtime

**API**: `POST /agent-runtimes`

#### Interactive Parameter Gathering

Before creating, gather the following from the user. Ask for required info and recommend sensible defaults for the rest.

**Step 1 - Ask the user for required info:**
- **Name**: Runtime name (lowercase, hyphens allowed). If not provided, ask.
- **Image URL**: Container image URL (e.g. `registry.example.com/my-agent:latest`). Must be provided.
- **Private registry?** Ask explicitly: "Is this image from a private registry?" If yes, `imageAuth` is **required** — collect `username` and `password` (Docker credentials of a user with pull access to the repo). Without these, AgentBase cannot pull the image.

**Step 2 - Recommend defaults, let user override:**

Present a summary with recommended values and ask the user to confirm or adjust:

| Parameter | Recommended | Options |
|-----------|-------------|---------|
| **Flavor** | `1x1-general` (1 CPU, 1 GB RAM) | Fetch available flavors via `GET /flavors` and show as table |
| **Min replicas** | `1` | Range: 1-10 |
| **Max replicas** | `1` | Range: 1-10. Set >1 for auto-scaling |
| **CPU scale threshold** | `50`% | Range: 25-75%. Scale up when CPU exceeds this |
| **Memory scale threshold** | `50`% | Range: 25-75%. Scale up when memory exceeds this |
| **Environment variables** | `{}` | Key-value pairs to inject into container |
| **Command** | `[]` (use image default) | Override Docker ENTRYPOINT |
| **Args** | `[]` (use image default) | Override Docker CMD |
| **Description** | `""` | Optional description |

**Step 3 - Confirm and create:**

Show the final JSON payload and ask the user to confirm before sending.

#### API Reference

**Required fields** (all fields are required by the API):
- `name` (string, min 1 char) -- unique name for the runtime
- `description` (string) -- description of the runtime (can be empty `""`)
- `imageUrl` (string, min 1 char) -- container image URL
- `command` (string array) -- use `[]` to keep image defaults
- `args` (string array) -- use `[]` to keep image defaults
- `environmentVariables` (object, string key-value pairs) -- use `{}` if none
- `flavorId` (string, min 1 char) -- compute flavor ID
- `autoscaling` (object):
  - `minReplicas` (int, 1-10)
  - `maxReplicas` (int, 1-10)
  - `cpuUtilization` (int, 25-75)
  - `memoryUtilization` (int, 25-75)

**Required for private registry** (`imageAuth` object):
- `imageAuth.enabled` (bool, default `true`)
- `imageAuth.username` (string, min 1 char) -- Docker username or robot account with pull access
- `imageAuth.password` (string, min 1 char) -- Docker password or access token

> Without `imageAuth`, AgentBase cannot pull images from private registries — the runtime will fail with an image pull error.

**Example (public registry)**:
```bash
curl -s -X POST "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-agent",
    "description": "",
    "imageUrl": "registry.example.com/my-agent:v1",
    "command": [],
    "args": [],
    "environmentVariables": {},
    "flavorId": "1x1-general",
    "autoscaling": {"minReplicas": 1, "maxReplicas": 1, "cpuUtilization": 50, "memoryUtilization": 50}
  }'
```

**Example (private registry — imageAuth required)**:
```bash
curl -s -X POST "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-agent",
    "description": "",
    "imageUrl": "registry.example.com/my-agent:v1",
    "imageAuth": {"enabled": true, "username": "my-docker-user", "password": "my-password"},
    "command": [],
    "args": [],
    "environmentVariables": {},
    "flavorId": "1x1-general",
    "autoscaling": {"minReplicas": 1, "maxReplicas": 1, "cpuUtilization": 50, "memoryUtilization": 50}
  }'
```

**Behavior**: Creating a runtime automatically creates a `DEFAULT` endpoint that tracks the latest version.

**Note on `command` and `args`**: These follow the Kubernetes container spec convention:
- `command` overrides the Docker image's `ENTRYPOINT` (e.g. `["python"]`)
- `args` overrides the Docker image's `CMD` (e.g. `["main.py"]`)
- Use empty arrays `[]` to keep the image's defaults.

---

### list -- List all runtimes

**API**: `GET /agent-runtimes?page={page}&size={size}`

**Note**: Runtime Service uses 1-indexed pagination (page=1 is first page).

```bash
curl -s "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes?page=1&size=20" \
  -H "Authorization: Bearer $TOKEN"
```

**Response**: `{ "listData": [...], "page": 1, "pageSize": 20, "totalPage": 1, "totalItem": 3 }`

Display results as a table: ID, Name, Status, Image, Created.

---

### get [id] -- Get runtime details

**API**: `GET /agent-runtimes/{id}`

```bash
curl -s "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID" \
  -H "Authorization: Bearer $TOKEN"
```

**Response fields**: `id`, `name`, `description`, `status`, `imageUrl`, `flavorId`, `autoscaling`, `environmentVariables`, `createdAt`, `updatedAt`.

---

### update [id] -- Update a runtime (creates new version)

**API**: `PATCH /agent-runtimes/{id}`

```bash
curl -s -X PATCH "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "",
    "imageUrl": "registry.example.com/my-agent:v2",
    "command": [],
    "args": [],
    "environmentVariables": {},
    "flavorId": "1x1-general",
    "autoscaling": {"minReplicas": 1, "maxReplicas": 1, "cpuUtilization": 50, "memoryUtilization": 50}
  }'
```

**Body fields** (same as create minus `name`): `description`, `imageUrl`, `imageAuth`, `command`, `args`, `environmentVariables`, `flavorId`, `autoscaling`. All fields except `imageAuth` are required.

**Behavior**: Each update creates a new version. The `DEFAULT` endpoint automatically updates to the new version.

---

### delete [id] -- Delete a runtime

**Before deleting**: Consider exporting or noting the resource configuration, as deletion is irreversible. There is no undo.

**API**: `DELETE /agent-runtimes/{id}`

```bash
curl -s -X DELETE "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID" \
  -H "Authorization: Bearer $TOKEN"
```

**Warning**: This permanently deletes the runtime and all its endpoints. Confirm with the user before executing.

---

### endpoints [id] -- Manage endpoints

**List endpoints**: `GET /agent-runtimes/{id}/endpoints`

```bash
curl -s "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID/endpoints?page=1&size=20" \
  -H "Authorization: Bearer $TOKEN"
```

**Create endpoint**: `POST /agent-runtimes/{id}/endpoints`

```bash
curl -s -X POST "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID/endpoints" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "canary", "version": 2}'
```

**Update endpoint version**: `PATCH /agent-runtimes/{id}/endpoints/{endpointId}?version={N}`

```bash
curl -s -X PATCH "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID/endpoints/$ENDPOINT_ID?version=3" \
  -H "Authorization: Bearer $TOKEN"
```

**Delete endpoint**: `DELETE /agent-runtimes/{id}/endpoints/{endpointId}`

```bash
curl -s -X DELETE "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID/endpoints/$ENDPOINT_ID" \
  -H "Authorization: Bearer $TOKEN"
```

**Endpoint response fields**: `id`, `agentRuntimeId`, `name`, `version`, `url`, `status`, `createdAt`, `updatedAt`.

---

### versions [id] -- List runtime versions

**API**: `GET /agent-runtimes/{id}/versions?page={page}&size={size}`

```bash
curl -s "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID/versions?page=1&size=20" \
  -H "Authorization: Bearer $TOKEN"
```

**Version fields**: `agentRuntimeId`, `version`, `imageUrl`, `flavorId`, `autoscaling`, `createdAt`.

Display as a table: Version, Image, Flavor, Created.

---

### status [id] -- Check runtime deployment status

Poll `GET /agent-runtimes/{id}` and check the `status` field.

**macOS/Linux/WSL:**
```bash
# Poll every 10 seconds until status is ACTIVE
while true; do
  STATUS=$(curl -s "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID" \
    -H "Authorization: Bearer $TOKEN" | jq -r '.status')
  echo "Status: $STATUS"
  if [ "$STATUS" = "ACTIVE" ]; then break; fi
  sleep 10
done
```

**Windows (PowerShell):**
```powershell
# Poll every 10 seconds until status is ACTIVE
while ($true) {
  $STATUS = (curl -s "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID" `
    -H "Authorization: Bearer $TOKEN" | jq -r '.status')
  Write-Host "Status: $STATUS"
  if ($STATUS -eq "ACTIVE") { break }
  Start-Sleep -Seconds 10
}
```

**Possible statuses**: `CREATING`, `UPDATING`, `ACTIVE`, `ERROR`, `DELETING`.

---

### reset-service-account [id] -- Reset runtime service account credentials

**API**: `PATCH /agent-runtimes/{id}/reset-service-account`

```bash
curl -s -X PATCH "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID/reset-service-account" \
  -H "Authorization: Bearer $TOKEN"
```

**Warning**: This regenerates the runtime's IAM service account credentials. The runtime will restart with new `GREENNODE_CLIENT_ID` and `GREENNODE_CLIENT_SECRET`. Confirm with the user before executing.

---

## Runtime Service Contract

Read the shared Runtime Service Contract at `/agentbase` skill's `references/runtime-contract.md` for container requirements (port 8080, health check, request headers, auto-injected credentials).

## Available Flavors

To list compute flavors:

```bash
curl -s "https://agentbase.api.vngcloud.vn/runtime/flavors" \
  -H "Authorization: Bearer $TOKEN"
```

Default flavor: `1x1-general` (1 CPU, 1 GB RAM).

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| 401 Unauthorized | Expired or invalid IAM token | Re-obtain token with valid `client_id`/`client_secret` |
| 403 Forbidden | Service account lacks permissions | Check IAM roles at https://iam.console.vngcloud.vn |
| Image pull failure | Wrong `imageUrl` or missing `imageAuth` | Verify image URL, add registry credentials in `imageAuth` |
| Status stuck on `CREATING` | Container failing to start | Check logs via `/agentbase-observe runtime-logs`, verify port 8080 and `/health` endpoint |
| Status `ERROR` | Container crash or health check failure | Check runtime logs for tracebacks, ensure `GET /health` returns 200 |
| Endpoint returns 502 | Container not ready or crashed | Wait for ACTIVE status, check container logs for errors |
