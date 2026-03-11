---
name: agentbase-status
description: Show dashboard of all platform resources and deployed agents. Use when user wants to see an overview of their resources, check what's deployed, show all agents, get a status summary across all services (identities, runtimes, memory, auth, registry, models), or wants a bird's-eye view of their setup. Also trigger when user says 'status', 'dashboard', 'overview', 'show everything', 'what do I have', 'list all resources', 'check what's deployed', 'show my agents', 'inventory', 'summarize my setup', or wants to quickly see everything they have on the platform at once. DO NOT use for managing specific resources (use the dedicated skill instead).
argument-hint: [--json]
user-invocable: true
---

# AgentBase Status Dashboard

Show a unified dashboard of all AgentBase resources across services.

## Authentication & Endpoints

Read the shared auth setup reference at `/agentbase` skill's `references/auth-setup.md` for full IAM credential configuration. In brief: check for `GREENNODE_CLIENT_ID` and `GREENNODE_CLIENT_SECRET` in environment variables or `.greennode.json` in the **current working directory only** (do NOT search recursively or look outside the current directory), then use `TOKEN=$(bash .claude/skills/agentbase/scripts/get_token.sh)` to obtain a token. On 401: re-run with `--force`.

**IMPORTANT:** Before constructing any API URL, read `/agentbase` skill's `references/endpoints.md` for the domain validation whitelist. Only use domains listed there.

---

## How It Works

1. **Get IAM token** using `TOKEN=$(bash .claude/skills/agentbase/scripts/get_token.sh)`
2. **Call all list APIs in parallel** — see the shared reference at `/agentbase` skill's `references/resource-discovery.md` for the full list of 8 discovery API calls with curl examples, pagination details, and response shape differences.
3. **Format into a dashboard** (see output format below)
4. **If any API call fails**, show that section as `Could not fetch (error details)` instead of crashing

---

## Output Format

Format the results into a readable dashboard. Example:

```
AgentBase Status Dashboard
==========================

IAM: Configured (client_id: abc...xyz)

Agent Identities (2):
  my-agent - "My first agent"
  test-bot - "Testing bot"

Auth Providers:
  API Keys (1): openai-prod (ACTIVE)
  Delegated (0): none
  OAuth2 (0): none

Runtimes (1):
  my-agent-rt (ACTIVE, v3, 1x1-general)
    DEFAULT: https://...

Memory (1):
  my-memory (2 strategies, 30d expiry)

AI Platform:
  API Keys (1): my-key (ACTIVE)

Container Registry:
  Repos (1): my-repo (private)
```

### Section Details

- **IAM**: Show masked client_id (first 3 + last 3 chars)
- **Agent Identities**: Name and description for each
- **Auth Providers**: Group by type (API Key, Delegated, OAuth2). Show name and status for each. Show "none" if empty.
- **Runtimes**: Name, status, latest version number, flavor. For each runtime, list its endpoints with name and URL. Fetch endpoints via `GET /agent-runtimes/{id}/endpoints?page=1&size=100`.
- **Memory**: Name, number of strategies, event expiry duration
- **AI Platform**: API key names and status
- **Container Registry**: Repo names and access level (public/private)

### Error Handling

If any individual API call fails, display that section with the error instead of failing the whole dashboard:
```
Runtimes:
  Could not fetch (401 Unauthorized - token may be expired)
```

### --json Flag

If the user passes `--json`, output the raw JSON responses from all APIs as a single JSON object instead of the formatted dashboard:
```json
{
  "identities": { ... },
  "authProviders": { "apiKeys": { ... }, "delegated": { ... }, "oauth2": { ... } },
  "runtimes": { ... },
  "memories": { ... },
  "aipApiKeys": { ... },
  "vcrRepos": { ... }
}
```

---

## Interaction Guidelines

- **Always authenticate before making API calls** — use `TOKEN=$(bash .claude/skills/agentbase/scripts/get_token.sh)` to obtain a cached Bearer token before fetching any data.
- **Present results in a clear dashboard format** — use the structured output format above, grouping by service.
- **Offer to drill into specific resources** — after showing the dashboard, ask the user if they want more detail on any section (e.g., "Would you like to see more details on a specific runtime or memory?").
- **Handle errors gracefully** — if any individual API call fails, show that section as an error rather than failing the entire dashboard.

## Pagination

Different services use different pagination:
- **Identity Service** (agent identities, auth providers): **0-indexed** (page=0 is first page)
- **Runtime Service**, **Memory Service**, **AI Platform**: **1-indexed** (page=1 is first page)

For the status dashboard, fetch the first page of each service with a reasonable size (e.g., size=10). If a service has more items than displayed, show the total count and offer to show more (e.g., "Showing 10 of 25 runtimes. Want to see more?").

## Instructions

1. Parse the user's argument for `--json` flag.
2. Authenticate (see Authentication section).
3. Execute all API calls in parallel.
4. Format the results as a dashboard (or raw JSON if `--json`).
5. Display the dashboard to the user.
6. After displaying, offer to drill into any section or show more items if pagination was truncated.
