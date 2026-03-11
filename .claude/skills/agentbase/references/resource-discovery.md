# Resource Discovery Reference

Shared reference for discovering all AgentBase resources across services. Used by `/agentbase-status` and `/agentbase-teardown`.

## Authentication

Get an IAM bearer token first (see `references/auth-setup.md`).

## Discovery API Calls

Run all of these in parallel to fetch resources across all services:

```bash
# Agent Identities (Identity Service — 0-indexed)
curl -s "https://agentbase.api.vngcloud.vn/identity/api/v1/agent-identities?page=0&size=100" \
  -H "Authorization: Bearer $TOKEN"

# API Key Providers (Identity Service — 0-indexed)
curl -s "https://agentbase.api.vngcloud.vn/identity/api/v1/outbound-auth/api-key-providers?page=0&size=100" \
  -H "Authorization: Bearer $TOKEN"

# Delegated API Key Providers (Identity Service — 0-indexed)
curl -s "https://agentbase.api.vngcloud.vn/identity/api/v1/outbound-auth/delegated-api-key-providers?page=0&size=100" \
  -H "Authorization: Bearer $TOKEN"

# OAuth2 Providers (Identity Service — 0-indexed)
curl -s "https://agentbase.api.vngcloud.vn/identity/api/v1/outbound-auth/oauth2-providers?page=0&size=100" \
  -H "Authorization: Bearer $TOKEN"

# Runtimes (Runtime Service — 1-indexed)
curl -s "https://agentbase.api.vngcloud.vn/runtime/agent-runtimes?page=1&size=100" \
  -H "Authorization: Bearer $TOKEN"

# Memories (Memory Service — 1-indexed)
curl -s "https://agentbase.api.vngcloud.vn/memory/memories?page=1&size=100" \
  -H "Authorization: Bearer $TOKEN"

# AIP API Keys (AI Platform — 1-indexed)
curl -s "https://aiplatform-hcm.api.vngcloud.vn/v1/api-keys?page=1&size=100" \
  -H "Authorization: Bearer $TOKEN"

# vCR Repositories (Container Registry — 1-indexed)
curl -s "https://vcr.api.vngcloud.vn/v1/repository?page=1&size=100" \
  -H "Authorization: Bearer $TOKEN"
```

## Service Summary

| Service | API | Base URL | Pagination | Response Items Field |
|---------|-----|----------|------------|---------------------|
| Agent Identities | `GET /api/v1/agent-identities?page=0&size=100` | `https://agentbase.api.vngcloud.vn/identity` | 0-indexed | `.content` |
| API Key Providers | `GET /api/v1/outbound-auth/api-key-providers?page=0&size=100` | `https://agentbase.api.vngcloud.vn/identity` | 0-indexed | `.content` |
| Delegated Providers | `GET /api/v1/outbound-auth/delegated-api-key-providers?page=0&size=100` | `https://agentbase.api.vngcloud.vn/identity` | 0-indexed | `.content` |
| OAuth2 Providers | `GET /api/v1/outbound-auth/oauth2-providers?page=0&size=100` | `https://agentbase.api.vngcloud.vn/identity` | 0-indexed | `.content` |
| Runtimes | `GET /agent-runtimes?page=1&size=100` | `https://agentbase.api.vngcloud.vn/runtime` | 1-indexed | `.listData` |
| Memories | `GET /memories?page=1&size=100` | `https://agentbase.api.vngcloud.vn/memory` | 1-indexed | `.listData` |
| AIP API Keys | `GET /v1/api-keys?page=1&size=100` | `https://aiplatform-hcm.api.vngcloud.vn` | 1-indexed | `.listData` |
| vCR Repos | `GET /v1/repository?page=1&size=100` | `https://vcr.api.vngcloud.vn` | 1-indexed | `.listData` |

## Error Handling

If any individual API call fails, handle that section as an error rather than failing the entire discovery. Show `Could not fetch (error details)` for the failed section.

## Response Shape

See `references/endpoints.md` for full response shape documentation (Identity uses Spring-style `{content, totalElements}`, other services use GreenNode-style `{listData, totalItem}`).
