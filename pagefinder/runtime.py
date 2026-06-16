import re

from langchain.agents import create_agent
from langchain.agents.middleware import before_model
from langchain_core.messages import HumanMessage, RemoveMessage
from langchain_core.tools import tool
from langgraph.config import get_config
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langchain_openai import ChatOpenAI

from greennode_agentbase import GreenNodeAgentBaseApp, PingStatus, RequestContext
from greennode_agentbase.memory import MemoryClient
from greennode_agentbase.memory.models import MemoryRecordSearchRequest
from greennode_agent_bridge import AgentBaseMemoryEvents

from pagefinder import config
from pagefinder.background import BackgroundSyncJob
from pagefinder.service import PagefinderService
from pagefinder.ui import register_ui_routes
from pagefinder.utils import (
    build_namespace,
    extract_page_ids_from_text,
    is_vietnamese,
    looks_like_list_request,
    looks_like_doc_search_request,
    looks_like_list_notes_request,
    looks_like_summary_request,
    looks_like_whats_new_request,
    strip_decorations,
    utc_now,
)

app = GreenNodeAgentBaseApp()
service = PagefinderService()
background_sync_job = BackgroundSyncJob(service)
checkpointer = AgentBaseMemoryEvents(memory_id=config.MEMORY_ID) if config.ENABLE_AGENTBASE_MEMORY else None
memory_client = MemoryClient() if config.ENABLE_AGENTBASE_MEMORY else None
llm = ChatOpenAI(model=config.LLM_MODEL, base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY)


# Dedicated LLM for diff summaries: short timeout + no retries so one slow/stuck
# call can never hang the whole "what's new" request.
summary_llm = ChatOpenAI(
    model=config.LLM_MODEL,
    base_url=config.LLM_BASE_URL,
    api_key=config.LLM_API_KEY,
    timeout=20,
    max_retries=0,
)


def _summarize_diff(title: str, diff_block: str, user_request: str = "") -> str:
    """One short sentence describing a diff, grounded strictly in it, in the SAME
    language as the user's request. Called by the tool at query time."""
    result = summary_llm.invoke(
        [
            (
                "system",
                "You summarize what changed in a document page in EXACTLY ONE short sentence, "
                "based ONLY on the provided diff (lines starting with + were added, - were removed). "
                "Reply in the SAME language as the user's request. Do not invent anything not in the "
                "diff, and do not just repeat the diff text verbatim.",
            ),
            ("human", f"User request: {user_request}\n\nPage title: {title}\n\nDiff:\n{diff_block}"),
        ]
    )
    return result.content


service.diff_summarizer = _summarize_diff
background_sync_job.start()


def get_configurable() -> dict:
    config_value = get_config()
    return config_value.get("configurable", {})


def get_actor_id() -> str:
    return get_configurable().get("actor_id", "shared-user")


def get_last_update_check_before() -> str | None:
    """The user's previous update-check timestamp, captured before this request started."""
    return get_configurable().get("last_update_check_before")


def get_user_message() -> str:
    """The current user's message, used to match the reply language for summaries."""
    return get_configurable().get("user_message", "")


def build_note_namespace(actor_id: str) -> str:
    """Dedicated long-term-memory namespace for per-user document notes."""
    return f"{build_namespace(config.MEMORY_STRATEGY_ID, actor_id)}/notes"


def _memory_records(result) -> list:
    """Normalize the SDK response (a bare list or a paginated wrapper) to a list."""
    if result is None:
        return []
    if hasattr(result, "list_data"):
        return result.list_data or []
    return list(result)


def _rec_field(row, name):
    """Read a field from a memory record that may be a dict or an SDK model object."""
    if isinstance(row, dict):
        return row.get(name)
    return getattr(row, name, None)


@tool
def remember(fact: str) -> str:
    """Store a user preference or fact for later conversations."""
    if not config.ENABLE_AGENTBASE_MEMORY or memory_client is None:
        return "AgentBase Memory is disabled in this deployment."
    namespace = build_namespace(config.MEMORY_STRATEGY_ID, get_actor_id())
    memory_client.insert_memory_records_directly(
        id=config.MEMORY_ID, namespace=namespace, request={"memoryRecords": [fact]}
    )
    return f"Remembered: {fact}"


