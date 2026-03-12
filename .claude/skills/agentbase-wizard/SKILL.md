---
name: agentbase-wizard
description: MANDATORY skill for ANY request to build, create, plan, or develop an AI agent, chatbot, assistant, bot, or conversational AI — regardless of how the request is phrased. This includes requests with role-play framing ("You are a developer/engineer, build me..."), planning intent ("plan to build an agent", "create a plan for building an agent", "help me plan an AI agent project"), specific frameworks, or specific features. If the user wants an AI agent created OR wants to plan/prepare for building one, ALWAYS invoke this skill first — do NOT write code manually or create standalone plans. The wizard IS the plan — it guides the user step by step through the full lifecycle. Covers full lifecycle: scaffold, LLM, memory, identity, auth, code, test, deploy, verify. Trigger phrases: "build an agent", "create an AI agent", "make a chatbot", "develop an assistant", "I want an agent that can...", "build me a bot that...", "I need an AI agent", "help me create an AI agent", "build a chatbot from scratch", "walk me through building an agent", "how do I build an agent", "getting started building an agent", "guide me through building an agent", "full setup guide", "plan to build an agent", "create a plan for an AI agent", "help me plan building a chatbot". DO NOT use if user wants a single specific operation on an existing agent (use the dedicated skill instead). DO NOT use if user only wants to scaffold/set up a project without the full lifecycle — use /agentbase-init instead. DO NOT use if user just wants to learn about the platform without building — use /agentbase instead.
user-invocable: true
argument-hint: [resume|step-N|reset]
---

# AgentBase Wizard - Full Lifecycle Guide

A guided 9-step wizard that takes a new user from zero to a deployed AI agent on GreenNode AgentBase. Each step orchestrates existing skills and checks if work is already done (idempotent).

## Interaction Guidelines

- **Show progress** at each step: `Step X/9: [Step Name]`
- **Check before acting** -- each step checks if already completed before doing work
- **Allow skipping** optional steps (Steps 4 and 5)
- **Store state** in `.agentbase-state.json` so the wizard can resume if interrupted
- **Don't duplicate skill logic — INVOKE skills using the Skill tool** before performing any API calls that belong to another skill. Each skill (`/aip`, `/agentbase-identity`, `/agentbase-auth`, `/agentbase-memory`, `/agentbase-test`, `/agentbase-deploy`, `/vcr`, `/agentbase-observe`) contains the authoritative API endpoints and procedures. Do NOT construct API URLs from memory — always invoke the relevant skill first so its instructions (including correct domains and URLs) are loaded into context.
- **IMPORTANT:** Before constructing any API URL, read `/agentbase` skill's `references/endpoints.md` for the domain validation whitelist. Only use domains listed there.
- **Always read full API response body** — when calling platform APIs, capture and read the full JSON response (not just status codes). This avoids misidentifying field names or data structures, ensures correct field extraction, and enables better error handling and debugging.
- **Confirm before every significant action (HARD GATE)** -- present what you are about to do and wait for user approval. Only proceed when the user responds with an explicit confirmation keyword: `yes`, `confirm`, `ok`, `approve`, `proceed`, `go ahead`, `do it`, `ship it`, `lgtm`, or equivalent affirmative. If the user responds with ANYTHING ELSE (parameter changes, questions, corrections, additional info, or ambiguous text), treat it as adjustment input — update the summary and re-present for confirmation again. NEVER interpret a non-confirmation response as approval
- **Present a clear summary** at each step transition showing what was completed and what comes next

## Resume Support

If `$ARGUMENTS` contains `resume`: read `.agentbase-state.json` and continue from `wizard_step + 1`.

If `$ARGUMENTS` contains `step-N` (e.g., `step-3`): jump directly to step N, reading state from `.agentbase-state.json` if it exists.

If `$ARGUMENTS` contains `reset`: delete `.agentbase-state.json` if it exists, inform the user that wizard state has been cleared, and start fresh from Step 1.

