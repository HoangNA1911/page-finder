# Pagefinder

Chat agent API for searching a small, fixed Confluence document corpus with RAG, change tracking, and per-user document notes.

## Features

- Contextual search over configured Confluence pages
- Update detection based on Confluence page version
- Per-user reading history
- Per-user notes attached to each document
- LangChain + AgentBase Memory for conversational continuity

## Required Environment Variables

Copy `.env.example` to `.env` and fill in:

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`
- `PAGEFINDER_ENABLE_AGENTBASE_MEMORY`
- `MEMORY_ID`
- `PAGEFINDER_SOURCE_MODE`
- `CONFLUENCE_BASE_URL`
- `CONFLUENCE_EMAIL`
- `CONFLUENCE_API_TOKEN`
- `CONFLUENCE_PAGE_IDS`

Default scenario uses a shared Confluence account and a fixed list of page IDs:

```env
PAGEFINDER_SOURCE_MODE=confluence
CONFLUENCE_BASE_URL=https://your-domain.atlassian.net
CONFLUENCE_EMAIL=shared-account@company.com
CONFLUENCE_API_TOKEN=...
CONFLUENCE_PAGE_IDS=123456,789012
PAGEFINDER_ENABLE_AGENTBASE_MEMORY=false
```

For local-only testing, you can still switch back to Markdown mode:

```env
PAGEFINDER_SOURCE_MODE=markdown
PAGEFINDER_DOCS_DIR=docs
```

## API Contract

The runtime entrypoint is `POST /invocations`.

If the runtime adapter supports custom GET routes, a lightweight chat UI is also mounted at `/` and talks to `/invocations` directly from the browser.

Required headers for memory-enabled conversations:

- `X-GreenNode-AgentBase-User-Id`
- `X-GreenNode-AgentBase-Session-Id`

Example request:

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -H "X-GreenNode-AgentBase-User-Id: demo-user" \
  -H "X-GreenNode-AgentBase-Session-Id: demo-session" \
  -d '{"message":"Tìm tài liệu nói về approval flow và note lại điểm cần chú ý"}'
```

Health check:

```bash
curl http://localhost:8080/health
```

## Behavior Notes

- The agent indexes the configured Confluence page IDs by default.
- Markdown mode remains available only as a fallback for local testing.
- Notes and reading history are stored locally in `.pagefinder/`.
- The indexed corpus auto-refreshes on query when `PAGEFINDER_AUTO_SYNC_ON_QUERY=true`.
- In Confluence mode, a background job can poll for updates every 5 minutes and refresh changed pages.
- Retrieval uses local hybrid ranking: stable hashed semantic similarity + lexical recall/density + keyword/title/heading boosts.
- Chunking keeps a small paragraph overlap to reduce misses at section boundaries.
- The app automatically reindexes old pages when the local index schema changes, so retrieval quality does not drift after restart or redeploy.
- Optional tuning knobs: `PAGEFINDER_CHUNK_MAX_CHARS`, `PAGEFINDER_CHUNK_OVERLAP_PARAGRAPHS`, `PAGEFINDER_SEARCH_CANDIDATE_LIMIT`, `PAGEFINDER_BACKGROUND_SYNC_ENABLED`, `PAGEFINDER_BACKGROUND_SYNC_INTERVAL_SECONDS`.
