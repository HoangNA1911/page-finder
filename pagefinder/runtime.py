from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.config import get_config

from greennode_agentbase import GreenNodeAgentBaseApp, PingStatus, RequestContext
from greennode_agentbase.memory import MemoryClient
from greennode_agentbase.memory.models import MemoryRecordSearchRequest
from greennode_agent_bridge import AgentBaseMemoryEvents

from pagefinder import config
from pagefinder.background import BackgroundSyncJob
from pagefinder.service import PagefinderService
from pagefinder.ui import register_ui_routes
from pagefinder.utils import build_namespace, extract_page_ids_from_text, looks_like_summary_request, utc_now

app = GreenNodeAgentBaseApp()
service = PagefinderService()
background_sync_job = BackgroundSyncJob(service)
checkpointer = AgentBaseMemoryEvents(memory_id=config.MEMORY_ID) if config.ENABLE_AGENTBASE_MEMORY else None
memory_client = MemoryClient() if config.ENABLE_AGENTBASE_MEMORY else None
llm = ChatOpenAI(model=config.LLM_MODEL, base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY)
background_sync_job.start()


def get_configurable() -> dict:
    config_value = get_config()
    return config_value.get("configurable", {})


def get_actor_id() -> str:
    return get_configurable().get("actor_id", "shared-user")


def get_last_seen_before() -> str | None:
    """The user's last-seen timestamp captured before the current request started."""
    return get_configurable().get("last_seen_before")


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


@tool
def remember(fact: str) -> str:
    """Store a user preference or fact for later conversations."""
    if not config.ENABLE_AGENTBASE_MEMORY or memory_client is None:
        return "AgentBase Memory is disabled in this deployment."
    namespace = build_namespace(config.MEMORY_STRATEGY_ID, get_actor_id())
    memory_client.insert_memory_records_directly(id=config.MEMORY_ID, namespace=namespace, request=[fact])
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
    if not results:
        return "No relevant memories found."
    return "\n".join(f"- {row.memory} (score: {row.score:.2f})" for row in results)


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
    """Report which documents changed since the current user last used the system."""
    try:
        return service.check_document_updates_impl(get_actor_id(), get_last_seen_before())
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
    memory_client.insert_memory_records_directly(id=config.MEMORY_ID, namespace=namespace, request=[record])
    return f"Saved note for {page['title']} (page_id={page_id})."


@tool
def list_document_notes(page_id: str = "") -> str:
    """List saved personal notes, optionally filtered to one document page (from AgentBase memory)."""
    if not config.ENABLE_AGENTBASE_MEMORY or memory_client is None:
        return "AgentBase Memory is disabled in this deployment; cannot list notes."
    actor_id = get_actor_id()
    namespace = build_note_namespace(actor_id)
    records = _memory_records(memory_client.list_memory_records(id=config.MEMORY_ID, namespace=namespace))
    prefix = f"page_id={page_id} |" if page_id else ""
    lines = [
        f"- {row.memory}"
        for row in records
        if row.memory and (not prefix or row.memory.startswith(prefix))
    ]
    if not lines:
        return "No saved document notes found."
    return "\n".join(lines)


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


@tool
def list_documents() -> str:
    """List every document currently in the indexed set (title + page_id).

    Use this when the user asks to list / show / enumerate the available documents
    WITHOUT giving a search keyword (e.g. "list all documents", "what docs do you have").
    """
    try:
        rows = service.store.list_pages()
    except Exception as error:
        return service.format_source_error(error)
    if not rows:
        return "No documents are indexed yet. Ask me to index/sync the Confluence pages first."
    lines = [f"- {row['title']} (page_id={row['page_id']})" for row in rows]
    return f"{len(rows)} indexed document(s):\n" + "\n".join(lines)


agent = create_agent(
    llm,
    tools=[
        search_documents,
        list_documents,
        read_document,
        check_document_updates,
        index_documents,
        sync_confluence_pages,
        add_document_note,
        list_document_notes,
        list_recent_reads,
        remember,
        recall,
    ],
    system_prompt=(
        "You are Pagefinder, a document assistant with RAG over a fixed indexed document set. "
        "Always prefer searching indexed documents before answering knowledge questions. "
        "When the user asks about document content, use search_documents first and cite the page title as a markdown "
        "link to its URL. "
        "When the user asks to list/show all available documents without a search keyword, use list_documents and "
        "present the actual document titles returned by the tool. Do NOT collapse them into invented topic categories "
        "or claim what the corpus is 'mostly about' — just list the real titles (you may show the first ~30 and note "
        "the total count if there are many). "
        "NEVER show page_id values to the user — they are internal identifiers only. Use page_id internally to call "
        "tools, but in your answer reference documents by their title (linked to the URL) instead. "
        "When the user asks to inspect one document in depth, use read_document. "
        "When the user asks whether docs changed, use check_document_updates only; it reads the local changelog and must not trigger a Confluence sync. "
        "When the user explicitly asks the system to index, re-index, or refresh the documents, use index_documents (incremental: only pages whose version changed). "
        "When the user asks to save or review personal notes, use add_document_note or list_document_notes. "
        "Use list_recent_reads to recover what the user opened before. "
        "If the indexed corpus is insufficient, say that the scope is limited to the configured documents."
    ),
    checkpointer=checkpointer,
)


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
    # Snapshot the user's previous last-seen timestamp BEFORE serving this request, then
    # advance it once the request is handled. "What's new?" answers against this snapshot,
    # so it reports everything changed since the user's previous visit.
    last_seen_before = service.store.get_last_seen(actor_id)
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
                return {
                    "status": "success",
                    "response": f"{summary}\n\n{url}",
                    "timestamp": utc_now(),
                }

            page_content = service.read_document_impl(
                page_id,
                message,
                actor_id=actor_id,
            )
            if page_content.startswith("Could not read") or page_content.startswith("Page "):
                return {"status": "success", "response": page_content, "timestamp": utc_now()}
            return {"status": "success", "response": page_content, "timestamp": utc_now()}

        runtime_config = {
            "configurable": {
                "thread_id": context.session_id,
                "actor_id": actor_id,
                "last_seen_before": last_seen_before,
            }
        }
        result = agent.invoke({"messages": [{"role": "user", "content": message}]}, config=runtime_config)
        ai_message = result["messages"][-1]
        return {"status": "success", "response": ai_message.content, "timestamp": utc_now()}
    finally:
        service.store.set_last_seen(actor_id)


@app.ping
def health_check() -> PingStatus:
    return PingStatus.HEALTHY


register_ui_routes(app)
