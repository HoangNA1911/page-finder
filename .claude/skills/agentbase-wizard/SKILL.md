---
name: agentbase-wizard
description: "START HERE if you're new to GreenNode AgentBase. Guided full lifecycle wizard for creating AI agents on GreenNode AgentBase. Use when user is new to the platform, wants step-by-step guidance from zero to deployed agent, or says 'help me create an agent'. Covers: setup, scaffold, LLM, memory, identity, auth, code, test, deploy, verify. DO NOT use if user wants to perform a specific operation (use the dedicated skill instead)."
user-invocable: true
argument-hint: "[resume|step-N|reset]"
---

# AgentBase Wizard - Full Lifecycle Guide

A guided 9-step wizard that takes a new user from zero to a deployed AI agent on GreenNode AgentBase. Each step orchestrates existing skills and checks if work is already done (idempotent).

## Interaction Guidelines

- **Show progress** at each step: `Step X/9: [Step Name]`
- **Check before acting** -- each step checks if already completed before doing work
- **Allow skipping** optional steps (Steps 4 and 5)
- **Store state** in `.agentbase-state.json` so the wizard can resume if interrupted
- **Don't duplicate skill logic** -- reference and invoke existing skills (`/agentbase-init`, `/agentbase-identity`, `/agentbase-auth`, `/agentbase-memory`, `/agentbase-deploy`, `/aip`, `/agentbase-observe`)
- **IMPORTANT:** Before constructing any API URL, read `/agentbase` skill's `references/endpoints.md` for the domain validation whitelist. Only use domains listed there.
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

1. Check if LLM access is already configured:
   - Look for `AIP_API_KEY` environment variable or in `.env` file
   - If found and non-empty, inform user and offer to skip
2. If not configured:
   - Check if the user already has API keys by listing them via `/aip api-keys list`
   - If keys exist, ask if they want to reuse one or create a new one
   - If no keys exist, guide through `/aip api-keys create`
   - Help the user browse available models via `/aip models list`
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

1. Ask the user: "Does your agent need conversation memory (to remember past messages across sessions)? If not, we can skip this step."
2. If yes:
   - Guide through `/agentbase-memory create` to create a memory store
   - Note: Memory integration into agent code will be handled in Step 6 (Customize Agent Code), after all infrastructure is in place.
3. If no: skip
4. Update state: `wizard_step: 4`, `memory_id` (if created)

---

## Step 5/9: Set Up Identity & External Auth (Optional)

**Goal**: Register the agent identity and configure outbound authentication for external APIs.

> **When is this step needed?** Only if your agent calls external services that require authentication (e.g., third-party APIs, databases with credentials). The AgentBase Runtime automatically provisions an identity for basic deployments — you only need an explicit identity when using outbound auth features like `apikey retrieve-key`, `delegated request-key`, or `oauth2 m2m-token`.

1. Ask the user: "Does your agent need to call any external APIs that require authentication (e.g., third-party services, databases)? If not, we can skip this step — the runtime will auto-provision an identity for your agent."

2. **If yes — Set up Identity first**, then Auth:

   a. **Identity**: List existing identities and let the user pick one or create a new one:
      - **Always list existing identities first** by calling the Identity API:
        ```bash
        curl -s "https://agentbase.api.vngcloud.vn/identity/api/v1/agent-identities?page=0&size=100" \
          -H "Authorization: Bearer $TOKEN"
        ```
      - Check state for a previously configured identity in `.agentbase-state.json` or `.greennode.json`
      - If a name is found AND it exists in the list, inform the user and ask if they want to keep it, pick a different one, or create a new one
      - If creating a new identity, collect parameters (name, description, return URLs) with user confirmation before creating via `/agentbase-identity`
      - Update `.greennode.json` with the `agent_identity` value

   b. **External Auth**: Guide through `/agentbase-auth` to store API keys or configure OAuth2 providers on the identity. Help set up each external service the user needs.

3. **If no**: skip — the runtime will auto-provision an identity during deployment.
4. Update state: `wizard_step: 5`, `agent_identity` (if created)

---

## Step 6/9: Customize Agent Code

**Goal**: Help the user customize their agent's logic — now that all infrastructure (LLM, memory, identity, auth) is configured.

1. Ask the user: "What should your agent do? Describe its purpose and I can help you customize `main.py`. Or if you prefer to code it yourself later, we can skip this step."
2. If the user describes what the agent should do:
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

1. **Validate project structure**: Invoke `/agentbase-test validate` to run static code analysis (Dockerfile, health endpoint, requirements, .dockerignore checks). Report any issues and help fix them.
2. If validation passes, offer to **run locally**:
   - Ask: "Would you like to test the agent locally before deploying?"
   - If yes: invoke `/agentbase-test local` to start the server and run contract tests
   - If local tests pass, offer to **build and test in Docker**:
     invoke `/agentbase-test docker` to build the image and run contract tests in a container
3. The agent must pass at least the validation step before proceeding to deployment
4. Update state: `wizard_step: 7`

---

## Step 8/9: Deploy

**Goal**: Build, push, and deploy the agent to AgentBase Runtime.

1. Invoke `/agentbase-deploy` logic, which handles:
   - Building the Docker image
   - Setting up vCR registry if needed (via `/vcr`)
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