@tool
def recall(query: str) -> str:
    """Search long-term memory for user-specific facts."""
    if not config.ENABLE_AGENTBASE_MEMORY or memory_client is None:
        return "AgentBase Memory is disabled in this deployment."
    namespace = build_namespace(config.MEMORY_STRATEGY_ID, get_actor_id())
    results = memory_client.search_memory_records(
        id=config.MEMORY_ID,
        namespace=namespace,
        request=MemoryRecordSearchRequest(query=query, limit=10),
    )
    rows = _memory_records(results)
    lines = []
    for row in rows:
        mem = _rec_field(row, "memory")
        if not mem:
            continue
        score = _rec_field(row, "score")
        lines.append(f"- {mem} (score: {score:.2f})" if isinstance(score, (int, float)) else f"- {mem}")
    if not lines:
        return "No relevant memories found."
    return "\n".join(lines)


@tool
def sync_confluence_pages() -> str:
    """Fetch the configured Confluence pages and refresh the local RAG index."""
    try:
        synced_pages = service.sync_pages(force=True)
    except Exception as error:
        return service.format_source_error(error)
    if not synced_pages:
        return "All configured Confluence pages are already up to date."
    return "\n".join(
        f"- Synced {page['title']} (page_id={page['page_id']}, version={page['version']})" for page in synced_pages
    )


@tool
def index_documents() -> str:
    """Index documents on demand (incremental): fetch the configured Confluence pages and
    reindex only those whose version changed since the last sync. Use this when the user
    asks the system to index, refresh, or update the index. For a full forced rebuild of
    every page regardless of version, use sync_confluence_pages instead."""
    try:
        synced_pages = service.sync_pages(force=False)
    except Exception as error:
        return service.format_source_error(error)
    if not synced_pages:
        return "Index is already up to date; no pages needed reindexing."
    return "\n".join(
        f"- Indexed {page['title']} (page_id={page['page_id']}, version={page['version']})"
        for page in synced_pages
    )


@tool
def check_document_updates() -> str:
    """Report which documents changed since the current user last checked for updates.

    The result may include a ```diff fenced block per changed page (added/removed
    lines). Present that block verbatim — do not rewrite or summarize away the diff.
    """
    try:
        return service.check_document_updates_impl(
            get_actor_id(), get_last_update_check_before(), get_user_message()
        )
    except Exception as error:
        return service.format_source_error(error)


@tool
def what_changed(page_id: str) -> str:
    """Show exactly what changed in a specific document (its latest content diff).

    Use when the user asks what changed / what was edited in a particular page.
    Returns a ```diff fenced block — present it verbatim; you may add ONE short
    sentence describing the change, but it must be grounded strictly in the diff.
    """
    try:
        return service.what_changed_impl(page_id, get_user_message())
    except Exception as error:
        return service.format_source_error(error)


@tool
def search_documents(query: str) -> str:
    """Search the indexed document content and return the best matching passages with citations."""
    try:
        requested_page_ids = extract_page_ids_from_text(query)
        for requested_page_id in requested_page_ids:
            page = service.store.get_page(requested_page_id)
            if not page:
                service.ensure_index_ready()
                page = service.store.get_page(requested_page_id)
            if page:
                chunks = page.get("chunks", [])[:3]
                return "\n\n".join(
                    f"[{chunk['heading']}]\npage_id={page['page_id']}\nURL: {page['url']}\n{chunk['text'][:900]}"
                    for chunk in chunks
                )

        matches = service.search_chunks(query, config.MAX_RESULTS)
    except Exception as error:
        return service.format_source_error(error)
    if not matches:
        return "No matching passages found in the indexed document set."
    lines = []
    for index, match in enumerate(matches, start=1):
        excerpt = match["text"][:500]
        lines.append(
            f"{index}. [{match['title']}] page_id={match['page_id']} heading={match['heading']} score={match['score']:.3f}\n"
            f"URL: {match['url']}\n"
            f"Excerpt: {excerpt}"
        )
    return "\n\n".join(lines)


