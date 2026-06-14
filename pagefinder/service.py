import hashlib
import math
from collections import Counter
from html import escape
from threading import Lock
from typing import Any

import requests
from bs4 import BeautifulSoup

from pagefinder import config
from pagefinder.sources import ConfluenceClient, MarkdownClient, PageSnapshot
from pagefinder.store import PagefinderStore
from pagefinder.utils import collapse_whitespace, normalize_text, tokenize


class PagefinderService:
    def __init__(self) -> None:
        self.sync_lock = Lock()
        self.confluence_client = None
        if config.SOURCE_MODE == "confluence":
            self.confluence_client = ConfluenceClient(
                base_url=config.CONFLUENCE_BASE_URL,
                email=config.CONFLUENCE_EMAIL,
                api_token=config.CONFLUENCE_API_TOKEN,
            )
        self.markdown_client = MarkdownClient(config.DOCS_DIR)
        self.store = PagefinderStore(config.DB_PATH, config.INDEX_PATH)

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

    def markdown_to_html(self, markdown_text: str) -> str:
        html_lines: list[str] = []
        list_open = False
        for raw_line in markdown_text.splitlines():
            line = raw_line.strip()
            if not line:
                if list_open:
                    html_lines.append("</ul>")
                    list_open = False
                continue
            if line.startswith("#"):
                if list_open:
                    html_lines.append("</ul>")
                    list_open = False
                level = min(len(line) - len(line.lstrip("#")), 6)
                text = escape(line[level:].strip())
                html_lines.append(f"<h{level}>{text}</h{level}>")
                continue
            if line.startswith("- ") or line.startswith("* "):
                if not list_open:
                    html_lines.append("<ul>")
                    list_open = True
                html_lines.append(f"<li>{escape(line[2:].strip())}</li>")
                continue
            if list_open:
                html_lines.append("</ul>")
                list_open = False
            html_lines.append(f"<p>{escape(line)}</p>")
        if list_open:
            html_lines.append("</ul>")
        return "\n".join(html_lines)

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
        page_html = page.body if page.body_format == "html" else self.markdown_to_html(page.body)
        sections = self.extract_sections(page_html)

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

    def cheap_embedding(self, text: str, dimensions: int = 256) -> list[float]:
        vector = [0.0] * dimensions
        for token in tokenize(text):
            slot = int.from_bytes(hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest(), "big") % dimensions
            vector[slot] += 1.0
        return vector

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self.cheap_embedding(text) for text in texts]

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

    def sync_pages(self, force: bool = False) -> list[dict[str, Any]]:
        with self.sync_lock:
            synced_pages: list[dict[str, Any]] = []
            if config.SOURCE_MODE == "markdown":
                active_page_ids: set[str] = set()
                for snapshot in self.markdown_client.iter_pages():
                    active_page_ids.add(snapshot.page_id)
                    stored_page = self.store.get_page(snapshot.page_id)
                    needs_reindex = (
                        force
                        or not stored_page
                        or stored_page.get("version") != snapshot.version
                        or stored_page.get("index_schema_version") != config.INDEX_SCHEMA_VERSION
                    )
                    if needs_reindex:
                        page_payload = self.reindex_page(snapshot)
                        self.store.upsert_page(page_payload)
                        synced_pages.append(page_payload)
                self.store.prune_pages(active_page_ids, config.SOURCE_MODE)
                return synced_pages

            active_page_ids = set(config.CONFLUENCE_PAGE_IDS)
            for page_id in config.CONFLUENCE_PAGE_IDS:
                stored_page = self.store.get_page(page_id)
                snapshot = self.confluence_client.fetch_page(page_id)
                needs_reindex = (
                    force
                    or not stored_page
                    or stored_page.get("version") != snapshot.version
                    or stored_page.get("index_schema_version") != config.INDEX_SCHEMA_VERSION
                )
                if needs_reindex:
                    page_payload = self.reindex_page(snapshot)
                    self.store.upsert_page(page_payload)
                    synced_pages.append(page_payload)
            self.store.prune_pages(active_page_ids, config.SOURCE_MODE)
            return synced_pages

    def ensure_index_ready(self) -> None:
        if not self.store.all_pages():
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

    def score_chunk(self, page: dict[str, Any], chunk: dict[str, Any], query: str, query_variants: list[str]) -> dict[str, float]:
        query_tokens = tokenize(query)
        semantic_score = max(self.cosine_similarity(self.cheap_embedding(variant), chunk["embedding"]) for variant in query_variants)

        normalized_title = page.get("normalized_title") or normalize_text(page["title"])
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
        page_id_boost = 1.0 if page["page_id"] in query else 0.0
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

    def search_chunks(self, query: str, limit: int) -> list[dict[str, Any]]:
        self.ensure_index_ready()
        query_variants = self.expand_query(query)
        matches: list[dict[str, Any]] = []
        for page in self.store.all_pages():
            for chunk in page.get("chunks", []):
                scores = self.score_chunk(page, chunk, query, query_variants)
                matches.append(
                    {
                        "score": scores["final"],
                        "semantic_score": scores["semantic"],
                        "keyword_score": scores["keyword"],
                        "metadata_score": scores["metadata"],
                        "page_id": page["page_id"],
                        "title": page["title"],
                        "url": page["url"],
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

    def check_document_updates_impl(self) -> str:
        updates: list[str] = []
        if config.SOURCE_MODE == "markdown":
            for snapshot in self.markdown_client.iter_pages():
                indexed_page = self.store.get_page(snapshot.page_id)
                if not indexed_page:
                    updates.append(f"- {snapshot.title} is not indexed yet.")
                    continue
                indexed_version = indexed_page.get("version")
                if indexed_version != snapshot.version:
                    updates.append(f"- {snapshot.title} changed from version {indexed_version} to {snapshot.version}.")
            if not updates:
                return "No updates detected for the configured Markdown documents."
            return "\n".join(updates)

        for page_id in config.CONFLUENCE_PAGE_IDS:
            current_snapshot = self.confluence_client.fetch_page(page_id)
            indexed_page = self.store.get_page(page_id)
            if not indexed_page:
                updates.append(f"- {current_snapshot.title} is not indexed yet.")
                continue
            indexed_version = indexed_page.get("version")
            if indexed_version != current_snapshot.version:
                updates.append(
                    f"- {current_snapshot.title} changed from version {indexed_version} to {current_snapshot.version}."
                )
        if not updates:
            return "No updates detected for the configured Confluence pages."
        return "\n".join(updates)
