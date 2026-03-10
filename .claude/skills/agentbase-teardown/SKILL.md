---
name: agentbase-teardown
description: "Clean up and remove all GreenNode AgentBase resources for a project. Use when user wants to tear down, clean up, decommission, or delete all resources associated with an agent (runtime, identity, auth, memory, registry, API keys). DO NOT use for deleting a single resource (use the dedicated skill instead)."
argument-hint: "[project-name] [--dry-run]"
---

# AgentBase Teardown

Guided cleanup of all AgentBase resources for a project or agent.

## Authentication & Endpoints

Read the shared auth setup reference at `/agentbase` skill's `references/auth-setup.md` for full IAM credential configuration. In brief: check for `GREENNODE_CLIENT_ID` and `GREENNODE_CLIENT_SECRET` in environment variables or `.greennode.json` in the **current working directory only** (do NOT search recursively or look outside the current directory), then use `TOKEN=$(bash .claude/skills/agentbase/scripts/get_token.sh)` to obtain a token. On 401: re-run with `--force`.

**IMPORTANT:** Before constructing any API URL, read `/agentbase` skill's `references/endpoints.md` for the domain validation whitelist. Only use domains listed there.

---

## Interaction Guidelines

- **ALWAYS show full deletion plan before executing** — never delete anything without showing the user exactly what will be removed
- **ALWAYS require explicit confirmation (HARD GATE)** — the user must respond with an explicit confirmation keyword (`yes`, `confirm`, `ok`, `approve`, `proceed`, `go ahead`, `do it`, `lgtm`, or equivalent affirmative) before any deletion begins. If the user responds with ANYTHING ELSE (deselecting items, questions, adjustments, or ambiguous text), treat it as additional input — update the plan and re-present for confirmation again. NEVER interpret a non-confirmation response as approval
- **Support --dry-run** — if the user passes `--dry-run`, show the plan only and do not execute any deletions
- **Let user deselect items** — after presenting the plan, let the user choose which items to keep (e.g., "keep the AIP key, delete everything else")
- **Warn about shared resources** — if a resource may be used by other agents (e.g., an AIP API key, an auth provider), explicitly warn the user (e.g., "This AIP key may be used by other agents")
- **Show progress during deletion** — report each deletion as it completes

---

## How It Works

### Step 1: Identify the Project

Determine which project/agent to tear down:
- If a project name is provided as argument, use it
- If `.agentbase-state.json` exists in the current directory, read the agent/project name from it
- Otherwise, ask the user which agent/project to tear down

### Step 2: Discover Related Resources

Authenticate and call all list APIs in parallel to find resources matching the project name. See the shared reference at `/agentbase` skill's `references/resource-discovery.md` for the full list of 8 discovery API calls with curl examples, pagination details, and response shape differences.

**Resource matching priority**:
1. **Exact resource IDs** from `.agentbase-state.json` or `.greennode.json` (preferred — most precise)
2. **Name matching** — look for resources whose name contains or matches the project name (case-insensitive)

> **Warning**: Name-based matching can be broad. For example, a project named "test" could match "test-agent" AND "api-test". Always show exact resource IDs (not just names) in the deletion plan so the user can verify which resources will be affected. If pattern matching finds resources that may belong to other projects, explicitly warn the user.

### Step 3: Present Deletion Plan

Show the user a numbered plan of what will be deleted:

```
Teardown Plan for "my-agent":
  1. Delete runtime endpoints (2 endpoints)
  2. Delete runtime "my-agent-rt" (v3)
  3. Delete auth provider "openai-key" (API Key)
  4. Delete agent identity "my-agent"
  5. Delete memory "my-agent-memory"
  6. Delete vCR repo "my-agent-repo"
  7. Delete AIP API key "my-agent-key" (shared resource)

All deletions are IRREVERSIBLE.
Proceed with all? Or type numbers to exclude (e.g., "skip 6,7"):
```

If no related resources are found, tell the user and stop.

### Step 4: Get User Confirmation

Wait for the user to:
- Confirm all deletions
- Deselect specific items (e.g., "skip 7" or "keep the AIP key")
- Cancel entirely

Do NOT proceed without explicit confirmation.

### Step 5: Execute Deletions in Dependency Order

Delete in this specific order to avoid dependency errors. If any API call returns 401 Unauthorized during the teardown sequence, re-fetch the IAM token and retry the failed call before continuing.

