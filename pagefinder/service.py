import hashlib
import math
from collections import Counter
from threading import Lock
from typing import Any

import requests
from bs4 import BeautifulSoup

from pagefinder import config
from pagefinder.sources import ConfluenceClient, PageSnapshot
from pagefinder.store import PagefinderStore
from pagefinder.utils import collapse_whitespace, normalize_text, tokenize, utc_now


class PagefinderService:
    def __init__(self) -> None:
        self.sync_lock = Lock()
        self.confluence_client = ConfluenceClient(
            base_url=config.CONFLUENCE_BASE_URL,
            email=config.CONFLUENCE_EMAIL,
            api_token=config.CONFLUENCE_API_TOKEN,
        )
        self.store = PagefinderStore(config.DB_PATH, config.INDEX_PATH)
        self._embedder = None
        self._embedder_ready = False

    def expand_query(self, query: str) -> list[str]:
        expansions = [query]
        normalized_query = normalize_text(query)
        tokens = tokenize(query)

        matched_terms: list[str] = []
        for canonical, variants in config.SEARCH_SYNONYMS.items():
            terms = [canonical, *variants]
            if any(term in normalized_query for term in terms):
                matched_terms.extend(terms)

        if matched_terms:
            expansions.append(f"{query} {' '.join(dict.fromkeys(matched_terms))}")

        if tokens:
            expansions.append(" ".join(tokens[:8]))

        unique_expansions: list[str] = []
        seen: set[str] = set()
        for item in expansions:
            key = normalize_text(item)
            if key and key not in seen:
                seen.add(key)
                unique_expansions.append(item)
        return unique_expansions

    def extract_sections(self, html: str) -> list[tuple[str, str]]:
        soup = BeautifulSoup(html, "html.parser")
        sections: list[tuple[str, str]] = []
        current_heading = "Overview"
        current_lines: list[str] = []

        for node in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "pre"]):
            text = collapse_whitespace(node.get_text(" ", strip=True))
            if not text:
                continue
            if node.name and node.name.startswith("h"):
                if current_lines:
                    sections.append((current_heading, "\n".join(current_lines)))
                    current_lines = []
                current_heading = text
            else:
                current_lines.append(text)

        if current_lines:
            sections.append((current_heading, "\n".join(current_lines)))
        return sections or [("Overview", collapse_whitespace(soup.get_text(" ", strip=True)))]

    def chunk_sections(self, page: PageSnapshot, max_chars: int = config.CHUNK_MAX_CHARS) -> list[dict[str, Any]]:
        chunks: list[dict[str, Any]] = []
        sections = self.extract_sections(page.body)

        for section_index, (heading, body) in enumerate(sections, start=1):
            paragraphs = [part.strip() for part in body.split("\n") if part.strip()]
            buffer: list[str] = []
            buffer_length = 0
            chunk_index = 1

            for paragraph in paragraphs:
                if buffer and buffer_length + len(paragraph) > max_chars:
                    chunk_text = "\n".join(buffer)
                    chunks.append(
                        {
                            "chunk_id": f"{page.page_id}:{section_index}:{chunk_index}",
                            "heading": heading,
                            "text": chunk_text,
                            "page_id": page.page_id,
                            "page_title": page.title,
                            "page_url": page.url,
                        }
                    )
                    chunk_index += 1
                    overlap = buffer[-config.CHUNK_OVERLAP_PARAGRAPHS :] if config.CHUNK_OVERLAP_PARAGRAPHS > 0 else []
                    buffer = overlap.copy()
                    buffer_length = sum(len(item) for item in buffer)
                buffer.append(paragraph)
                buffer_length += len(paragraph)

            if buffer:
                chunks.append(
                    {
                        "chunk_id": f"{page.page_id}:{section_index}:{chunk_index}",
                        "heading": heading,
                        "text": "\n".join(buffer),
                        "page_id": page.page_id,
                        "page_title": page.title,
                        "page_url": page.url,
                    }
                )

        return chunks

    def cheap_embedding(self, text: str, dimensions: int = config.EMBEDDING_DIM) -> list[float]:
        vector = [0.0] * dimensions
        for token in tokenize(text):
            slot = int.from_bytes(hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest(), "big") % dimensions
            vector[slot] += 1.0
        return vector

    def _get_embedder(self):
        """Lazily build the OpenAI-compatible embedder, or None when unconfigured."""
        if self._embedder_ready:
            return self._embedder
        self._embedder_ready = True
        if config.EMBEDDING_MODEL and config.EMBEDDING_API_KEY and config.EMBEDDING_BASE_URL:
            try:
                from langchain_openai import OpenAIEmbeddings

                self._embedder = OpenAIEmbeddings(
                    model=config.EMBEDDING_MODEL,
                    base_url=config.EMBEDDING_BASE_URL,
                    api_key=config.EMBEDDING_API_KEY,
                    dimensions=config.EMBEDDING_DIM,
                    chunk_size=config.EMBEDDING_BATCH_SIZE,
                )
            except Exception as error:  # noqa: BLE001 - degrade gracefully to cheap_embedding
                print(f"[pagefinder] embedding init failed, falling back to cheap_embedding: {error}")
                self._embedder = None
        return self._embedder

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        embedder = self._get_embedder()
        if embedder is not None:
            try:
                vectors = embedder.embed_documents(list(texts))
                if vectors and len(vectors[0]) == config.EMBEDDING_DIM:
                    return vectors
                print(
                    f"[pagefinder] embedding dimension mismatch (got "
                    f"{len(vectors[0]) if vectors else 0}, expected {config.EMBEDDING_DIM}); "
                    "falling back to cheap_embedding"
                )
            except Exception as error:  # noqa: BLE001 - degrade gracefully
                print(f"[pagefinder] embedding request failed, falling back to cheap_embedding: {error}")
        return [self.cheap_embedding(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        embedder = self._get_embedder()
        if embedder is not None:
            try:
                vector = embedder.embed_query(text)
                if len(vector) == config.EMBEDDING_DIM:
                    return vector
            except Exception as error:  # noqa: BLE001 - degrade gracefully
                print(f"[pagefinder] query embedding failed, falling back to cheap_embedding: {error}")
        return self.cheap_embedding(text)

    @staticmethod
    def cosine_similarity(left: list[float], right: list[float]) -> float:
        numerator = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if not left_norm or not right_norm:
            return 0.0
        return numerator / (left_norm * right_norm)

    def reindex_page(self, snapshot: PageSnapshot) -> dict[str, Any]:
        chunks = self.chunk_sections(snapshot)
        vectors = self.embed_texts([f"{chunk['heading']}\n{chunk['text']}" for chunk in chunks])
        for chunk, vector in zip(chunks, vectors):
            chunk_tokens = tokenize(chunk["text"])
            chunk["embedding"] = vector
            chunk["normalized_heading"] = normalize_text(chunk["heading"])
            chunk["normalized_text"] = normalize_text(chunk["text"])
            chunk["tokens"] = chunk_tokens
            chunk["token_count"] = len(chunk_tokens)
        return {
            "page_id": snapshot.page_id,
            "title": snapshot.title,
            "url": snapshot.url,
            "version": snapshot.version,
            "fetched_at": snapshot.fetched_at,
            "source_mode": config.SOURCE_MODE,
            "index_schema_version": config.INDEX_SCHEMA_VERSION,
            "normalized_title": normalize_text(snapshot.title),
            "chunks": chunks,
        }

    @staticmethod
    def _log_index(message: str) -> None:
        print(f"[{utc_now()}] [pagefinder.index] {message}", flush=True)

    def target_page_ids(self) -> list[str]:
        """The pages to index: explicit CONFLUENCE_PAGE_IDS unioned with every page
        discovered in CONFLUENCE_SPACE_KEYS (when configured)."""
        page_ids = list(config.CONFLUENCE_PAGE_IDS)
        if config.CONFLUENCE_SPACE_KEYS:
            for page_id in self.confluence_client.list_page_ids(config.CONFLUENCE_SPACE_KEYS):
                if page_id not in page_ids:
                    page_ids.append(page_id)
        return page_ids

    def sync_pages(self, force: bool = False) -> list[dict[str, Any]]:
        with self.sync_lock:
            synced_pages: list[dict[str, Any]] = []
            page_ids = self.target_page_ids()
            active_page_ids = set(page_ids)
            mode = "discovery" if config.CONFLUENCE_SPACE_KEYS else "manual"
            self._log_index(
                f"Sync started (force={force}, mode={mode}) for {len(active_page_ids)} page(s)."
            )
            for page_id in page_ids:
                stored_page = self.store.get_page(page_id)
                # Cheap metadata probe first: only pull the full body when the page is
                # new, its version moved, or the index schema changed.
                meta = self.confluence_client.fetch_page_meta(page_id)
                needs_reindex = (
                    force
                    or not stored_page
                    or stored_page.get("version") != meta.version
                    or stored_page.get("index_schema_version") != config.INDEX_SCHEMA_VERSION
                )
                if not needs_reindex:
                    self._log_index(
                        f"Skipped page_id={page_id} title='{meta.title}' "
                        f"(already at version={meta.version})."
                    )
                    continue
                reason = "forced" if force else ("new" if not stored_page else "version-changed")
                snapshot = self.confluence_client.fetch_page(page_id)
                page_payload = self.reindex_page(snapshot)
                self.store.upsert_page(page_payload)
                synced_pages.append(page_payload)
                # Log a changelog entry only for genuine content changes (new page or
                # version bump) — not for schema-version or forced re-indexes where the
                # underlying content is unchanged, so the per-user "what's new" stays clean.
                stored_version = stored_page.get("version") if stored_page else None
                if stored_page is None:
                    self.store.record_document_update(
                        page_id, snapshot.title, None, snapshot.version, "new"
                    )
                elif stored_version != snapshot.version:
                    self.store.record_document_update(
                        page_id, snapshot.title, stored_version, snapshot.version, "updated"
                    )
                self._log_index(
                    f"Indexed page_id={page_id} title='{snapshot.title}' version={snapshot.version} "
                    f"chunks={len(page_payload['chunks'])} reason={reason}."
                )
            self.store.prune_pages(active_page_ids, config.SOURCE_MODE)
            self._log_index(
                f"Sync finished: {len(synced_pages)} page(s) reindexed, "
                f"{len(active_page_ids)} page(s) in scope."
            )
            return synced_pages

    def ensure_index_ready(self) -> None:
        if self.store.count_pages() == 0:
            self.sync_pages(force=True)
            return
        if config.AUTO_SYNC_ON_QUERY:
            self.sync_pages(force=False)

    @staticmethod
    def keyword_overlap_score(query_tokens: list[str], text_tokens: set[str]) -> float:
        if not query_tokens or not text_tokens:
            return 0.0
        matched = sum(1 for token in query_tokens if token in text_tokens)
        return matched / len(query_tokens)

    @staticmethod
    def lexical_recall_score(query_tokens: list[str], text_token_counts: Counter[str]) -> float:
        if not query_tokens or not text_token_counts:
            return 0.0
        unique_query_tokens = list(dict.fromkeys(query_tokens))
        matched = sum(1 for token in unique_query_tokens if text_token_counts.get(token, 0) > 0)
        return matched / len(unique_query_tokens)

    @staticmethod
    def lexical_density_score(query_tokens: list[str], text_token_counts: Counter[str]) -> float:
        if not query_tokens or not text_token_counts:
            return 0.0
        total_hits = sum(min(text_token_counts.get(token, 0), 3) for token in query_tokens)
        return min(total_hits / max(len(query_tokens), 1), 1.0)

    @staticmethod
    def numeric_token_boost(query_tokens: list[str], text_tokens: set[str]) -> float:
        numeric_tokens = [token for token in query_tokens if any(character.isdigit() for character in token)]
        if not numeric_tokens:
            return 0.0
        matched = sum(1 for token in numeric_tokens if token in text_tokens)
        return matched / len(numeric_tokens)

    @staticmethod
    def phrase_match_score(normalized_query: str, normalized_text: str) -> float:
        if not normalized_query or not normalized_text:
            return 0.0
        if normalized_query in normalized_text:
            return 1.0
        query_tokens = normalized_query.split()
        if len(query_tokens) < 2:
            return 0.0
        bigrams = [" ".join(query_tokens[index : index + 2]) for index in range(len(query_tokens) - 1)]
        if any(bigram in normalized_text for bigram in bigrams):
            return 0.5
        return 0.0

    def score_chunk(
        self,
        chunk: dict[str, Any],
        query: str,
        query_variants: list[str],
        variant_vectors: list[list[float]],
    ) -> dict[str, float]:
        query_tokens = tokenize(query)
        semantic_score = max(self.cosine_similarity(vector, chunk["embedding"]) for vector in variant_vectors)

        normalized_title = chunk.get("normalized_title") or normalize_text(chunk["title"])
        normalized_heading = chunk.get("normalized_heading") or normalize_text(chunk["heading"])
        normalized_text = chunk.get("normalized_text") or normalize_text(chunk["text"])
        title_tokens = set(normalized_title.split())
        heading_tokens = set(normalized_heading.split())
        chunk_tokens = chunk.get("tokens") or tokenize(chunk["text"])
        text_tokens = set(chunk_tokens)
        text_token_counts = Counter(chunk_tokens)

        title_overlap = self.keyword_overlap_score(query_tokens, title_tokens)
        heading_overlap = self.keyword_overlap_score(query_tokens, heading_tokens)
        text_overlap = self.keyword_overlap_score(query_tokens, text_tokens)
        text_recall = self.lexical_recall_score(query_tokens, text_token_counts)
        text_density = self.lexical_density_score(query_tokens, text_token_counts)
        phrase_score = max(self.phrase_match_score(normalize_text(variant), normalized_text) for variant in query_variants)
        page_id_boost = 1.0 if chunk["page_id"] in query else 0.0
        numeric_boost = self.numeric_token_boost(query_tokens, text_tokens | heading_tokens | title_tokens)

        keyword_score = (
            (0.25 * text_overlap)
            + (0.25 * text_recall)
            + (0.15 * text_density)
            + (0.20 * heading_overlap)
            + (0.15 * title_overlap)
        )
        metadata_boost = (
            (0.15 * title_overlap)
            + (0.25 * heading_overlap)
            + (0.20 * phrase_score)
            + (0.20 * numeric_boost)
            + (0.20 * page_id_boost)
        )
        final_score = (0.42 * semantic_score) + (0.38 * keyword_score) + (0.20 * metadata_boost)

        return {
            "semantic": semantic_score,
            "keyword": keyword_score,
            "metadata": metadata_boost,
            "final": final_score,
        }

    @staticmethod
    def dedupe_and_rerank_matches(matches: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
        deduped: list[dict[str, Any]] = []
        seen_signatures: set[tuple[str, str, str]] = set()
        page_counts: dict[str, int] = {}

        for match in matches:
            signature = (match["page_id"], match["heading"], match["text"][:160])
            if signature in seen_signatures:
                continue
            if page_counts.get(match["page_id"], 0) >= 2:
                continue
            seen_signatures.add(signature)
            page_counts[match["page_id"]] = page_counts.get(match["page_id"], 0) + 1
            deduped.append(match)
            if len(deduped) >= limit:
                break

        return deduped

    @staticmethod
    def build_fts_query(query: str) -> str:
        tokens = tokenize(query)
        if not tokens:
            return ""
        # tokenize() already lowercases and strips punctuation, so every token is a
        # bare word; quoting keeps FTS5 from interpreting any of them as operators.
        return " OR ".join(f'"{token}"' for token in tokens)

    def gather_candidate_rowids(self, query: str, variant_vectors: list[list[float]]) -> list[int]:
        rowids: list[int] = []
        seen: set[int] = set()
        for vector in variant_vectors:
            for rowid in self.store.knn_chunk_rowids(vector, config.VEC_CANDIDATE_LIMIT):
                if rowid not in seen:
                    seen.add(rowid)
                    rowids.append(rowid)
        for rowid in self.store.fts_chunk_rowids(self.build_fts_query(query), config.FTS_CANDIDATE_LIMIT):
            if rowid not in seen:
                seen.add(rowid)
                rowids.append(rowid)
        return rowids

    def search_chunks(self, query: str, limit: int) -> list[dict[str, Any]]:
        self.ensure_index_ready()
        query_variants = self.expand_query(query)
        variant_vectors = [self.embed_query(variant) for variant in query_variants]

        rowids = self.gather_candidate_rowids(query, variant_vectors)
        candidates = self.store.get_chunks_for_rerank(rowids)

        matches: list[dict[str, Any]] = []
        for chunk in candidates:
            scores = self.score_chunk(chunk, query, query_variants, variant_vectors)
            matches.append(
                {
                    "score": scores["final"],
                    "semantic_score": scores["semantic"],
                    "keyword_score": scores["keyword"],
                    "metadata_score": scores["metadata"],
                    "page_id": chunk["page_id"],
                    "title": chunk["title"],
                    "url": chunk["url"],
                    "heading": chunk["heading"],
                    "text": chunk["text"],
                    "token_count": chunk.get("token_count", 0),
                }
            )
        matches.sort(
            key=lambda item: (
                item["score"],
                item["metadata_score"],
                item["keyword_score"],
                -abs(item.get("token_count", 0) - 120),
            ),
            reverse=True,
        )
        candidate_limit = max(limit * 4, config.SEARCH_CANDIDATE_LIMIT)
        return self.dedupe_and_rerank_matches(matches[:candidate_limit], limit)

    @staticmethod
    def format_source_error(error: Exception) -> str:
        if isinstance(error, requests.HTTPError):
            response = error.response
            status_code = response.status_code if response is not None else "unknown"
            return (
                "Could not read the configured Confluence content. "
                f"HTTP status: {status_code}. Please verify CONFLUENCE_BASE_URL, page IDs, and account access."
            )
        return f"Could not read the configured document source: {error}"

    def read_document_impl(self, page_id: str, focus: str = "", actor_id: str = "shared-user") -> str:
        page = self.store.get_page(page_id)
        if not page:
            self.sync_pages(force=True)
            page = self.store.get_page(page_id)
        if not page:
            return f"Page {page_id} is not available in the configured document scope."

        self.store.add_read(actor_id, page["page_id"], page["title"], focus)

        if focus:
            matches = [
                match
                for match in self.search_chunks(f"{page['title']} {focus}", config.MAX_RESULTS)
                if match["page_id"] == page_id
            ]
            if matches:
                return "\n\n".join(
                    f"[{match['heading']}]\nURL: {match['url']}\n{match['text'][:900]}" for match in matches[:3]
                )

        chunks = page.get("chunks", [])[:3]
        return "\n\n".join(f"[{chunk['heading']}]\nURL: {page['url']}\n{chunk['text'][:900]}" for chunk in chunks)

    def check_document_updates_impl(self, actor_id: str, since: str | None) -> str:
        """Report document changes recorded since the user last used the system.

        Pure local lookup: compares the user's ``last_seen`` (``since``) against the
        document version changes already recorded in the local changelog. It does NOT
        re-fetch or sync from Confluence — keeping the index current is the background
        sync job's responsibility — so this stays fast and adds no Confluence latency.
        ``since`` is the user's previous last-seen timestamp, captured before the
        current request.
        """
        if not since:
            return (
                "This looks like your first session, so there is no earlier visit to "
                "compare against yet. I'll track document updates from now on."
            )

        rows = self.store.get_updates_since(since)
        if not rows:
            return "No documents have changed since you last used the system."

        # Collapse multiple changes to the same page into its most recent entry.
        latest_by_page: dict[str, Any] = {}
        for row in rows:
            latest_by_page[row["page_id"]] = row

        lines: list[str] = []
        for row in latest_by_page.values():
            if row["change_type"] == "new":
                lines.append(f"- {row['title']} (page_id={row['page_id']}) was added.")
            else:
                lines.append(
                    f"- {row['title']} (page_id={row['page_id']}) was updated "
                    f"(version {row['old_version']} → {row['new_version']})."
                )
        header = f"{len(lines)} document(s) changed since {since}:"
        return "\n".join([header, *lines])
