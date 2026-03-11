---
name: agentbase-init
description: Scaffold a new AI agent project (files only). Use ONLY when user wants the project skeleton without the full guided wizard. Creates main.py, Dockerfile, requirements.txt with optional LangChain or LangGraph integration. Even when a framework is mentioned (LangChain, LangGraph), use this skill if the user ONLY asks for project setup/scaffolding without testing, deployment, or other lifecycle steps. If the user request includes testing, deployment, or multi-step goals alongside creation, use /agentbase-wizard instead. Trigger phrases: "new project", "create project", "init project", "scaffold project", "set up project", "start new project", "project template", "boilerplate code", "create agent boilerplate", "init agent", "scaffold agent", "start fresh", "set up agent code", "set up a new agent project". DO NOT use for registering the agent (use /agentbase-identity) or deploying (use /agentbase-deploy).
argument-hint: [project-name] [--langchain|--langgraph]
user-invocable: true
---

# Scaffold a New GreenNode AgentBase Agent Project

You are scaffolding a new GreenNode AgentBase agent project. Follow these steps precisely.

## Interaction Guidelines

- **Guide first, act only when asked** — if the user asks "how to" scaffold or set up an agent project, respond with instructions and guidance only. Do NOT create files or directories unless they explicitly ask you to do it for them (e.g., "create a new agent project", "scaffold it for me").
- **Confirm before executing (HARD GATE)** — before creating the project, present a summary of all choices (project name, framework, directory location) and ask the user to confirm. Do NOT auto-execute. Only proceed when the user responds with an explicit confirmation keyword: `yes`, `confirm`, `ok`, `approve`, `proceed`, `go ahead`, `do it`, `lgtm`, or equivalent affirmative. If the user responds with ANYTHING ELSE (parameter changes, questions, corrections, additional info, or ambiguous text), treat it as adjustment input — update the summary and re-present for confirmation again. NEVER interpret a non-confirmation response as approval.
- **Never auto-decide parameters** — when a choice is required (e.g., project name, framework type), always ask the user. You may recommend options, but never auto-select or impose values without the user's explicit agreement.
- **Present options, let user choose** — when there are multiple choices (e.g., Basic/LangChain/LangGraph), list the available options with descriptions and let the user pick. Do not make the choice for them.

## Step 1: Gather Input

- **Project name**: Use `$ARGUMENTS[0]` if provided. Otherwise, ask the user for a project name (lowercase, hyphens allowed, no spaces). The project name is used for naming only (README, state file, Docker image tag) — files are created in the current working directory.
- **Python version**: Ask the user which Python version to use for the Docker base image (default: `3.13-slim`). Common options: `3.11-slim`, `3.12-slim`, `3.13-slim`. Use the chosen version in the Dockerfile `FROM` line.
- **Framework**: Check `$ARGUMENTS` for `--langchain`, `--langchain-memory`, `--langgraph`, `--langgraph-memory`, or `--custom`. If none is provided, ask the user to choose:
  - **Basic** - No AI framework, simple request/response agent (good starting point for any custom integration)
  - **LangChain** - Agent with tools via LangChain, uses GreenNode AI Platform LLM
  - **LangChain + Memory** - LangChain agent with built-in AgentBase Memory integration (short-term: checkpointer `AgentBaseMemoryEvents` + long-term: tool-based `MemoryClient` SDK with `remember`/`recall` tools)
  - **LangGraph** - Stateful graph agent with LangGraph, uses GreenNode AI Platform LLM
  - **LangGraph + Memory** - LangGraph agent with built-in AgentBase Memory integration (short-term: checkpointer `AgentBaseMemoryEvents` + long-term: tool-based `MemoryClient` SDK with `remember`/`recall` tools)
  - **Custom** - For any other framework (CrewAI, AutoGen, OpenAI SDK, etc.). Uses Basic template as the starting point — the user adds their own framework dependencies to `requirements.txt` and implements their logic in `main.py`. The only requirement is that the agent uses `greennode-agentbase` for the HTTP server (`GreenNodeAgentBaseApp`).

  **Important**: If the user mentions a specific framework that is NOT LangChain or LangGraph, recommend the **Custom** option and help them add their framework's dependencies. Do NOT force LangChain/LangGraph on users who want a different framework.

