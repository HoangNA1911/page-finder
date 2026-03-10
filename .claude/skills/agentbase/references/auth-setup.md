# AgentBase Authentication Setup

## Credential Discovery

Look for IAM credentials in the following order:

1. **Environment variables**: `GREENNODE_CLIENT_ID` and `GREENNODE_CLIENT_SECRET`
2. **Config file**: `.greennode.json` in the **current working directory only** (do NOT search recursively or look outside the current directory). The file should contain `client_id` and `client_secret` fields.

## If Credentials Are Not Found

Present the user with two numbered options and wait for their explicit choice before proceeding:

1. **Auto create IAM Service Account** — follows the "Automated IAM Service Account Setup" flow in the `/agentbase` skill reference.
2. **I already have credentials / create manually** — provide existing `client_id` and `client_secret`, or create one manually at https://iam.console.vngcloud.vn/service-accounts

If the user chooses option 1, confirm once more before starting the setup flow.

## Token Fetching (with Caching)

The SDK auto-loads credentials from env vars or `.greennode.json`. For curl-based API calls, use the shared `get_token.sh` script.

### Token script — `scripts/get_token.sh`

A standalone script at `.claude/skills/agentbase/scripts/get_token.sh` that handles credential loading, token caching, and JWT-based expiry validation. No function definition needed — just call it.

### Usage

```bash
TOKEN=$(bash .claude/skills/agentbase/scripts/get_token.sh)
curl -s -X GET "https://agentbase.api.vngcloud.vn/..." \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

### Handling 401 (token expired)

Force a fresh token (bypasses cache):

```bash
TOKEN=$(bash .claude/skills/agentbase/scripts/get_token.sh --force)
```

### Rules for token management

- **ALWAYS** use `TOKEN=$(bash .claude/skills/agentbase/scripts/get_token.sh)` before making API calls. **NEVER** fetch a token with inline curl.
- The cache file `.greennode_token_cache` is shared across all skills — a token fetched by one skill is reused by others.
- On **401** responses: re-run with `--force` to bypass cache.
- Token expiry is determined by decoding the JWT `exp` claim — no hardcoded TTL.

## Token Usage

Include the token in the `Authorization` header for all API calls:

```
Authorization: Bearer $TOKEN
```