@tool
def read_document(page_id: str, focus: str = "") -> str:
    """Read a specific indexed document, optionally focused on a sub-topic."""
    try:
        return service.read_document_impl(page_id, focus, actor_id=get_actor_id())
    except Exception as error:
        return service.format_source_error(error)


@tool
def add_document_note(page_id: str, note: str) -> str:
    """Save a personal note for a specific document page (stored in AgentBase long-term memory)."""
    if not config.ENABLE_AGENTBASE_MEMORY or memory_client is None:
        return "AgentBase Memory is disabled in this deployment; cannot save notes."
    actor_id = get_actor_id()
    page = service.store.get_page(page_id)
    if not page:
        return f"Page {page_id} is not indexed yet. Sync or read it first."
    namespace = build_note_namespace(actor_id)
    record = f"page_id={page_id} | title={page['title']} | {note}"
    memory_client.insert_memory_records_directly(
        id=config.MEMORY_ID, namespace=namespace, request={"memoryRecords": [record]}
    )
    return f"Saved note for {page['title']} (page_id={page_id})."


@tool
def list_document_notes(page_id: str = "") -> str:
    """List saved personal notes, optionally filtered to one document page (from AgentBase memory).
    Returns a ready-to-display markdown bullet list (title linked to URL, page_id hidden) — relay it AS-IS."""
    return _list_notes_text(get_actor_id(), get_user_message(), page_id)


def _parse_note_record(mem: str) -> tuple[str, str, str]:
    """Split a stored note record 'page_id=X | title=Y | <note>' into (page_id, title, note)."""
    parts = mem.split(" | ", 2)
    pid = parts[0][len("page_id="):] if parts[0].startswith("page_id=") else ""
    title = parts[1][len("title="):] if len(parts) > 1 and parts[1].startswith("title=") else ""
    note = parts[2] if len(parts) > 2 else ""
    return pid, title, note


def _list_notes_text(actor_id: str, message: str = "", page_id: str = "") -> str:
    """Build a ready-to-display markdown list of the user's saved notes — each as
    '- [title](url) — note', page_id hidden, in the user's language. Used by both the
    tool and the handler fast-path so the listing never depends on the LLM."""
    vi = is_vietnamese(message)
    if not config.ENABLE_AGENTBASE_MEMORY or memory_client is None:
        return (
            "Tính năng ghi chú cá nhân đang tắt trong hệ thống này."
            if vi else "AgentBase Memory is disabled in this deployment; cannot list notes."
        )
    namespace = build_note_namespace(actor_id)
    records = _memory_records(memory_client.list_memory_records(id=config.MEMORY_ID, namespace=namespace))
    prefix = f"page_id={page_id} |" if page_id else ""
    lines = []
    for row in records:
        mem = _rec_field(row, "memory")
        if not mem or (prefix and not mem.startswith(prefix)):
            continue
        pid, title, note = _parse_note_record(mem)
        page = service.store.get_page(pid) if pid else None
        url = page.get("url") if page else None
        label = (title or pid).replace("[", "(").replace("]", ")")
        head = f"[{label}]({url})" if url else label
        lines.append(f"- {head} — {note}" if note else f"- {head}")
    if not lines:
        return "Bạn chưa lưu ghi chú nào." if vi else "No saved notes yet."
    header = "Các ghi chú đã lưu của bạn:" if vi else "Your saved notes:"
    return header + "\n" + "\n".join(lines)


def _find_note_matches(page_id: str, note_text: str) -> list[tuple[str, str]]:
    """Return [(record_id, memory_text)] of the current user's notes matching the given
    page_id and/or a case-insensitive snippet of the note text."""
    namespace = build_note_namespace(get_actor_id())
    records = _memory_records(memory_client.list_memory_records(id=config.MEMORY_ID, namespace=namespace))
    matches = []
    for row in records:
        mem = _rec_field(row, "memory")
        rid = _rec_field(row, "id")
        if not mem or not rid:
            continue
        if page_id and not mem.startswith(f"page_id={page_id} |"):
            continue
        if note_text and note_text.lower() not in mem.lower():
            continue
        matches.append((rid, mem))
    return matches