## File Boundaries

- **`.greennode.json`** — SDK-only config: credentials (`client_id`, `client_secret`) and `agent_identity`. Owned by the `greennode-agentbase` SDK. Do NOT use for project state or other non-SDK configs.
- **`.agentbase-state.json`** — wizard/tool state: `wizard_step`, `runtime_id`, `memory_id`, resource IDs, etc. Owned by the wizard and other AgentBase skills.

## Step 2: Check Current Directory

**All files are created in the current working directory (CWD).** Do NOT create a subdirectory for the project.

Before creating files, check if the CWD already contains any project files (`main.py`, `Dockerfile`, `requirements.txt`):
- If files exist, warn the user: "The current directory already contains project files (main.py, Dockerfile, etc.). Continuing will overwrite them. Proceed?"
- Only continue if the user confirms.

**CRITICAL**: Never create a subdirectory named after the project. The user is expected to already be in the correct directory (e.g., they ran `mkdir my-agent && cd my-agent` before invoking this skill). All files go directly in CWD.

## Step 3: Create Files

### 3a. `main.py` - Agent Entrypoint

```python
import os
from datetime import datetime
from dotenv import load_dotenv
from greennode_agentbase import (
    GreenNodeAgentBaseApp,
    RequestContext,
    PingStatus,
)

load_dotenv()

app = GreenNodeAgentBaseApp()


@app.entrypoint
def handler(payload: dict, context: RequestContext) -> dict:
    """Main agent entrypoint.

    Args:
        payload: JSON body from POST /invocations
        context: Request metadata (session_id, user_id, request_headers)
    """
    message = payload.get("message", "Hello")
    return {
        "status": "success",
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "session_id": context.session_id,
    }


@app.ping
def health_check() -> PingStatus:
    """Custom health check for GET /health endpoint."""
    return PingStatus.HEALTHY


if __name__ == "__main__":
    app.run(port=8080, host="0.0.0.0")
```

### 3b. `Dockerfile`

```dockerfile
FROM python:{{PYTHON_VERSION}}
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["python", "main.py"]
```

### 3c. `requirements.txt`

For a **basic** project:
```
greennode-agentbase
python-dotenv
```

For a **LangChain** project:
```
greennode-agentbase
langchain>=1.2.0,<2.0.0
langgraph>=1.0.0,<2.0.0
langchain-openai>=1.1.0,<2.0.0
python-dotenv
```

For a **LangChain + Memory** project:
```
greennode-agentbase
greennode-agent-bridge[langgraph]
langchain>=1.2.0,<2.0.0
langgraph>=1.0.0,<2.0.0
langchain-openai>=1.1.0,<2.0.0
python-dotenv
```

For a **LangGraph** project:
```
greennode-agentbase
greennode-agent-bridge[langgraph]
langgraph>=1.0.0,<2.0.0
langchain-openai>=1.1.0,<2.0.0
python-dotenv
```

For a **LangGraph + Memory** project (same as LangGraph):
```
greennode-agentbase
greennode-agent-bridge[langgraph]
langgraph>=1.0.0,<2.0.0
langchain-openai>=1.1.0,<2.0.0
python-dotenv
```

### 3d. `.greennode.json` - Configuration Template

```json
{
  "client_id": "",
  "client_secret": "",
  "agent_identity": ""
}
```

### 3e. `.env.example`

For a **basic** project:
```
GREENNODE_CLIENT_ID=
GREENNODE_CLIENT_SECRET=
GREENNODE_AGENT_IDENTITY=
```