**Phase 1 — Runtime endpoints:**
```bash
# List endpoints for each runtime
curl -s "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID/endpoints?page=1&size=100" \
  -H "Authorization: Bearer $TOKEN"

# Delete each non-DEFAULT endpoint
curl -s -X DELETE "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID/endpoints/$ENDPOINT_ID" \
  -H "Authorization: Bearer $TOKEN"
```

**Phase 2 — Runtimes:**
```bash
curl -s -X DELETE "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID" \
  -H "Authorization: Bearer $TOKEN"
```

**Phase 3 — Auth providers** (API Key, Delegated, OAuth2):
```bash
# API Key providers
curl -s -X DELETE "https://agentbase.api.vngcloud.vn/identity/api/v1/outbound-auth/api-key-providers/$NAME" \
  -H "Authorization: Bearer $TOKEN"

# Delegated providers
curl -s -X DELETE "https://agentbase.api.vngcloud.vn/identity/api/v1/outbound-auth/delegated-api-key-providers/$NAME" \
  -H "Authorization: Bearer $TOKEN"

# OAuth2 providers
curl -s -X DELETE "https://agentbase.api.vngcloud.vn/identity/api/v1/outbound-auth/oauth2-providers/$NAME" \
  -H "Authorization: Bearer $TOKEN"
```

**Phase 4 — Agent identity:**
```bash
curl -s -X DELETE "https://agentbase.api.vngcloud.vn/identity/api/v1/agent-identities/$NAME" \
  -H "Authorization: Bearer $TOKEN"
```

**Phase 5 — Memory:**
```bash
curl -s -X DELETE "https://agentbase.api.vngcloud.vn/memory/memories/$MEMORY_ID" \
  -H "Authorization: Bearer $TOKEN"
```

**Phase 6 — vCR repositories:**
> **Important**: You MUST delete all images in a repo before deleting the repo itself — the vCR API rejects repo deletion if any images remain.

```bash
# Step 1: List all images in the repo (paginate if totalPage > 1)
curl -s "https://vcr.api.vngcloud.vn/v1/repository/$REPO_ID/images?name=&page=1&size=100" \
  -H "Authorization: Bearer $TOKEN"

# Step 2: Delete each image (repeat for every imageName returned)
curl -s -X DELETE "https://vcr.api.vngcloud.vn/v1/repository/$REPO_ID/images/delete?imageName=$IMAGE_NAME" \
  -H "Authorization: Bearer $TOKEN"

# Step 3: After all images are deleted, delete the repo
curl -s -X DELETE "https://vcr.api.vngcloud.vn/v1/repository/$REPO_ID" \
  -H "Authorization: Bearer $TOKEN"
```

**Phase 7 — AIP API keys** (optional, may be shared):
```bash
curl -s -X DELETE "https://aiplatform-hcm.api.vngcloud.vn/v1/api-keys/$KEY_NAME" \
  -H "Authorization: Bearer $TOKEN"
```
After deleting an AIP key, poll `GET /v1/api-keys/{name}` every 3 seconds until HTTP 404 (timeout ~30s) to confirm deletion.

### Step 6: Report Results

Show a summary of what was deleted and any errors:

```
Teardown Results for "my-agent":
  Deleted runtime endpoints (2)
  Deleted runtime "my-agent-rt"
  Deleted auth provider "openai-key"
  Deleted agent identity "my-agent"
  Deleted memory "my-agent-memory"
  Skipped vCR repo "my-agent-repo" (user chose to keep)
  Failed to delete AIP key "my-agent-key" (403 Forbidden)

Teardown complete. 5 of 7 resources removed.
```

### Step 7: Clean Up Local State

If `.agentbase-state.json` exists in the current directory, offer to remove it:
```
Found .agentbase-state.json in current directory. Remove it? (y/n)
```

---

## Instructions

1. Parse the user's argument for project name and `--dry-run` flag.
2. Authenticate (see Authentication section).
3. Identify the project (argument, `.agentbase-state.json`, or ask user).
4. Discover all related resources across all services (parallel API calls).
5. Present the deletion plan with numbered items.
6. If `--dry-run`, stop after showing the plan.
7. Wait for user confirmation (allow deselecting items).
8. Execute deletions in dependency order, reporting progress.
9. Show final summary.
10. Offer to clean up `.agentbase-state.json` if present.
