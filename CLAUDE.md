# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
cp .env.example .env   # fill in required vars
pip install -r requirements.txt
python main.py         # starts on port 8080
```

Confluence is the only document source. (The former local Markdown mode has been removed.)

## Architecture

Pagefinder is a RAG chat agent: a LangChain/LangGraph agent with tools that search over a locally-indexed corpus of Confluence pages.

```
HTTP /invocations
    → runtime.py   (GreenNodeAgentBaseApp + LangGraph agent)
    → service.py   (PagefinderService: search, indexing, sync)
    → store.py     (PagefinderStore: SQLite index)
    → sources.py   (ConfluenceClient)
```

**`runtime.py`** — Wires the agent. Registers tools (`search_documents`, `read_document`, `check_document_updates`, on-demand indexing tools, notes/history tools, optional memory tools), extracts `actor_id`/`thread_id` from the request, and runs the LangGraph agent. Short-circuits directly to `read_document_impl` if the request already specifies a `page_id`.

**`service.py`** — The core logic. Three main responsibilities:
1. **Indexing** (`sync_pages` → `reindex_page`): fetches pages, splits into chunks by heading/paragraph with overlap, computes embeddings, writes to the store. Each indexing run logs per page (`[pagefinder.index] ...`: sync start, indexed/skipped per page with chunk count, sync finished).
2. **Search** (`search_chunks`): expands the query via synonyms, scores every chunk with hybrid scoring, deduplicates, returns top N.
3. **Hybrid scoring** (`score_chunk`): three weighted components — *semantic* (42%, cosine on cheap embeddings), *keyword* (38%, lexical overlap/recall/density), *metadata* (20%, title/heading/phrase/numeric boost).

**`store.py`** — SQLite store in `.pagefinder/pagefinder.db`:
- `pages` + `chunks` (chunk text/metadata) + `vec_chunks` (sqlite-vec KNN) + `chunks_fts` (FTS5), all sharing the same `rowid`, hold the searchable index.
- `reading_history` holds per-user read history. **Per-user document notes are no longer stored here** — they live in AgentBase long-term memory (see `runtime.py`).
- `document_updates` is a changelog: `sync_pages` appends one row when a page is newly indexed or its version changes (not for forced/schema-only reindexes). `user_activity` holds each user's `last_seen_at`.

**"What's new?" flow** — `check_document_updates` is a **pure local lookup**: it reads the `document_updates` changelog filtered by the user's *previous* `last_seen_at` (snapshotted in `runtime.handler` before the request, passed via the `last_seen_before` configurable). It does **not** sync or re-fetch Confluence (no `ensure_index_ready`) — keeping the changelog current is the background sync job's job — so it adds no Confluence latency. The system prompt also forbids the agent from triggering a sync on these questions. `handler` advances `last_seen_at` to now at the end of every request, so the tool reports everything changed since the user's prior visit. Brand-new users (no `last_seen_at` row) get a "first session" message instead of a flood.

**On-demand indexing** — `index_documents` runs an **incremental** sync (`sync_pages(force=False)`: probe version metadata, reindex only pages whose version changed); the agent calls it when the user asks to index/refresh the corpus. `sync_confluence_pages` runs a **full forced** rebuild (`sync_pages(force=True)`, every page regardless of version). Both are ungated (any user may invoke them) and serialize on `service.sync_lock`, so concurrent calls run sequentially rather than overlapping.

**`runtime.py` notes** — `add_document_note` / `list_document_notes` persist notes in AgentBase Memory under the namespace `…/actors/{actor_id}/notes` (record text `page_id=… | title=… | <note>`). Both require `PAGEFINDER_ENABLE_AGENTBASE_MEMORY=true`; they return a disabled message otherwise.

**`background.py`** — Daemon thread that calls `sync_pages(force=False)` every `BACKGROUND_SYNC_INTERVAL_SECONDS` (gated only by `PAGEFINDER_BACKGROUND_SYNC_ENABLED`). Version metadata from Confluence determines whether a page needs reindexing.

## Embedding and Search

The system uses **no external embedding API**. `cheap_embedding()` in `service.py` produces a 256-dimensional vector by hashing each token with Blake2b and incrementing the corresponding bucket. This is fast and deterministic but not semantic — quality comes from the hybrid scoring, not the embedding alone.

`expand_query()` generates up to 3 variants (original, synonym-expanded, token-trimmed) and takes the max semantic score across all variants.

`INDEX_SCHEMA_VERSION` in `config.py` acts as a cache-buster: bumping it triggers a full reindex on next sync.

## Key Configuration

All tunables are env vars with defaults in `config.py`. The search-relevant ones:

| Var | Default | Effect |
|-----|---------|--------|
| `PAGEFINDER_CHUNK_MAX_CHARS` | 1200 | Max chars per chunk |
| `PAGEFINDER_SEARCH_CANDIDATE_LIMIT` | 25 | Candidates before dedup |
| `PAGEFINDER_MAX_RESULTS` | 5 | Results returned to caller |
| `PAGEFINDER_AUTO_SYNC_ON_QUERY` | false | Sync before each search query (off by default; `check_document_updates` never syncs regardless) |
| `PAGEFINDER_BACKGROUND_SYNC_INTERVAL_SECONDS` | 300 | Polling interval |
