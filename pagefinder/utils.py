import re
from datetime import datetime, timezone


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