@tool
def delete_document_note(page_id: str = "", note_text: str = "") -> str:
    """Delete a saved personal note. Identify it by its page_id and/or a snippet of the
    note text. Call list_document_notes first to see existing notes. If several notes
    match, they are listed back so you can narrow down with a more specific note_text."""
    if not config.ENABLE_AGENTBASE_MEMORY or memory_client is None:
        return "AgentBase Memory is disabled in this deployment; cannot delete notes."
    if not page_id and not note_text:
        return "Specify which note to delete (a page_id and/or a snippet of the note text)."
    matches = _find_note_matches(page_id, note_text)
    if not matches:
        return "No matching note found to delete."
    if len(matches) > 1:
        listing = "\n".join(f"- {mem}" for _, mem in matches)
        return "Multiple notes match; be more specific about the note text:\n" + listing
    rid, mem = matches[0]
    memory_client.delete_memory_record(id=config.MEMORY_ID, memoryRecordId=rid)
    _, title, note = _parse_note_record(mem)
    return f"Deleted note \"{note}\" for {title or page_id}."


@tool
def update_document_note(new_note: str, page_id: str = "", note_text: str = "") -> str:
    """Edit a saved personal note: replace its text with new_note. Identify the note to
    edit by its page_id and/or a snippet of the current note text (note_text). Call
    list_document_notes first. If several notes match, they are listed back so you can
    narrow down with a more specific note_text."""
    if not config.ENABLE_AGENTBASE_MEMORY or memory_client is None:
        return "AgentBase Memory is disabled in this deployment; cannot edit notes."
    if not page_id and not note_text:
        return "Specify which note to edit (a page_id and/or a snippet of the current note text)."
    matches = _find_note_matches(page_id, note_text)
    if not matches:
        return "No matching note found to edit."
    if len(matches) > 1:
        listing = "\n".join(f"- {mem}" for _, mem in matches)
        return "Multiple notes match; be more specific about the note text:\n" + listing
    rid, mem = matches[0]
    pid, title, old_note = _parse_note_record(mem)
    namespace = build_note_namespace(get_actor_id())
    new_record = f"page_id={pid} | title={title} | {new_note}"
    memory_client.insert_memory_records_directly(
        id=config.MEMORY_ID, namespace=namespace, request={"memoryRecords": [new_record]}
    )
    memory_client.delete_memory_record(id=config.MEMORY_ID, memoryRecordId=rid)
    return f"Updated note for {title or pid}: \"{old_note}\" → \"{new_note}\"."


@tool
def list_recent_reads(limit: int = 10) -> str:
    """List recently read documents for the current user."""
    actor_id = get_actor_id()
    rows = service.store.list_reads(actor_id, limit)
    if not rows:
        return "No reading history found."
    return "\n".join(
        f"- {row['page_title']} (page_id={row['page_id']}) at {row['created_at']} query={row['query'] or '-'}"
        for row in rows
    )


def _list_documents_text(message: str = "") -> str:
    """Build the markdown bullet list of indexed documents (shared by the tool and
    the handler fast-path). Header language follows the user's question."""
    vi = is_vietnamese(message)
    try:
        total = service.store.count_pages()
        rows = service.store.list_pages(limit=60)
    except Exception as error:
        return service.format_source_error(error)
    if not rows:
        return (
            "Chưa có tài liệu nào được lập chỉ mục. Hãy yêu cầu mình index/đồng bộ các trang Confluence trước."
            if vi else
            "No documents are indexed yet. Ask me to index/sync the Confluence pages first."
        )
    # Square brackets in a title break markdown link syntax ([label](url)); swap them.
    lines = [
        f"- [{row['title'].replace('[', '(').replace(']', ')')}]({row['url']})"
        for row in rows
    ]
    if vi:
        header = (
            f"{total} tài liệu đã được lập chỉ mục (hiển thị {len(rows)} đầu tiên):"
            if total > len(rows)
            else f"{total} tài liệu đã được lập chỉ mục:"
        )
    else:
        header = (
            f"{total} indexed documents (showing first {len(rows)}):"
            if total > len(rows)
            else f"{total} indexed document(s):"
        )
    return header + "\n" + "\n".join(lines)