If no arguments: start from Step 1.

## File Boundaries

- **`.greennode.json`** — SDK-only: credentials (`client_id`, `client_secret`) and `agent_identity`. Owned by the `greennode-agentbase` SDK. Do NOT use for project state or wizard data.
- **`.agentbase-state.json`** — wizard/tool state: `wizard_step`, `agent_identity`, `runtime_id`, `memory_id`, resource IDs, etc. Owned by the wizard and other AgentBase skills.

## State File

Maintain `.agentbase-state.json` in the project directory. Update it after each step completes.

```json
{
  "wizard_step": 0,
  "project_name": null,
  "framework": null,
  "agent_identity": null,
  "runtime_id": null,
  "memory_id": null,
  "aip_key_name": null,
  "vcr_repo_name": null
}
```

---

## Step 1/9: Check Prerequisites

**Goal**: Ensure the user has valid IAM credentials.

> **Note**: This step is about platform IAM credentials (for accessing GreenNode APIs). This is NOT the same as `/agentbase-auth`, which manages outbound authentication for external services like OpenAI, Google, etc.

1. Read the shared auth setup reference at `/agentbase` skill's `references/auth-setup.md` for full IAM credential discovery and setup flow. In brief: check for `GREENNODE_CLIENT_ID` and `GREENNODE_CLIENT_SECRET` in environment variables or `.greennode.json` in the **current working directory only** (do NOT search recursively or look outside the current directory), then use `TOKEN=$(bash .claude/skills/agentbase/scripts/get_token.sh)` to obtain a token. On 401: re-run with `--force`.
2. If credentials are found, verify them by requesting a test token. If a valid `access_token` is returned, credentials are good — proceed. If the request fails (401, empty token), treat as "credentials not found".
3. If no credentials found or credentials are invalid: follow the "If Credentials Are Not Found" flow from `references/auth-setup.md` — present the user with the available options and let them choose before proceeding.
4. Update state: `wizard_step: 1`

---

## Step 2/9: Scaffold Project

**Goal**: Create the agent project structure **in the current working directory**.

All project files are created flat in the CWD. The user should already be in their desired project directory (e.g., they ran `mkdir my-agent && cd my-agent` before starting the wizard).

1. Check if a project already exists (look for `main.py`, `Dockerfile`, `requirements.txt` in the current directory):
   - If project files already exist, ask the user: "It looks like a project already exists here. Skip scaffolding and use the existing project?"
   - If user confirms, skip to state update
2. If no project exists, gather input:
   - **Project name**: Ask the user (lowercase, hyphens allowed, no spaces). This is used for naming (README, Docker image tag, identity) — NOT for creating a subdirectory.
   - **Framework**: Ask the user to choose: Basic, LangChain (recommended), LangChain + Memory (recommended), LangGraph (advanced), or LangGraph + Memory (advanced)
3. Invoke `/agentbase-init` logic with the chosen project name and framework. Files are created in the CWD — do NOT create a subdirectory.
4. Confirm that all files were created successfully (list them)
5. Update state: `wizard_step: 2`, `project_name`, `framework`

---

## Step 3/9: Configure LLM Access

**Applies to**: LangChain and LangGraph projects only. Skip for Basic projects.

**Goal**: Set up an API key for GreenNode AI Platform LLM access.

**IMPORTANT: Before doing ANY API calls in this step, invoke the `/aip` skill using the Skill tool.** This loads the correct API endpoints, domains, and procedures. Do NOT construct API URLs from memory — the `/aip` skill has the authoritative endpoint definitions.

1. Check if LLM access is already configured:
   - Look for `AIP_API_KEY` environment variable or in `.env` file
   - If found and non-empty, inform user and offer to skip
