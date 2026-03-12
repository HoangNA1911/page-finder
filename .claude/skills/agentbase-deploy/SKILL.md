---
name: agentbase-deploy
description: Deploy an AI agent to production (end-to-end). Handles full pipeline: build Docker image, push to registry, create/update runtime, verify deployment. Also trigger for post-build deployment intent: "after testing, deploy it", "then deploy", "ship it to production". Trigger phrases: "deploy my agent", "ship it", "go live", "put it online", "release new version", "push to production", "make it live", "deploy to production", "publish my agent". DO NOT use for managing existing runtimes, endpoints, or versions without deploying new code — use /agentbase-runtime instead. DO NOT trigger for deploying non-AI-agent applications (React apps, web apps, microservices, etc.) — this skill is exclusively for AI agent deployment on GreenNode AgentBase.
argument-hint: [runtime-name]
user-invocable: true
---

# AgentBase Deploy Workflow

Full end-to-end deployment of an agent to GreenNode AgentBase Runtime.

## Interaction Guidelines

- **Guide first, act only when asked** — if the user asks "how to" deploy or about the deployment process, respond with instructions and guidance only. Do NOT execute the deployment pipeline unless they explicitly ask you to do it (e.g., "deploy my agent", "ship it").
- **Present full deployment plan before starting (HARD GATE)** — before executing any step, present a complete deployment plan summarizing all parameters (runtime name, image tag, registry URL, build platform, compute flavor, autoscaling settings, etc.) and ask the user to confirm. Do NOT start execution until the user responds with an explicit confirmation keyword: `yes`, `confirm`, `ok`, `approve`, `proceed`, `go ahead`, `do it`, `ship it`, `lgtm`, or equivalent affirmative. If the user responds with ANYTHING ELSE (parameter changes, questions, corrections, additional info, or ambiguous text), treat it as adjustment input — update the plan and re-present the full summary for confirmation again. NEVER interpret a non-confirmation response as approval.
- **Re-present plan after any adjustment** — if the user requests changes to the plan (e.g., different runtime name, different flavor, different registry), update the plan and present the **full updated plan** again for confirmation. Do NOT proceed with execution until the user explicitly approves the updated plan with a confirmation keyword. This applies to every adjustment — always re-present and wait for explicit approval.
- **Never auto-decide parameters** — when a step requires parameters (e.g., runtime name, image tag, platform, flavor, registry credentials), always ask the user for each required value. You may recommend sensible defaults or options, but never auto-select or impose values without the user's explicit agreement.
- **Present options, let user choose** — when there are multiple choices (e.g., build platform, compute flavor, registry auth method), list the available options and let the user pick. Do not make the choice for them.
- **Dry-run support**: When user requests `--dry-run` or preview, show the exact API request (method, URL, headers, payload) and explain the expected outcome WITHOUT executing. Let user review before proceeding.
- **Always read full API response body** — when calling platform APIs, capture and read the full JSON response (not just status codes). This avoids misidentifying field names or data structures, ensures correct field extraction, and enables better error handling and debugging.

## Prerequisites

Before starting, gather:
- **IAM credentials** (needed for calling platform APIs during deployment — the deployed container gets its own credentials auto-injected by the runtime): Read the shared auth setup reference at `/agentbase` skill's `references/auth-setup.md` for full IAM credential configuration. In brief: check for `GREENNODE_CLIENT_ID` and `GREENNODE_CLIENT_SECRET` in environment variables or `.greennode.json` in the **current working directory only** (do NOT search recursively or look outside the current directory), then fetch an access token via the IAM token endpoint.
- **API domains**: Before constructing any API URL, read `/agentbase` skill's `references/endpoints.md` for the domain validation whitelist. Only use domains listed there.
- **Docker registry URL**: Ask the user if not previously configured. The image will be pushed here.
- **Runtime name**: From the argument, or ask the user.

## Deployment Steps

### Step 1: Validate Project

Check the current working directory for required files:

- [ ] `Dockerfile` exists
- [ ] Agent entrypoint exists (e.g. `main.py`, `app.py`, or as defined in Dockerfile CMD)
- [ ] Dependencies file exists (`requirements.txt`, `pyproject.toml`, `package.json`, etc.)
- [ ] Agent exposes `GET /health` returning HTTP 200 (search code for a `/health` route)
- [ ] `.dockerignore` exists and excludes sensitive files

If any are missing, inform the user what is needed and offer to help create them. Do NOT proceed until validation passes.

**Dockerfile requirements**:
- Must expose port `8080`
- Must install dependencies
- Can use any language/framework as long as it satisfies the runtime service contract

**CRITICAL — `.dockerignore` and sensitive files**:
- Check if a `.dockerignore` file exists. If not, **create one** before building. It MUST exclude at minimum:
  ```
  .env
  .env.*
  .greennode.json
  .git/
  .venv/
  venv/
  __pycache__/
  *.py[cod]
  ```
