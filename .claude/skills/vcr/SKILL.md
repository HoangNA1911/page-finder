---
name: vcr
description: >
  Manage Docker repositories on GreenNode Container Registry (vCR). Use this skill whenever the user mentions
  vCR, GreenNode container registry, Docker registry on GreenNode, or wants to create/list/delete Docker
  repositories, manage registry credentials (robot accounts), push/pull images on vcr.vngcloud.vn,
  list images or artifacts in a vCR repository, or set up Docker login credentials for GreenNode. Also trigger
  when user mentions "container registry" in the context of GreenNode or VNG infrastructure. Do NOT trigger
  for general Docker questions unrelated to GreenNode or vCR.
argument-hint: <repos|robot-accounts|images|artifacts> [repo-name]
---

# GreenNode Container Registry (vCR) Skill

This skill helps users manage Docker container repositories on GreenNode's Container Registry service (vCR).
It covers the full lifecycle: creating repositories, setting up credentials (robot accounts), and managing images.

## Authentication & Endpoints

Read the shared auth setup reference at `/agentbase` skill's `references/auth-setup.md` for full IAM credential configuration. In brief: check for `GREENNODE_CLIENT_ID` and `GREENNODE_CLIENT_SECRET` in environment variables or `.greennode.json` in the **current working directory only** (do NOT search recursively or look outside the current directory), then use `TOKEN=$(bash .claude/skills/agentbase/scripts/get_token.sh)` to obtain a token. On 401: re-run with `--force`. Note: for vCR operations, the service account needs the **`vcrFullAccess`** policy.

**IMPORTANT:** Before constructing any API URL, read `/agentbase` skill's `references/endpoints.md` for the domain validation whitelist. Only use domains listed there.

## Interaction Guidelines

- **Guide first, act only when asked** — if the user asks "how to" do something (e.g., "how to create a docker repo"), respond with instructions and guidance only. Do NOT execute API calls or create resources unless they explicitly ask you to do it for them (e.g., "create a repo for me", "help me set it up").
- **Confirm before executing (HARD GATE)** — before performing any action (create repo, create robot account, delete, attach/detach, update), present a clear summary of what will be done (including all parameters and values) and ask the user to confirm. Do NOT auto-execute. Only proceed when the user responds with an explicit confirmation keyword: `yes`, `confirm`, `ok`, `approve`, `proceed`, `go ahead`, `do it`, `ship it`, `lgtm`, or equivalent affirmative. If the user responds with ANYTHING ELSE (parameter changes, questions, corrections, additional info, or ambiguous text), treat it as adjustment input — update the plan and re-present the full summary for confirmation again. NEVER interpret a non-confirmation response as approval. For destructive operations (delete repo, delete robot account, delete image), additionally warn that the action is irreversible.
- **Never auto-decide parameters** — when an action requires parameters (e.g., repo name, access level, quota, robot account name, permissions, duration), always ask the user for each required value. You may recommend sensible defaults or options, but never auto-select or impose values without the user's explicit agreement.
- **Present options, let user choose** — when there are multiple choices (e.g., permissions, repositories, robot accounts), list the available options and let the user pick. Do not make the choice for them.
- **Recommend sensible defaults** — suggest private access, 10 GB quota, pull+push permissions — but always let the user override and confirm before applying.
- **When creating robot accounts, always ask about permissions.** Never create a robot account without confirming which permissions the user wants.
- **Handle errors gracefully** — if an API call returns 401, remind the user to check their IAM token; if 500, suggest retrying.
- **Dry-run support**: When user requests `--dry-run` or preview, show the exact API request (method, URL, headers, payload) and explain the expected outcome WITHOUT executing. Let user review before proceeding.

## API Basics