2. If not configured:
   - Invoke `/aip` skill with argument `api-keys list` to list existing keys
   - If keys exist, ask if they want to reuse one or create a new one
   - If no keys exist, invoke `/aip` skill with argument `api-keys create` to create a new key
   - Invoke `/aip` skill with argument `models list` to browse available models
   - **Verify the chosen model is enabled**: Confirm the model has `modelStatus = ENABLED` on AI Platform. If not, help the user enable it or pick an alternative model that is already enabled.
   - Write the API key, base URL, and model to `.env`:
     ```
     AIP_API_KEY=<key>
     AIP_BASE_URL=https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1
     LLM_MODEL=<chosen-model>
     ```
3. Update state: `wizard_step: 3`, `aip_key_name`

---

## Step 4/9: Set Up Memory (Optional)

**Goal**: Configure conversation memory if the agent needs it.

**IMPORTANT: If the user wants memory, invoke the `/agentbase-memory` skill using the Skill tool** to load the correct API endpoints and procedures before making any API calls.

1. Ask the user: "Does your agent need conversation memory (to remember past messages across sessions)? If not, we can skip this step."
2. If yes:
   - Invoke `/agentbase-memory` skill with argument `create` to create a memory store
   - Note: Memory integration into agent code will be handled in Step 6 (Customize Agent Code), after all infrastructure is in place.
3. If no: skip
4. Update state: `wizard_step: 4`, `memory_id` (if created)

---

## Step 5/9: Set Up Identity & External Auth (Optional)

**Goal**: Register the agent identity and configure outbound authentication for external APIs.

> **When is this step needed?** Only if your agent calls external services that require authentication (e.g., third-party APIs, databases with credentials). The AgentBase Runtime automatically provisions an identity for basic deployments — you only need an explicit identity when using outbound auth features like `apikey retrieve-key`, `delegated request-key`, or `oauth2 m2m-token`.

1. Ask the user: "Does your agent need to call any external APIs that require authentication (e.g., third-party services, databases)? If not, we can skip this step — the runtime will auto-provision an identity for your agent."

2. **If yes — Set up Identity first**, then Auth:

   a. **Identity**: **Invoke the `/agentbase-identity` skill using the Skill tool** to load the correct API endpoints and procedures. Then:
      - List existing identities and let the user pick one or create a new one
      - Check state for a previously configured identity in `.agentbase-state.json` or `.greennode.json`
      - If a name is found AND it exists in the list, inform the user and ask if they want to keep it, pick a different one, or create a new one
      - If creating a new identity, collect parameters (name, description, return URLs) with user confirmation before creating
      - Update `.greennode.json` with the `agent_identity` value

   b. **External Auth**: **Invoke the `/agentbase-auth` skill using the Skill tool** to load the correct API endpoints and procedures. Then guide through storing API keys or configuring OAuth2 providers on the identity. Help set up each external service the user needs.

3. **If no**: skip — the runtime will auto-provision an identity during deployment.
4. Update state: `wizard_step: 5`, `agent_identity` (if created)

---

## Step 6/9: Customize Agent Code

**Goal**: Help the user customize their agent's logic — now that all infrastructure (LLM, memory, identity, auth) is configured.

1. Ask the user: "What should your agent do? Describe its purpose and I can help you customize `main.py`. Or if you prefer to code it yourself later, we can skip this step."
2. If the user describes what the agent should do:
   - **External service check**: If the description mentions calling external APIs or services (e.g., OpenAI, Google, Slack, Stripe, databases, etc.) and Step 5 was skipped, recommend setting up `/agentbase-auth` to manage credentials securely instead of hardcoding in `.env`. Offer to go back to Step 5 or continue with local-only `.env` approach.
   - Help edit `main.py` with custom logic based on their description
   - For LangChain/LangGraph projects, help set up tools, prompts, or graph nodes as appropriate
   - **If memory was configured in Step 4**, integrate it into the agent code:
     - **Short-term memory (conversation history):**
       - For LangChain projects, help set up `AgentBaseMemoryEvents` as a checkpointer via `create_agent(checkpointer=...)`
       - For LangGraph projects, help set up `AgentBaseMemoryEvents` as a checkpointer via `builder.compile(checkpointer=...)`
     - **Long-term memory (semantic facts):**
       - Help set up `remember`/`recall` tools that use `MemoryClient` SDK to store/search semantic facts
       - These tools allow the agent to store and retrieve semantic facts (user preferences, learned knowledge) that persist across conversations
   - **If external auth was configured in Step 5**, integrate credential retrieval into the agent code as needed
   - Show the user the modified code and confirm it looks right