For a **LangChain** or **LangGraph** project:
```
GREENNODE_CLIENT_ID=
GREENNODE_CLIENT_SECRET=
GREENNODE_AGENT_IDENTITY=
AIP_API_KEY=
AIP_BASE_URL=https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1
LLM_MODEL=
```

For a **LangChain + Memory** or **LangGraph + Memory** project:
```
GREENNODE_CLIENT_ID=
GREENNODE_CLIENT_SECRET=
GREENNODE_AGENT_IDENTITY=
AIP_API_KEY=
AIP_BASE_URL=https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1
LLM_MODEL=
MEMORY_ID=
```

### 3f. `.gitignore`

```
__pycache__/
*.py[cod]
.env
.greennode.json
.greennode_token_cache
.agentbase-state.json
.vcr-credentials.json
.venv/
venv/
*.egg-info/
dist/
build/
```

### 3g. `.dockerignore`

```
.venv/
venv/
__pycache__/
*.py[cod]
.env
.env.*
.greennode.json
.git/
.gitignore
*.md
```

## Step 4: LangChain Integration (only if LangChain or LangChain + Memory was chosen)

If the user chose **LangChain**, replace `main.py` with the template in `assets/langchain_main.py`. Read the file and use its contents as the `main.py` for the project.

If the user chose **LangChain + Memory**, replace `main.py` with the template in `assets/langchain_memory_main.py`. Read the file and use its contents as the `main.py` for the project. This template includes `AgentBaseMemoryEvents` (CheckpointSaver for short-term conversation persistence) and tool-based long-term memory via `MemoryClient` SDK (`remember`/`recall` tools). The user will need to create a memory via `/agentbase-memory create` and set the `MEMORY_ID` environment variable.

## Step 5: LangGraph Integration (only if LangGraph or LangGraph + Memory was chosen)

If the user chose **LangGraph**, replace `main.py` with the template in `assets/langgraph_main.py`. Read the file and use its contents as the `main.py` for the project.

If the user chose **LangGraph + Memory**, replace `main.py` with the template in `assets/langgraph_memory_main.py`. Read the file and use its contents as the `main.py` for the project. This template includes `AgentBaseMemoryEvents` (CheckpointSaver for short-term conversation persistence) and tool-based long-term memory via `MemoryClient` SDK (`remember`/`recall` tools). The user will need to create a memory via `/agentbase-memory create` and set the `MEMORY_ID` environment variable.

## Step 6: Set Up Virtual Environment

After creating all files, set up the Python virtual environment **in the current working directory** (same directory as `main.py` and `requirements.txt`).

**Detect the user's OS** and use the appropriate activation command:

```bash
python3 -m venv venv   # macOS/Linux; use "python" instead of "python3" on Windows
```

**macOS/Linux:**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell):**
```powershell
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Windows (cmd.exe):**
```cmd
venv\Scripts\activate.bat
pip install -r requirements.txt
```

- Use `python3 -m venv venv` (standard `venv`, not `.venv`); on Windows, `python` may be needed instead of `python3`
- Run `pip install -r requirements.txt` inside the activated venv
- If `pip install` fails due to a missing package or version conflict, report the error to the user and ask how to proceed
- **IMPORTANT**: Do NOT `cd` into any subdirectory. The venv must be in the same directory as the project files.

## Step 7: Create README.md

Create a `README.md` with the following content (replace `{project_name}` with actual name).

For **LangChain** or **LangGraph** projects, include the "Configure LLM" section. For **basic** projects, omit it.

```markdown
# {project_name}

A GreenNode AgentBase agent.

## Prerequisites

