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


# Pictographic / emoji ranges. Deliberately excludes em dash (—), en dash, bullet (•),
# ellipsis and other normal punctuation so list formatting stays intact.
_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF"  # emoji, symbols & pictographs, supplemental
    "\U00002600-\U000026FF"   # miscellaneous symbols
    "\U00002700-\U000027BF"   # dingbats (✂ ✅ ✓ ✗ …)
    "\U00002B00-\U00002BFF"   # misc symbols & arrows (★ ⬆ …)
    "\U00002300-\U000023FF"   # technical (⌚ ⏰ …)
    "\U0000FE00-\U0000FE0F"   # variation selectors
    "\U0001F1E6-\U0001F1FF"   # regional indicators (flags)
    "\U0000200D]"             # zero-width joiner
)


def strip_decorations(text: str) -> str:
    """Remove emojis/icons and any leaked page_id from a reply, deterministically — so
    the output stays plain regardless of what the LLM tried to add. Safe on plain text."""
    if not text:
        return text
    text = _EMOJI_RE.sub("", text)
    # Drop leaked page identifiers in any shape: "page_id=123", "(Page ID: 123)", "Page ID 123".
    text = re.sub(r"\(?\s*page[ _]?id\s*[:=]?\s*\d+\s*\)?", "", text, flags=re.IGNORECASE)
    # Tidy whitespace left behind by removed icons.
    text = re.sub(r"\*\*[ \t]+(?=\S)", "**", text)            # "**  Title" -> "**Title"
    text = re.sub(r"(?m)^[ \t]+(?=(\*\*|#{1,6}\s|\[|- |\* ))", "", text)  # leading space before a marker
    text = re.sub(r"[ \t]{2,}", " ", text)                    # collapse runs
    return "\n".join(line.rstrip() for line in text.split("\n"))


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


def looks_like_list_notes_request(message: str) -> bool:
    """True for 'list/show my saved notes' — but NOT add/edit/delete-note requests."""
    folded = normalize_text(fold_accents(message))
    if "ghi chu" not in folded and "note" not in folded:
        return False
    # add / edit / delete intents must go to their own tools via the agent, not the list.
    write_verbs = (
        "them ghi chu", "luu ghi chu", "them note", "add note", "ghi chu cho", "ghi chu la",
        "ghi chu thanh", "xoa", "sua", "chinh sua", "cap nhat ghi chu", "update ghi chu",
        "delete", "edit",
    )
    if any(v in folded for v in write_verbs):
        return False
    list_verbs = (
        "liet ke", "danh sach", "list", "show", "xem", "hien thi", "co nhung", "co bao nhieu",
        "co may", "cua toi", "cua minh", "da luu", "nao", "tat ca",
    )
    return any(v in folded for v in list_verbs)


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