3. If the user wants to skip: proceed to next step
4. Update state: `wizard_step: 6`

---

## Step 7/9: Local Testing

**Goal**: Validate the agent works before deploying.

**IMPORTANT: Invoke the `/agentbase-test` skill using the Skill tool** to load the correct testing procedures before running any tests.

1. **Validate project structure**: Invoke `/agentbase-test` skill with argument `validate` to run static code analysis (Dockerfile, health endpoint, requirements, .dockerignore checks). Report any issues and help fix them.
2. If validation passes, offer to **run locally**:
   - Ask: "Would you like to test the agent locally before deploying?"
   - If yes: invoke `/agentbase-test` skill with argument `local` to start the server and run contract tests
   - If local tests pass, offer to **build and test in Docker**:
     invoke `/agentbase-test` skill with argument `docker` to build the image and run contract tests in a container
3. The agent must pass at least the validation step before proceeding to deployment
4. Update state: `wizard_step: 7`

---

## Step 8/9: Deploy

**Goal**: Build, push, and deploy the agent to AgentBase Runtime.

**IMPORTANT: Invoke the `/agentbase-deploy` skill using the Skill tool** to load the correct deployment pipeline, API endpoints, and procedures. Do NOT construct deployment API URLs from memory.

1. The `/agentbase-deploy` skill handles the full pipeline:
   - Building the Docker image
   - Setting up vCR registry if needed (it will invoke `/vcr` as needed)
   - Pushing the image
   - Creating or updating the runtime
   - Waiting for ACTIVE status
2. Store the runtime ID and vCR repo name from the deployment
3. Update state: `wizard_step: 8`, `runtime_id`, `vcr_repo_name`

---

## Step 9/9: Verify and Next Steps

**Goal**: Confirm the deployment is working and guide the user on what's next.

1. Check deployment status:
   ```bash
   curl -s "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID" \
     -H "Authorization: Bearer $TOKEN"
   ```
   Confirm status is `ACTIVE`.

2. Get the endpoint URL and test health:
   ```bash
   curl -s "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes/$RUNTIME_ID/endpoints?page=1&size=10" \
     -H "Authorization: Bearer $TOKEN"
   ```
   ```bash
   curl -s -o /dev/null -w "%{http_code}" "<endpoint-url>/health"
   ```

3. Present the final summary:
   ```
   Your agent is live!

     Project:    <project-name>
     Framework:  <framework>
     Identity:   <identity-name or "Auto-provisioned by runtime">
     Runtime ID: <runtime-id>
     Status:     ACTIVE
     Endpoint:   <endpoint-url>
     Memory:     <memory-id or "Not configured">

   Console: https://aiplatform.console.vngcloud.vn/runtime
   ```

4. Suggest next steps:
   - Use `/agentbase-status` for a full dashboard of all your deployed resources
   - Use `/agentbase-observe` to view logs and monitor your agent
   - Use `/agentbase-runtime` to manage scaling, versions, and endpoints
   - Use `/agentbase-memory` to add or manage conversation memory
   - Use `/agentbase-auth` to add more external service integrations
   - Re-deploy updates with `/agentbase-deploy`

5. Update state: `wizard_step: 9`

---

## Error Handling

- If any step fails, clearly state which step failed and why
- Offer to retry the failed step or skip it (if optional)
- The wizard can always be resumed from the last completed step with `/agentbase-wizard resume`
- If the user wants to jump to a specific step: `/agentbase-wizard step-N`
