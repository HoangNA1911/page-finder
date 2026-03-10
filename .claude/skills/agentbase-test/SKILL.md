---
name: agentbase-test
description: "Test and validate GreenNode AgentBase agents locally. Use when user wants to test their agent before deploying, run a smoke test, do a pre-deploy check, verify agent works, sanity check, validate code meets runtime contract, run Docker locally, or check integration readiness. DO NOT use for deploying (use /agentbase-deploy) or monitoring deployed agents (use /agentbase-observe)."
user-invocable: true
argument-hint: "[validate|local|docker|preflight]"
---

# AgentBase Test

Test and validate GreenNode AgentBase agents before deployment.

```
/agentbase-test [validate|local|docker|preflight]
```

## Interaction Guidelines

- **Ask which mode** if the user does not specify one. Suggest `validate` as the quickest option.
- **For `local` and `docker` modes (HARD GATE)**, confirm with the user before starting the server or container. Only proceed when the user responds with an explicit confirmation keyword: `yes`, `confirm`, `ok`, `approve`, `proceed`, `go ahead`, `do it`, `lgtm`, or equivalent affirmative. If the user responds with anything else, treat it as additional input and re-present the summary for confirmation.
- **Show clear pass/fail results** with actionable fix suggestions for each check.
- **IMPORTANT:** Before constructing any API URL, read `/agentbase` skill's `references/endpoints.md` for the domain validation whitelist. Only use domains listed there.
- **If all tests pass**, suggest the next step: `/agentbase-deploy`.
- **Support `--dry-run`**: show what would be tested without actually running anything.

---

## Mode: validate

Static code analysis -- no server is started.

Run each check below and report pass/fail with actionable fix suggestions:

### Checks

1. **Dockerfile EXPOSE 8080** -- Verify `Dockerfile` exists and contains `EXPOSE 8080`.
   - Fix: Add `EXPOSE 8080` to the Dockerfile.

2. **Entrypoint file exists** -- Detect the entrypoint from the Dockerfile `CMD` or `ENTRYPOINT` directive. Default to `main.py` if not determinable. Verify the file exists and either:
   - Imports `GreenNodeAgentBaseApp` from the SDK, OR
   - Sets up Flask/FastAPI/other HTTP framework listening on port 8080.
   - Fix: Create the entrypoint file or update the Dockerfile CMD to point to the correct file.

3. **Health endpoint handler** -- Search the entrypoint (and imported modules) for a `GET /health` route that returns HTTP 200.
   - Fix: Add a `/health` endpoint returning HTTP 200. Example:
     ```python
     @app.route("/health", methods=["GET"])
     def health():
         return "OK", 200
     ```

4. **Invocation endpoint handler** -- Search for a `POST /invocations` route handler.
   - Fix: Add a `/invocations` endpoint. Example:
     ```python
     @app.route("/invocations", methods=["POST"])
     def invocations():
         data = request.get_json()
         return jsonify({"result": "ok"})
     ```

5. **`.dockerignore` exclusions** -- Verify `.dockerignore` exists and excludes: `.env`, `.greennode.json`, `__pycache__`, `.git`.
   - Fix: Create or update `.dockerignore` with the missing entries. Offer to create it automatically.

6. **`requirements.txt` includes `greennode-agentbase`** (if using SDK) -- If the entrypoint imports from `greennode_agentbase`, verify that `requirements.txt` (or `pyproject.toml`) lists the `greennode-agentbase` package.
   - Fix: Add `greennode-agentbase` to `requirements.txt`.

### Output Format

```
Validation Results
==================
[PASS] Dockerfile exposes port 8080
[PASS] Entrypoint main.py exists and imports GreenNodeAgentBaseApp
[FAIL] Health endpoint handler not found
       -> Add a GET /health route returning 200 to main.py
[PASS] Invocation endpoint handler found (POST /invocations)
[WARN] .dockerignore missing .greennode.json
       -> Add ".greennode.json" to .dockerignore
[PASS] requirements.txt includes greennode-agentbase

Result: 4/6 passed, 1 failed, 1 warning
```

---

## Mode: local

Run the agent locally and test endpoints against the runtime service contract.

### Steps

1. **Detect entrypoint** -- Parse `Dockerfile` for `CMD` or `ENTRYPOINT`. Default to `main.py`.