- If `.dockerignore` exists, verify it excludes `.env`, `.env.*`, and `.greennode.json`. If any are missing, **warn the user** and offer to add them.
- **NEVER allow sensitive files** (`.env`, `.greennode.json`, credential files, API keys) to be copied into the Docker image. This is a security risk — secrets baked into images can be extracted by anyone with access to the image.
- If the Dockerfile uses `COPY . .` without a proper `.dockerignore`, warn the user that all files including secrets will be copied into the image.
- **For environment variables needed at runtime** (beyond what AgentBase auto-injects like `GREENNODE_CLIENT_ID`, `GREENNODE_CLIENT_SECRET`, `GREENNODE_AGENT_IDENTITY`): these should be configured via the `environmentVariables` field in the runtime create/update API, NOT baked into the Docker image. Ask the user if they need any additional environment variables and include them in the runtime API call.

**Ask the user** if they have a preference for:
- Compute flavor (default: `1x1-general` -- 1 CPU, 1 GB RAM). List flavors with `/agentbase-runtime` if needed.
- Autoscaling settings (default: 1 replica, no scaling)

### Step 2: Build Docker Image

**Ask the user** which platform to build for using AskUserQuestion:
- `linux/amd64` (Recommended) — AgentBase Runtime runs on amd64. Required when building on Apple Silicon (arm64) to ensure compatible images.
- `linux/arm64` — Use if the target runtime supports ARM architecture.

Then build with the selected platform:

```bash
docker build --platform <selected-platform> -t <registry>/<runtime-name>:<tag> .
```
- Use the runtime name as the image name.
- For the tag, use a timestamp-based tag or `latest`. Generate the tag based on the user's OS:
  - **macOS/Linux**: `v$(date +%Y%m%d%H%M%S)`
  - **Windows (PowerShell)**: `v$(Get-Date -Format "yyyyMMddHHmmss")`
  - Or simply use `latest` (works on all platforms)
- If the build fails, show the error output and help the user fix it.

### Step 3: Push to Registry

**Before pushing**, ask the user how they want to authenticate with the Docker registry using AskUserQuestion. Present these three options:

1. **Already logged in** — The user has already run `docker login` for the target registry. Verify by attempting to pull a nonexistent image:
   ```bash
   docker pull <registry-host>/nonexistent/verify-auth:test 2>&1
   ```
   If the output contains "not found" or "manifest unknown", auth is working — proceed with the push. If the output contains "unauthorized" or "denied", the user is not logged in — ask them to choose another option.

2. **Provide credentials** — The user provides registry credentials manually. Collect:
   - **Registry host** (e.g., `vcr.vngcloud.vn`, `docker.io`, `ghcr.io`)
   - **Username**
   - **Password / token**
   Then run `docker login`:
   ```bash
   echo "$PASSWORD" | docker login <registry-host> -u <username> --password-stdin
   ```

3. **Create a new repo on vCR** — The user wants to create a new Docker repository on GreenNode Container Registry (vCR) and set up credentials from scratch. Invoke the `/vcr` skill to:
   - **Check for existing repos first** — vCR repo names must be unique. List existing repos and offer to reuse if a match is found.
   - Create a repository on vCR (only if no duplicate exists)
   - Create a robot account with push+pull permissions
   - Run `docker login vcr.vngcloud.vn` with the robot account credentials
   After the `/vcr` skill completes, continue with the push using the vCR registry path.

Once authentication is confirmed, push the image:

```bash
docker push <registry>/<runtime-name>:<tag>
```

- If push fails, check for authentication issues or network errors.

**Private registry check**: After a successful push, ask the user if the registry is **private** (requires authentication to pull). If yes, collect and save:
- `REGISTRY_USERNAME` — Docker username or robot account
- `REGISTRY_PASSWORD` — Docker password or token

These credentials will be passed as `imageAuth` when creating/updating the runtime so AgentBase can pull the image.

### Step 4: Create or Update Runtime

Obtain an IAM token: `TOKEN=$(bash .claude/skills/agentbase/scripts/get_token.sh)`. On 401: re-run with `--force`.

Then check if a runtime with this name already exists:

```bash
curl -s "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes?page=1&size=100" \
  -H "Authorization: Bearer $TOKEN"
```

Search the response `listData` for a matching `name`.

#### If NEW runtime (no existing match):

For **public registry**:
```bash
curl -s -X POST "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "<runtime-name>",
    "description": "",
    "imageUrl": "<registry>/<runtime-name>:<tag>",
    "command": [],
    "args": [],
    "environmentVariables": {},
    "flavorId": "1x1-general",
    "autoscaling": {"minReplicas": 1, "maxReplicas": 1, "cpuUtilization": 50, "memoryUtilization": 50}
  }'
```

For **private registry** (add `imageAuth` with credentials collected in Step 3):
```bash
curl -s -X POST "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "<runtime-name>",
    "description": "",
    "imageUrl": "<registry>/<runtime-name>:<tag>",
    "imageAuth": {"enabled": true, "username": "<REGISTRY_USERNAME>", "password": "<REGISTRY_PASSWORD>"},
    "command": [],
    "args": [],
    "environmentVariables": {},
    "flavorId": "1x1-general",
    "autoscaling": {"minReplicas": 1, "maxReplicas": 1, "cpuUtilization": 50, "memoryUtilization": 50}
  }'
```

