import re
import unicodedata
from datetime import datetime, timezone


def fold_accents(value: str) -> str:
    """Lowercase and strip Vietnamese diacritics so 'liệt kê tài liệu' matches the
    plain ASCII phrase 'liet ke tai lieu'."""
    lowered = value.casefold().replace("đ", "d")
    decomposed = unicodedata.normalize("NFD", lowered)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_namespace(memory_strategy_id: str, actor_id: str) -> str:
    return f"/strategies/{memory_strategy_id}/actors/{actor_id}"


def collapse_whitespace(value: str) -> str:
    return " ".join(value.split())


def normalize_text(value: str) -> str:
    lowered = value.casefold()
    lowered = re.sub(r"[^\w\s]", " ", lowered)
    return collapse_whitespace(lowered)


def tokenize(value: str) -> list[str]:
    normalized = normalize_text(value)
    return [token for token in normalized.split() if token]


def extract_page_ids_from_text(value: str) -> list[str]:
    return re.findall(r"\b\d{4,}\b", value)


def looks_like_summary_request(message: str) -> bool:
    lowered = message.lower()
    keywords = [
        "tóm tắt", "tom tat", "tóm lược", "tom luoc", "nội dung", "noi dung",
        "summar",  # summary / summarize / summarise
        "tl;dr", "tldr", "recap", "overview",
    ]
    return any(keyword in lowered for keyword in keywords)


# "about / về / on the topic of" qualifiers turn a bare list request into a
# topic search, which must go through the search agent, not the fast-path.
# Stored accent-folded; matched as whole words (padded with spaces on both sides).
_SEARCH_QUALIFIERS = ("ve", "about", "lien quan", "topic", "chu de", "regarding", "on")

# Targets that are NOT the document corpus — "list my notes / reading history" must
# go to their own tools (list_document_notes / list_recent_reads), not list_documents.
_NON_DOC_TARGETS = ("ghi chu", "note", "lich su", "history", "da doc", "da xem", "da luu")


def is_vietnamese(message: str) -> bool:
    """Heuristic: the message is Vietnamese if it has Vietnamese diacritics or uses
    common Vietnamese words. Used to pick the language of deterministic fast-path text."""
    if fold_accents(message) != message.casefold():
        return True  # had diacritics → Vietnamese
    folded = f" {fold_accents(message)} "
    words = (" tai lieu ", " co ", " khong ", " gi ", " nhung ", " cho ", " minh ",
             " ban ", " trang ", " moi ", " cap nhat ", " thay doi ", " danh sach ")
    return any(w in folded for w in words)


def looks_like_list_request(message: str) -> bool:
    """True for a bare 'show me all the documents' request (no search keyword)."""
    # A "what changed / what's new" question is never a plain list request, even though
    # it can contain "tài liệu nào". Defer to the what's-new intent.
    if looks_like_whats_new_request(message):
        return False
    lowered = normalize_text(fold_accents(message))
    padded = f" {lowered} "
    if any(f" {q} " in padded for q in _SEARCH_QUALIFIERS):
        return False
    if any(t in lowered for t in _NON_DOC_TARGETS):
        return False
    phrases = [
        "list document", "list doc", "list all", "show all document", "show all doc",
        "show document", "show doc", "all document", "all doc", "what document",
        "what doc", "which document", "which doc", "available document", "available doc",
        "liet ke", "danh sach tai lieu", "danh sach doc", "danh sach document",
        "co nhung tai lieu", "co tai lieu gi", "co nhung doc", "co doc gi",
        "co nhung document", "tai lieu nao", "co document gi", "co nhung trang",
    ]
    return any(phrase in lowered for phrase in phrases)


def looks_like_whats_new_request(message: str) -> bool:
    """True for 'what's new / what changed / any updates' without a specific page."""
    lowered = normalize_text(fold_accents(message))
    phrases = [
        "whats new", "what is new", "what changed", "what has changed", "anything new",
        "any update", "any new doc", "any new document", "recently updated",
        "updated recently", "recent change", "recent update",
        "co gi moi", "co gi update", "co gi thay doi", "vua update", "vua cap nhat",
        "moi update", "moi cap nhat", "co cap nhat", "co thay doi", "vua duoc update",
        "vua duoc cap nhat", "co document nao vua", "co tai lieu nao vua",
        "co tai lieu nao moi", "co document nao moi", "gan day co",
    ]
    return any(phrase in lowered for phrase in phrases)