@tool
def list_documents() -> str:
    """List every document currently in the indexed set as clickable title links.

    Use this when the user asks to list / show / enumerate the available documents
    WITHOUT giving a search keyword (e.g. "list all documents", "what docs do you have").
    Returns a ready-to-display markdown bullet list of linked titles — present it as-is.
    """
    return _list_documents_text(get_user_message())


_BYLINE_RE = re.compile(
    r"^.{0,40}?\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\s*",
    re.IGNORECASE,
)


def _clean_excerpt(text: str, limit: int = 160) -> str:
    """Turn a raw chunk into a tidy one-line excerpt: collapse whitespace, drop a leading
    'Author DD Month YYYY' byline, and cut at a sentence/word boundary."""
    cleaned = " ".join(text.split())
    cleaned = _BYLINE_RE.sub("", cleaned).strip()
    if len(cleaned) <= limit:
        return cleaned
    window = cleaned[: limit + 40]
    end = max(window.rfind(". "), window.rfind("! "), window.rfind("? "))
    if end >= 60:
        return window[: end + 1]
    cut = cleaned[:limit].rsplit(" ", 1)[0]
    return cut + "…"


def _search_documents_text(message: str) -> str:
    """Render document-search results deterministically: one bullet per DISTINCT matching
    page (title linked to URL, page_id hidden) with a grounded excerpt. Used by the
    handler fast-path so 'find documents about X' never lets the LLM pad, drop, or
    hallucinate entries (e.g. inventing 'Test Page' from conversation history)."""
    vi = is_vietnamese(message)
    # Retrieve more chunks than we display: results cluster on a few pages (and some get
    # dropped as empty), so over-fetch and dedupe down to DISTINCT pages to fill the list.
    want_pages = max(config.MAX_RESULTS, 5)
    try:
        matches = service.search_chunks(message, want_pages * 4)
    except Exception as error:
        return service.format_source_error(error)
    # Collapse to distinct pages (keeping each page's best-scoring chunk), skipping
    # placeholder/near-empty pages (e.g. a "Test Page" whose body is just "Test").
    seen: set[str] = set()
    pages: list[dict] = []
    for match in matches:
        if match["page_id"] in seen:
            continue
        if len(" ".join((match.get("text") or "").split())) < 25:
            continue
        seen.add(match["page_id"])
        pages.append(match)
    # Relevance floor relative to the top hit: drop weak filler (e.g. an off-topic
    # "Meeting notes" page that only matches on baseline semantic noise) instead of
    # padding to a fixed count. Always keep at least the best match.
    lines: list[str] = []
    if pages:
        top_score = pages[0]["score"]
        floor = max(0.30, 0.70 * top_score)
        for rank, match in enumerate(pages[:want_pages]):
            if rank > 0 and match["score"] < floor:
                break
            label = (match["title"] or "").replace("[", "(").replace("]", ")")
            excerpt = _clean_excerpt(match.get("text") or "")
            head = f"[{label}]({match['url']})" if match.get("url") else label
            lines.append(f"- {head} — {excerpt}" if excerpt else f"- {head}")
    if not lines:
        return (
            "Không tìm thấy tài liệu nào phù hợp trong hệ thống."
            if vi else "No matching documents found in the indexed set."
        )
    header = "Các tài liệu liên quan:" if vi else "Related documents:"
    return header + "\n" + "\n".join(lines)


# Keep only the last few user turns in the conversation thread. The agent's checkpointer
# persists history per session_id, and replaying a long thread to the LLM every turn is
# what made long-lived browser sessions take 1-2 min (vs ~30s for a fresh session). This
# trims (and permanently shrinks) the thread before each model call — no extra LLM call.
_KEEP_TURNS = 3