- **Base URL**: `https://vcr.api.vngcloud.vn`
- **Auth**: `Authorization: Bearer {iam_access_token}` header on every request
- **Image path format**: `vcr.vngcloud.vn/{repoBackendName}/{imageName}:{tag}` (use the repository's `backendName` from the API, not the display name)
- **Pagination**: query params are `page` (1-indexed, first page is `page=1`) and `size` (items per page).

Always use the exact curl examples provided below as templates for API calls.

For detailed request/response schemas and field descriptions, read `references/api.md`.

## Core Capabilities

### 1. Repository Management (CRUD)

Repositories are the top-level containers that hold Docker images.

| Action | Method | Endpoint |
|--------|--------|----------|
| List repos | GET | `/v1/repository` |
| Create repo | POST | `/v1/repository` |
| Get repo by ID | GET | `/v1/repository/{repoId}` |
| Delete repo | DELETE | `/v1/repository/{repoId}` (**Before deleting**: You MUST delete all images in the repo first — the API will reject repo deletion if any images remain. Also consider exporting or noting the resource configuration, as deletion is irreversible. There is no undo.) |
| Update quota | PUT | `/v1/repository/{repoId}/quotas` |

**Curl examples:**

```bash
# List all repositories
curl -s "https://vcr.api.vngcloud.vn/v1/repository?page=1&size=50" \
  -H "Authorization: Bearer $TOKEN"

# Create a repository
curl -s -X POST "https://vcr.api.vngcloud.vn/v1/repository" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"repoName": "my-repo", "isPublic": false, "quotaLimit": 10}'

# Delete a repository (MUST delete all images first — see "Repo Deletion Prerequisite" below)
curl -s -X DELETE "https://vcr.api.vngcloud.vn/v1/repository/{repoId}" \
  -H "Authorization: Bearer $TOKEN"
```

**Repo Deletion Prerequisite — Delete All Images First:**
The vCR API **will not allow** deleting a repository that still contains images. You MUST delete every image in the repo before calling `DELETE /v1/repository/{repoId}`, otherwise the API returns an error.

Workflow:
1. List all images: `GET /v1/repository/{repoId}/images?name=&page=1&size=100`
2. For each image, delete it: `DELETE /v1/repository/{repoId}/images/delete?imageName={imageName}`
3. Paginate if `totalPage > 1` — repeat until all images are deleted
4. Only then delete the repo: `DELETE /v1/repository/{repoId}`

```bash
# Step 1: List all images in the repo
curl -s "https://vcr.api.vngcloud.vn/v1/repository/{repoId}/images?name=&page=1&size=100" \
  -H "Authorization: Bearer $TOKEN"

# Step 2: Delete each image (repeat for every imageName returned)
curl -s -X DELETE "https://vcr.api.vngcloud.vn/v1/repository/{repoId}/images/delete?imageName={imageName}" \
  -H "Authorization: Bearer $TOKEN"

# Step 3: After all images are deleted, delete the repo
curl -s -X DELETE "https://vcr.api.vngcloud.vn/v1/repository/{repoId}" \
  -H "Authorization: Bearer $TOKEN"
```

**Before creating**, always check if a repo with the same name already exists — `repoName` must be unique (the backend will reject duplicates):
```bash
curl -s "https://vcr.api.vngcloud.vn/v1/repository?name=my-repo&page=1&size=10" \
  -H "Authorization: Bearer $TOKEN"
```
If a matching repo is found in `listData`, inform the user and offer to **reuse the existing repo** instead of creating a new one. Only proceed with creation if no match is found.

When creating a repository, ask the user for:
- **Repository name** (`repoName`) — lowercase, alphanumeric and hyphens. **Must be unique** — no two repos can have the same name.
- **Access level** (`isPublic`) — **boolean**: `false` = private, `true` = public. Recommend private (`false`) for most use cases.
- **Quota limit** (`quotaLimit`) — in GB; recommend a sensible default like 10 GB and let the user adjust

### 2. Robot Accounts

Robot accounts are service accounts for Docker push/pull access, used to authenticate with the registry.

| Action | Method | Endpoint |
|--------|--------|----------|
| List robot accounts | GET | `/v1/user` |
| Create robot account | POST | `/v1/user` |
| Update robot account | PUT | `/v1/user/{repoUserId}` |
| Delete robot account | DELETE | `/v1/user/{repoUserId}` |
| Enable robot account | PUT | `/v1/user/{repoUserId}/enable` |
| Disable robot account | PUT | `/v1/user/{repoUserId}/disable` |
| Update permissions | PUT | `/v1/user/{repoUserId}/permission` |
| Refresh secret key | GET | `/v1/user/{repoUserId}/refresh` |

**Curl examples:**

```bash
# List robot accounts
curl -s "https://vcr.api.vngcloud.vn/v1/user?page=1&size=50" \
  -H "Authorization: Bearer $TOKEN"

# List available permissions (fetch before creating robot account)
curl -s "https://vcr.api.vngcloud.vn/v1/user/permissions" \
  -H "Authorization: Bearer $TOKEN"

# Create robot account with permissions for a repo
curl -s -X POST "https://vcr.api.vngcloud.vn/v1/user" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-account", "duration": 365, "permissionRequestList": [{"repoId": "REPO_UUID", "policyIdList": ["PULL_UUID", "PUSH_UUID"]}]}'
```

### 3. Permissions

Before creating a robot account, fetch the available permissions so the user can choose which ones to grant.
Returns an array of `{uuid, action}` — typical actions are things like `push`, `pull`, etc.
Always present these options to the user and ask them to select which permissions to grant.

### 4. Repository-Robot Account Attachment

Robot accounts can be attached to or detached from repositories:

| Action | Method | Endpoint |
|--------|--------|----------|
| List attached robot accounts | GET | `/v1/repository/{repoId}/user` |
| Attach robot accounts | PUT | `/v1/repository/{repoId}/attach` |
| Detach robot accounts | PUT | `/v1/repository/{repoId}/detach` |

### 5. Image & Artifact Management

| Action | Method | Endpoint |
|--------|--------|----------|
| List images | GET | `/v1/repository/{repoId}/images?name=&page=1&size=10` |
| Get image detail | GET | `/v1/repository/{repoId}/images/detail?imageName=xxx` |
| Delete image | DELETE | `/v1/repository/{repoId}/images/delete?imageName=xxx` |
| List artifacts | GET | `/v1/repository/{repoId}/images/artifacts?imageName=xxx&name=&page=1&size=10` |
| Delete artifact | DELETE | `/v1/repository/{repoId}/images/artifacts/delete?imageName=xxx&digest=xxx` |

> **Important**: The `name=` query parameter must always be present in List Images and List Artifacts requests (even as empty string), otherwise the API returns 500. Pagination is 1-based (`page=1` is the first page; `page=0` returns 400).

**Curl examples:**

```bash
# List images in a repository (name= must be present, even empty)
curl -s "https://vcr.api.vngcloud.vn/v1/repository/{repoId}/images?name=&page=1&size=10" \
  -H "Authorization: Bearer $TOKEN"

# List artifacts for a specific image
curl -s "https://vcr.api.vngcloud.vn/v1/repository/{repoId}/images/artifacts?imageName=my-image&name=&page=1&size=10" \
  -H "Authorization: Bearer $TOKEN"
```

## Key Workflow: Create a Robot Account for a Repository

This is the most common end-to-end workflow. Follow these steps in order:

### Step 1: Identify the repository
- If the user specifies a repo name or ID, use it directly.
- If not, call `GET /v1/repository` to list repositories and help the user pick one.
- If no repository exists yet, offer to create one first. **Before creating**, always check for existing repos with the same name (see Section 1 above) — `repoName` must be unique.
- Note: the repository's `backendName` field is the actual repo name used in the Docker image path (`vcr.vngcloud.vn/{backendName}/{imageName}:{tag}`).

### Step 2: Fetch and present permissions
- Call `GET /v1/user/permissions` to get the list of available permissions.
- Present them to the user in a readable format (e.g., a numbered list showing each action).
- **Recommend `pull` + `push`** as the default — this covers most use cases and avoids issues with the "all" permission option (see Known API Quirks).
- Ask the user which permissions they want to grant, but default to pull + push if they don't have a preference.

### Step 3: Create the robot account
- Ask for an account name (and optionally description, duration in days).
- Call `POST /v1/user` with the body:
  ```json
  {
    "name": "chosen-name",
    "description": "optional description",
    "duration": 365,
    "permissionRequestList": [
      {
        "repoId": "the-repo-uuid",
        "policyIdList": ["permission-uuid-1", "permission-uuid-2"]
      }
    ]
  }
  ```
- The response contains `{ "secretKey": "..." }` — this is the **password**. Save it immediately as it cannot be retrieved again.

### Step 4: Retrieve the full username
- Call `GET /v1/user` to list all robot accounts.
- Find the robot account whose `backendName` ends with the name you just created.
- The `backendName` has the format `{prefix}-{chosen-name}`, where `{prefix}` is automatically prepended by the system.
- This full `backendName` (e.g., `109072-my-account`) is the **username** for Docker login.

### Step 5: Save credentials and guide the user
- Save credentials to `.vcr-credentials.json`:
  ```json
  {
    "username": "the-robot-account-backendName",
    "password": "the-secret-key",
    "registry": "vcr.vngcloud.vn",
    "repository": "the-repo-backendName"
  }
  ```
- **Security**: Ensure `.vcr-credentials.json` is in `.gitignore` to prevent credential leaks. If a `.gitignore` exists, add the entry; if not, warn the user to add it manually.
- Tell the user the file path and show them how to use the credentials (use the repo's `backendName` as `{repoBackendName}`):
  ```bash
  # Login to vCR
  docker login vcr.vngcloud.vn -u {username} -p {password}

  # Tag and push an image
  docker tag myimage:latest vcr.vngcloud.vn/{repoBackendName}/{imageName}:{tag}
  docker push vcr.vngcloud.vn/{repoBackendName}/{imageName}:{tag}

  # Pull an image
  docker pull vcr.vngcloud.vn/{repoBackendName}/{imageName}:{tag}
  ```

## Docker Login Verification (Before Push)

Before pushing an image, always verify Docker is logged in with the correct host and username. This prevents confusing "denied" or "unauthorized" errors mid-push.

### Check current login status

Verify Docker is logged in to vCR by attempting to pull a nonexistent image. This method works across all platforms and credential helpers without triggering OS-level privacy prompts:

```bash
docker pull vcr.vngcloud.vn/{repoBackendName}/nonexistent:test 2>&1
```

- **"not found"** or **"manifest unknown"** → Auth is working, Docker is logged in.
- **"unauthorized"** or **"denied"** → Docker is **not logged in** to vCR. Run `docker login vcr.vngcloud.vn` first.

### Verify the username matches the robot account

If Docker is logged in but pushes still fail with "denied", the logged-in username may not match the robot account. Re-login with the correct credentials:

```bash
docker login vcr.vngcloud.vn -u {robotAccount.backendName} -p {secretKey}
```

Then re-run the pull verification above to confirm auth works.

### Quick verification checklist

Before running `docker push`:
- [ ] `docker pull vcr.vngcloud.vn/{repoBackendName}/nonexistent:test` returns "not found" (not "unauthorized")
- [ ] Logged-in username is the full robot account `backendName` (e.g., `109072-my-account`)
- [ ] Image is tagged with the full path: `vcr.vngcloud.vn/{repoBackendName}/{imageName}:{tag}`

## Known API Quirks

- **Repository names must be unique** — creating a repo with a `repoName` that already exists will fail. Always check for existing repos before creating. The system-generated `backendName` is also unique and derived from `repoName`.
- **Pagination is 1-based** — always use `page=1` as the first page. `page=0` returns 400.
- **Re-attach after detach is broken** — detaching a robot account then re-attaching it to the same repo returns 500 (backend bug). **Workaround**: use `PUT /v1/user/{repoUserId}/permission` to update repo access instead of detach/attach.
- **`name=` is required for image/artifact list** — `GET .../images` and `GET .../artifacts` require the `name` query parameter to be present (even as empty string `name=`), otherwise returns 500.
- **Repo deletion requires empty repo** — you MUST delete all images in a repository before deleting the repo itself. The API will reject `DELETE /v1/repository/{repoId}` if any images remain. List images with `GET /v1/repository/{repoId}/images?name=&page=1&size=100`, delete each one, then delete the repo.
- **"all" permission does not work** — when creating a robot account, do NOT use an "all permissions" shortcut. Always grant specific permissions (`pull` + `push`). The "all" option appears to be broken on the backend.

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| 401 Unauthorized | Expired or invalid IAM token | Re-obtain token with valid `client_id`/`client_secret` |
| 400 Bad Request on list images | Missing `name=` query param | Always include `name=` (even empty) in image/artifact list requests |
| 400 Bad Request on pagination | Using `page=0` | Pagination is 1-based; use `page=1` for the first page |
| 500 on re-attach robot account | Backend bug on detach/re-attach | Use `PUT /v1/user/{id}/permission` to update access instead |
| Repo deletion fails (not empty) | Repo still contains images | Delete all images first (`DELETE /v1/repository/{repoId}/images/delete?imageName=...` for each image), then retry repo deletion |
| Repo creation fails (duplicate) | `repoName` already exists | List repos with `GET /v1/repository?name=...` and reuse the existing repo |
| Docker push denied | Robot account lacks push permission | Check robot account permissions via `GET /v1/user/permissions` |
| Docker login fails | Wrong username format | Use the full `backendName` (e.g., `109072-my-account`), not just the chosen name |
| Docker push unauthorized | Logged in with wrong account | Run the Docker Login Verification steps above to check host and username |
| Docker push unauthorized | Credential helper overrides login | Re-login explicitly with `docker login vcr.vngcloud.vn -u <username> -p <password>` |