- Python 3.10+
- A GreenNode IAM Service Account ([create one here](https://iam.console.vngcloud.vn/service-accounts))

## Setup

1. Create and activate a virtual environment:
   ```bash
   # macOS/Linux:
   python3 -m venv venv && source venv/bin/activate

   # Windows (PowerShell):
   python -m venv venv; venv\Scripts\Activate.ps1
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure credentials for **local development** (choose one method):

   **Option A** - Environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

   **Option B** - Config file (already created):
   Edit `.greennode.json` with your `client_id` and `client_secret` from your IAM Service Account.

   > **Note**: When deployed on AgentBase Runtime, the IAM service account and Agent Identity are managed by the runtime system and automatically available to the SDK — no manual credential configuration needed in the container.

4. (Optional, for local dev) Create an Agent Identity at https://aiplatform.console.vngcloud.vn/identity and set `agent_identity` in `.greennode.json` or `GREENNODE_AGENT_IDENTITY` env var. On AgentBase Runtime, this is managed automatically by the runtime system.

## Configure LLM (LangChain/LangGraph only)

This project uses [GreenNode AI Platform](https://aiplatform.console.vngcloud.vn) as the LLM provider (OpenAI-compatible endpoint).

1. List existing API keys using `/aip api-keys list` and reuse one, or create a new one with `/aip api-keys create` if needed
2. Browse available models using `/aip models list`
3. Set in `.env`:
```
AIP_API_KEY=your-api-key
AIP_BASE_URL=https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1
LLM_MODEL=model-code-from-step-2
```

**Production**: Use `/agentbase-auth` to store your API key on the platform and inject it at runtime.

## Run Locally

```bash
python3 main.py
```

The agent starts on `http://127.0.0.1:8080`.

Test it:
```bash
curl -X POST http://127.0.0.1:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, agent!"}'
```

**Testing tips** — the SDK extracts metadata from request headers (defined in `greennode_agentbase.runtime.models`):
- If the agent uses **memory** (short-term or long-term), **both headers are required** — the agent will return an error without them:
  `-H "X-GreenNode-AgentBase-User-Id: test-user"` `-H "X-GreenNode-AgentBase-Session-Id: test-session-1"`
- If the agent uses **user identity features** (delegated API key, OAuth2 3LO token), pass a user header so credentials resolve correctly:
  `-H "X-GreenNode-AgentBase-User-Id: user-abc"`
- To pass **custom headers** to the agent, use the `X-GreenNode-AgentBase-Custom-` prefix. The SDK collects all headers with this prefix (plus `Authorization`) into `context.request_headers`:
  `-H "X-GreenNode-AgentBase-Custom-My-Key: some-value"`
  Then access in handler: `context.request_headers.get("X-GreenNode-AgentBase-Custom-My-Key")`

Health check:
```bash
curl http://127.0.0.1:8080/health
```

## Deploy to AgentBase Runtime

1. Build and push your Docker image (or use `/agentbase-deploy` skill)
2. Create a Runtime at https://aiplatform.console.vngcloud.vn/runtime
3. Create an Endpoint pointing to your Runtime

See the [AgentBase documentation](https://aiplatform.console.vngcloud.vn) for detailed deployment guides.

## Add Conversation Memory (Optional)

When you need conversation history or long-term memory, use `/agentbase-memory` to set up AgentBase Memory and integrate it with your agent.

## Project Structure

- `main.py` - Agent entrypoint with handler and health check
- `Dockerfile` - Container image definition
- `requirements.txt` - Python dependencies
- `.greennode.json` - AgentBase configuration
- `.env.example` - Environment variable template
```

## Step 8: Final Output

After creating all files, display a summary:

1. List all created files
2. Show next steps:
   - Virtual environment was created and dependencies were installed in Step 6
   - Reactivate venv when needed: `source venv/bin/activate` (macOS/Linux) or `venv\Scripts\Activate.ps1` (Windows PowerShell)
   - Configure credentials in `.greennode.json` or `.env`
   - For LangChain/LangGraph: set up LLM access with `/aip` (list existing API keys or create one, browse models)
   - `python3 main.py`
3. Mention that `/agentbase-deploy` can be used later to deploy to AgentBase Runtime
4. Mention that `/agentbase-memory` can be used later to add conversation memory when needed
5. Mention that `/agentbase-identity create` can be used to register an agent identity on the platform
6. Mention that `/agentbase-auth` can be used to store API keys securely on the platform for runtime injection