@before_model
def trim_history(state, runtime):
    messages = state["messages"]
    human_positions = [i for i, m in enumerate(messages) if isinstance(m, HumanMessage)]
    if len(human_positions) <= _KEEP_TURNS:
        return None
    start = human_positions[-_KEEP_TURNS]
    kept = messages[start:]
    return {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), *kept]}


agent = create_agent(
    llm,
    middleware=[trim_history],
    tools=[
        search_documents,
        list_documents,
        read_document,
        check_document_updates,
        what_changed,
        index_documents,
        sync_confluence_pages,
        add_document_note,
        list_document_notes,
        delete_document_note,
        update_document_note,
        list_recent_reads,
        remember,
        recall,
    ],
    system_prompt=(
        "You are Pagefinder, a document assistant with RAG over a fixed indexed document set. "
        "===== ABSOLUTE OUTPUT RULES (apply to EVERY reply, no exceptions) ===== "
        "1. NEVER use emojis, emoticons, or decorative icons ANYWHERE — not in headings, bullets, tables, or text. "
        "Your entire reply must be plain text/markdown with zero pictographic characters. "
        "2. NEVER show page_id or any 'Page ID' value to the user — not as text, not as a table column, not in a link. "
        "page_id is internal only; reference every document by its title linked to its URL. "
        "3. NEVER render results (documents, search hits, notes) as a table and NEVER add a '#'/index or 'Page ID' column. "
        "Use a simple markdown bullet list instead. "
        "4. Do NOT invent status reports, error tables, or 'system interrupted' messages; relay tool results factually. "
        "These four rules override any other formatting instinct. If you are about to add an icon, a Page ID, or a table, do not. "
        "===== END ABSOLUTE RULES ===== "
        "Always prefer searching indexed documents before answering knowledge questions. "
        "When the user asks about document content, use search_documents first and cite the page title as a markdown "
        "link to its URL. "
        "Format search results ALWAYS as a plain markdown bullet list — one bullet per result: the title as a markdown "
        "link, then ' — ' and ONE short description sentence ON THE SAME LINE as the link. NEVER render results as a "
        "table, NEVER add a '#'/index column, NEVER add a 'Page ID' column or show page_id, and do NOT start the answer "
        "with an emoji or a decorative icon heading. Show EVERY result the search_documents tool returns, one bullet "
        "each, in the order given — do NOT drop, merge, filter, or limit them, and do NOT add results the tool did not return. "
        "When the user asks to list/show all available documents without a search keyword, use list_documents and "
        "present its output AS-IS: a simple markdown bullet list of clickable titles. Do NOT build a table, do NOT add "
        "a Page ID column, do NOT split into invented topic categories, and do NOT claim what the corpus is 'mostly "
        "about'. Show the first ~30 linked titles and note the total count if there are many. "
        "NEVER show page_id values to the user — they are internal identifiers only. Use page_id internally to call "
        "tools, but in your answer reference documents by their title (linked to the URL) instead. "
        "When the user asks to inspect one document in depth, use read_document. "
        "When the user asks whether docs changed, use check_document_updates only; it reads the local changelog and must not trigger a Confluence sync. "
        "When the user asks WHAT specifically changed in a given page, use what_changed(page_id). "
        "Both tools return a ready-to-display markdown block: each document line, then its one-sentence summary, then its "
        "own ```diff fenced block. Output that block VERBATIM — do NOT renumber, do NOT convert bullets to a numbered list, "
        "do NOT move or collect the diffs into a separate section, do NOT repeat the document list, and do NOT add summaries "
        "of your own (each summary is already included). Keep every ```diff block exactly where it is and unchanged. "
        "You may add at most ONE short intro sentence at the very top; otherwise relay the tool output unchanged. "
        "When the user explicitly asks the system to index, re-index, or refresh the documents, use index_documents (incremental: only pages whose version changed). "
        "When the user asks to save or review personal notes, use add_document_note or list_document_notes. "
        "To delete a note use delete_document_note, and to edit/change a note use update_document_note; for both, "
        "first call list_document_notes to find the right note, then identify it by its page_id and/or a snippet of "
        "its note_text. If the tool reports multiple matches, ask the user which one (by note text). "
        "Use list_recent_reads to recover what the user opened before. "
        "If the indexed corpus is insufficient, say that the scope is limited to the configured documents. "
        "Do NOT use emojis or decorative icons anywhere in your answers; keep the text plain."
    ),
    checkpointer=checkpointer,
)