2. **Ensure virtual environment and dependencies** -- Check if a `venv` directory exists in the current working directory:

   **If `venv/` does NOT exist**: create it and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # macOS/Linux
   # venv\Scripts\Activate.ps1  # Windows PowerShell
   pip install -r requirements.txt
   ```

   **If `venv/` already exists**: activate it and verify dependencies are installed:
   ```bash
   source venv/bin/activate   # macOS/Linux
   # venv\Scripts\Activate.ps1  # Windows PowerShell
   pip install -r requirements.txt  # installs any missing packages
   ```

   **IMPORTANT**: Always use the venv Python to run the agent. All `python` and `pip` commands in subsequent steps must use the venv (e.g., `venv/bin/python` on macOS/Linux or `venv\Scripts\python` on Windows) to ensure correct dependencies are available.

3. **Confirm with user** before starting the server.

4. **Start server** in the background using the venv Python:
   ```bash
   venv/bin/python <entrypoint> &    # macOS/Linux
   # venv\Scripts\python <entrypoint> &  # Windows
   SERVER_PID=$!
   ```

5. **Poll health endpoint** -- `GET http://localhost:8080/health` with 30s timeout, retrying every 2s:
   ```bash
   for i in $(seq 1 15); do
     STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health 2>/dev/null)
     if [ "$STATUS" = "200" ]; then echo "Health OK"; break; fi
     sleep 2
   done
   ```

6. **Run contract tests**:

   | Test | Request | Expected |
   |------|---------|----------|
   | Health | `GET /health` | HTTP 200 |
   | Invocation (valid) | `POST /invocations` with `{"message": "test"}` | HTTP 200 with response body |
   | Invocation (empty) | `POST /invocations` with `{}` | No crash (4xx OK, 5xx is warning) |
   | Invocation (missing memory headers) | `POST /invocations` without User-Id/Session-Id headers (only if agent uses memory) | Error response indicating missing headers |

   **Important**: If the agent uses AgentBase Memory (detected by `AgentBaseMemoryEvents` or `MemoryClient` imports), **always include** `X-GreenNode-AgentBase-User-Id` and `X-GreenNode-AgentBase-Session-Id` headers in test requests. Without these headers, memory-enabled agents will return an error.

   ```bash
   # Health
   curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health

   # Invocation (valid) — include memory headers if agent uses memory
   curl -s -w "\n%{http_code}" -X POST http://localhost:8080/invocations \
     -H "Content-Type: application/json" \
     -H "X-GreenNode-AgentBase-User-Id: test-user" \
     -H "X-GreenNode-AgentBase-Session-Id: test-session" \
     -d '{"message": "test"}'

   # Invocation (empty body)
   curl -s -w "\n%{http_code}" -X POST http://localhost:8080/invocations \
     -H "Content-Type: application/json" \
     -H "X-GreenNode-AgentBase-User-Id: test-user" \
     -H "X-GreenNode-AgentBase-Session-Id: test-session" \
     -d '{}'
   ```

7. **Show test results summary**.

8. **Stop server**:
   ```bash
   kill $SERVER_PID 2>/dev/null
   ```

9. **If server crashes**, capture and show stderr output to help the user debug.

### Output Format

```
Local Test Results
==================
Server started (PID 12345)
Health endpoint ready after 4s

[PASS] GET /health -> 200
[PASS] POST /invocations {"message":"test"} -> 200 (response: {"result":"..."})
[WARN] POST /invocations {} -> 500 (server returned error, but did not crash)

Result: 2/3 passed, 0 failed, 1 warning
Server stopped.
```

---

## Mode: docker

Build and run the agent in a Docker container, then test endpoints.

### Steps

1. **Verify Docker daemon** is running:
   ```bash
   docker info >/dev/null 2>&1 || echo "Docker is not running"
   ```

2. **Determine project name** -- Use the current directory name as the project name, or ask the user.

3. **Build image**:
   ```bash
   docker build --platform linux/amd64 -t {project-name}:test .
   ```

4. **Confirm with user** before starting the container.

5. **Run container**:
   ```bash
   docker run -d -p 8080:8080 --env-file .env --name {project-name}-test {project-name}:test
   ```
   - If `.env` does not exist, omit `--env-file .env`.
   - If port 8080 is already in use, detect and report the conflict.

6. **Wait for container healthy** -- Poll `GET http://localhost:8080/health` with 60s timeout, retrying every 2s:
   ```bash
   for i in $(seq 1 30); do
     STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health 2>/dev/null)
     if [ "$STATUS" = "200" ]; then echo "Container healthy"; break; fi
     # Check if container is still running
     if ! docker ps -q -f name={project-name}-test | grep -q .; then
       echo "Container exited unexpectedly"
       docker logs {project-name}-test
       break
     fi
     sleep 2
   done
   ```

7. **Run contract tests** -- Same tests as `local` mode (health, invocation valid, invocation empty).

8. **Show container logs** if tests fail or container crashes:
   ```bash
   docker logs {project-name}-test
   ```

9. **Cleanup**:
   ```bash
   docker stop {project-name}-test 2>/dev/null
   docker rm {project-name}-test 2>/dev/null
   ```

10. **Report results**.

### Output Format

```
Docker Test Results
===================
Image built: {project-name}:test (linux/amd64)
Container started: {project-name}-test
Health endpoint ready after 8s

[PASS] GET /health -> 200
[PASS] POST /invocations {"message":"test"} -> 200
[PASS] POST /invocations {} -> 400 (graceful error)

Result: 3/3 passed
Container stopped and removed.
```