This automatically creates a `DEFAULT` endpoint.

#### If EXISTING runtime (update):

For **public registry**:
```bash
curl -s -X PATCH "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "",
    "imageUrl": "<registry>/<runtime-name>:<tag>",
    "command": [],
    "args": [],
    "environmentVariables": {},
    "flavorId": "1x1-general",
    "autoscaling": {"minReplicas": 1, "maxReplicas": 1, "cpuUtilization": 50, "memoryUtilization": 50}
  }'
```

For **private registry** (add `imageAuth` with credentials collected in Step 3):
```bash
curl -s -X PATCH "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "",
    "imageUrl": "<registry>/<runtime-name>:<tag>",
    "imageAuth": {"enabled": true, "username": "<REGISTRY_USERNAME>", "password": "<REGISTRY_PASSWORD>"},
    "command": [],
    "args": [],
    "environmentVariables": {},
    "flavorId": "1x1-general",
    "autoscaling": {"minReplicas": 1, "maxReplicas": 1, "cpuUtilization": 50, "memoryUtilization": 50}
  }'
```

This creates a new version. The `DEFAULT` endpoint auto-updates to the new version.

**Canary deployment** (optional): If the user wants to test before routing all traffic, create a custom endpoint pointing to the new version:

```bash
# Get the latest version number from the update response or list versions
curl -s -X POST "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID/endpoints" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "canary", "version": <new-version-number>}'
```

### Step 5: Wait for ACTIVE Status

Poll the runtime status until it becomes `ACTIVE`. Use the appropriate version for the user's OS:

**macOS/Linux/WSL:**
```bash
RUNTIME_ID="<id-from-step-4>"
for i in $(seq 1 30); do
  STATUS=$(curl -s "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID" \
    -H "Authorization: Bearer $TOKEN" | jq -r '.status')
  echo "Attempt $i: Status = $STATUS"
  if [ "$STATUS" = "ACTIVE" ]; then break; fi
  if [ "$STATUS" = "ERROR" ]; then
    echo "Deployment failed with ERROR status."
    break
  fi
  if [ "$i" = "30" ]; then
    echo "Timed out after 5 minutes. Status is still $STATUS."
    break
  fi
  sleep 10
done
```

**Windows (PowerShell):**
```powershell
$RUNTIME_ID = "<id-from-step-4>"
for ($i = 1; $i -le 30; $i++) {
  $STATUS = (curl -s "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID" `
    -H "Authorization: Bearer $TOKEN" | jq -r '.status')
  Write-Host "Attempt ${i}: Status = $STATUS"
  if ($STATUS -eq "ACTIVE") { break }
  if ($STATUS -eq "ERROR") { Write-Host "Deployment failed with ERROR status."; break }
  Start-Sleep -Seconds 10
}
```

If status is `ERROR` after polling, show the runtime details and help debug. Common issues:
- Image pull failures (wrong URL or auth)
- Container crash on startup (check health endpoint)
- Port mismatch (container must listen on 8080)

### Step 6: Get Endpoint URL

```bash
curl -s "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID/endpoints?page=1&size=10" \
  -H "Authorization: Bearer $TOKEN"
```

Find the `DEFAULT` endpoint in the response and extract its `url` field.

### Step 7: Test Health

```bash
curl -s -o /dev/null -w "%{http_code}" "<endpoint-url>/health"
```

Expect HTTP 200. If it fails, the container may still be starting -- retry a few times with short delays.

### Step 8: Report Deployment Result

Present a summary to the user:

```
Deployment complete!

  Runtime:   <runtime-name>
  Runtime ID: <runtime-id>
  Version:   <version-number>
  Status:    ACTIVE
  Endpoint:  <endpoint-url>
  Health:    OK (200)

Console: https://aiplatform.console.vngcloud.vn/runtime
```

Use `/agentbase-observe` to monitor logs and debug issues after deployment.

> **Agent Identity**: The runtime automatically provisions an agent identity for the deployed container. See `/agentbase-identity` for managing agent identities manually or viewing the auto-provisioned one.

> **Memory-enabled agents**: If your agent uses conversation memory or long-term memory, set up the Memory Service first using `/agentbase-memory` before deploying, so the memory container is ready when the agent starts.

If the deployment failed at any step, clearly state which step failed, show error details, and suggest fixes.

### Rollback

To rollback to a previous version, update the endpoint to point to the previous version number:

```bash
# List versions to find the previous one
curl -s "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID/versions?page=1&size=10" \
  -H "Authorization: Bearer $TOKEN"

# Update DEFAULT endpoint to previous version
curl -s -X PATCH "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID/endpoints/$ENDPOINT_ID?version=$PREVIOUS_VERSION" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Runtime Service Contract

Read the shared Runtime Service Contract at `/agentbase` skill's `references/runtime-contract.md` for container requirements (port 8080, health check, request headers, auto-injected credentials).