def _success(text: str) -> dict:
    """Build a success response with the reply sanitized (no emojis / leaked page_id)."""
    return {"status": "success", "response": strip_decorations(text), "timestamp": utc_now()}


@app.entrypoint
def handler(payload: dict, context: RequestContext) -> dict:
    if config.ENABLE_AGENTBASE_MEMORY and (not context.user_id or not context.session_id):
        return {
            "status": "error",
            "error": (
                "Missing required headers: X-GreenNode-AgentBase-User-Id and "
                "X-GreenNode-AgentBase-Session-Id are required when using memory."
            ),
        }

    if not context.user_id:
        context.user_id = "shared-user"
    if not context.session_id:
        context.session_id = "shared-session"

    message = payload.get("message", "")
    if not message:
        return {"status": "error", "error": "Payload must include a non-empty 'message'."}

    actor_id = context.user_id or "shared-user"
    # Snapshot the user's previous update-check timestamp BEFORE serving this request.
    # "What's new?" answers against this snapshot and advances the timestamp itself (in
    # check_document_updates_impl), so it reports everything changed since the user's
    # previous update check — not since their last general visit. last_seen_at is still
    # advanced every request below as a record of general activity.
    last_update_check_before = service.store.get_last_update_check(actor_id)
    try:
        requested_page_ids = extract_page_ids_from_text(message)
        if requested_page_ids:
            page_id = requested_page_ids[0]

            if looks_like_summary_request(message):
                try:
                    title, url, text = service.fetch_page_for_summary(page_id)
                except Exception as exc:  # network / not found / no access
                    return {
                        "status": "success",
                        "response": f"Could not fetch page {page_id}: {exc}",
                        "timestamp": utc_now(),
                    }
                summary = llm.invoke(
                    [
                        (
                            "system",
                            "You summarize a Confluence page for the user. Reply in the SAME "
                            "language as the user's request. Be concise, use markdown (short "
                            "headings and bullet points), keep the key points, and do not invent "
                            "content that is not in the page.",
                        ),
                        (
                            "human",
                            f"User request:\n{message}\n\nPage title: {title}\n\n"
                            f"Page content:\n{text[:16000]}",
                        ),
                    ]
                ).content
                return _success(f"{summary}\n\n{url}")

            page_content = service.read_document_impl(
                page_id,
                message,
                actor_id=actor_id,
            )
            return _success(page_content)

        # Fast-paths: deterministic intents that need no agent reasoning. Calling the
        # tool logic directly skips both LLM round-trips (tool-selection + relay), so
        # these answers return in milliseconds instead of waiting on the model twice.
        # what's-new is checked before list: an update question can contain "tài liệu nào"
        # which would otherwise look like a plain list request.
        if looks_like_list_notes_request(message):
            return _success(_list_notes_text(actor_id, message))
        if looks_like_whats_new_request(message):
            try:
                whats_new = service.check_document_updates_impl(actor_id, last_update_check_before, message)
            except Exception as error:
                whats_new = service.format_source_error(error)
            return _success(whats_new)
        if looks_like_list_request(message):
            return _success(_list_documents_text(message))
        if looks_like_doc_search_request(message):
            return _success(_search_documents_text(message))

        runtime_config = {
            "configurable": {
                "thread_id": context.session_id,
                "actor_id": actor_id,
                "last_update_check_before": last_update_check_before,
                "user_message": message,
            }
        }
        result = agent.invoke({"messages": [{"role": "user", "content": message}]}, config=runtime_config)
        ai_message = result["messages"][-1]
        return _success(ai_message.content)
    finally:
        service.store.set_last_seen(actor_id)


@app.ping
def health_check() -> PingStatus:
    return PingStatus.HEALTHY


register_ui_routes(app)