---

## Mode: preflight

Integration readiness check -- verifies that platform resources referenced in the agent code are properly configured. Requires IAM credentials.

### Prerequisites

Look for credentials in env vars `GREENNODE_CLIENT_ID` / `GREENNODE_CLIENT_SECRET` or `.greennode.json` in the **current working directory only** (do NOT search recursively or look outside the current directory). If credentials are not found, present the user with two options:
1. **Auto create** -- run the "Automated IAM Service Account Setup" flow from the `/agentbase` skill (after confirming with the user)
2. **I already have / create manually** -- user provides existing `client_id` and `client_secret`, or creates one manually at https://iam.console.vngcloud.vn/service-accounts

Do NOT proceed without letting the user choose.

### Steps

1. **Obtain IAM token**: See `/agentbase` reference skill for IAM authentication setup (client_id/client_secret → Bearer token flow).

2. **Scan agent code** for SDK usage patterns. Check the entrypoint and imported modules for:
   - `agentbase-memory` SDK usage (e.g., `MemoryClient`, `AgentBaseMemoryEvents`; long-term memory uses `MemoryClient` tool-based approach)
   - `agentbase-identity` usage (e.g., `AgentIdentity`, `GREENNODE_AGENT_IDENTITY`)
   - `@requires_api_key` decorator or `AuthProvider` usage
   - AIP model usage (e.g., `ChatOpenAI` with `agentbase` or `aip` base URL, `AIPClient`)

3. **Run integration checks** based on detected usage:

   **Memory check** (if `agentbase-memory` detected):
   ```bash
   curl -s "https://agentbase.api.vngcloud.vn/memory/memories?page=1&size=1" \
     -H "Authorization: Bearer $TOKEN"
   ```
   - Verify the API responds successfully and at least one memory store exists (or the user has access).

   **Identity check** (if `agentbase-identity` detected):
   ```bash
   curl -s "https://agentbase.api.vngcloud.vn/identity/api/v1/agent-identities?page=0&size=10" \
     -H "Authorization: Bearer $TOKEN"
   ```
   - Verify at least one agent identity exists.

   **Auth provider check** (if `@requires_api_key` detected):
   ```bash
   curl -s "https://agentbase.api.vngcloud.vn/identity/api/v1/outbound-auth/api-key-providers?page=0&size=10" \
     -H "Authorization: Bearer $TOKEN"
   ```
   - Verify at least one auth provider exists.

   **AIP check** (if AIP model usage detected):
   ```bash
   curl -s "https://aiplatform-hcm.api.vngcloud.vn/v1/api-keys" \
     -H "Authorization: Bearer $TOKEN"
   ```
   - Verify at least one API key exists and models are enabled.

4. **Report readiness matrix**.

### Output Format

```
Preflight Check Results
=======================
IAM credentials: OK (token obtained)

Detected integrations:
  agentbase-memory .... found (AgentBaseMemoryEvents in main.py)
  agentbase-identity .. found (agent_identity in main.py)
  @requires_api_key ... not detected
  AIP models ......... found (ChatOpenAI with aip base_url)

Readiness:
  [PASS] Memory service: accessible, 2 memory stores found
  [FAIL] Identity: no agent identities registered
         -> Run /agentbase-identity to register your agent
  [SKIP] Auth providers: not used by this agent
  [PASS] AIP: API key found, 3 models enabled

Result: 2/3 ready, 1 not configured
```

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Port 8080 already in use | Another process is using the port | Run `lsof -i :8080` to find the process, then `kill <PID>` or use a different port |
| Docker not running | Docker daemon is stopped | Start Docker Desktop or run `sudo systemctl start docker` |
| `ModuleNotFoundError` on local start | Missing dependencies or not using venv | Ensure `venv` exists (`python3 -m venv venv`), activate it (`source venv/bin/activate`), then run `pip install -r requirements.txt` |
| Container exits immediately | Crash on startup | Run `docker logs {container-name}` to see the error |
| Health endpoint timeout | Server takes too long to start or is not binding to 0.0.0.0:8080 | Ensure the server binds to `0.0.0.0` (not `127.0.0.1`) and port `8080` |
| `.env` file not found (docker mode) | No `.env` in project root | Create `.env` or omit env vars if not needed. The `--env-file` flag is skipped if `.env` is absent |
| IAM token fails (preflight) | Expired or invalid IAM token | Re-check `GREENNODE_CLIENT_ID` / `GREENNODE_CLIENT_SECRET` or regenerate at https://iam.console.vngcloud.vn/service-accounts |
| `docker build` fails on Apple Silicon | Platform mismatch | Use `--platform linux/amd64` (already included in docker mode) |
| `curl: command not found` | curl not installed | Install curl: `brew install curl` (macOS) or `apt install curl` (Linux) |
| Permission denied on Docker socket | User not in docker group | Run `sudo usermod -aG docker $USER` and restart terminal, or use `sudo docker` |
