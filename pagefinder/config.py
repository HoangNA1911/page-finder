import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

MEMORY_ID = os.environ.get("MEMORY_ID", "")
MEMORY_STRATEGY_ID = os.environ.get("MEMORY_STRATEGY_ID", "default")
ENABLE_AGENTBASE_MEMORY = os.environ.get("PAGEFINDER_ENABLE_AGENTBASE_MEMORY", "false").lower() == "true"
LLM_MODEL = os.environ.get("LLM_MODEL", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")

SOURCE_MODE = os.environ.get("PAGEFINDER_SOURCE_MODE", "confluence").strip().lower()
DOCS_DIR = Path(os.environ.get("PAGEFINDER_DOCS_DIR", "docs"))

CONFLUENCE_BASE_URL = os.environ.get("CONFLUENCE_BASE_URL", "")
CONFLUENCE_EMAIL = os.environ.get("CONFLUENCE_EMAIL", "")
CONFLUENCE_API_TOKEN = os.environ.get("CONFLUENCE_API_TOKEN", "")
CONFLUENCE_PAGE_IDS = [
    page_id.strip()
    for page_id in os.environ.get("CONFLUENCE_PAGE_IDS", "").split(",")
    if page_id.strip()
]

DATA_DIR = Path(os.environ.get("PAGEFINDER_DATA_DIR", ".pagefinder"))
INDEX_PATH = DATA_DIR / "index.json"
DB_PATH = DATA_DIR / "pagefinder.db"
AUTO_SYNC_ON_QUERY = os.environ.get("PAGEFINDER_AUTO_SYNC_ON_QUERY", "true").lower() == "true"
BACKGROUND_SYNC_ENABLED = os.environ.get("PAGEFINDER_BACKGROUND_SYNC_ENABLED", "true").lower() == "true"
BACKGROUND_SYNC_INTERVAL_SECONDS = int(os.environ.get("PAGEFINDER_BACKGROUND_SYNC_INTERVAL_SECONDS", "300"))
MAX_RESULTS = int(os.environ.get("PAGEFINDER_MAX_RESULTS", "5"))
CHUNK_MAX_CHARS = int(os.environ.get("PAGEFINDER_CHUNK_MAX_CHARS", "1200"))
CHUNK_OVERLAP_PARAGRAPHS = int(os.environ.get("PAGEFINDER_CHUNK_OVERLAP_PARAGRAPHS", "1"))
SEARCH_CANDIDATE_LIMIT = int(os.environ.get("PAGEFINDER_SEARCH_CANDIDATE_LIMIT", "25"))
INDEX_SCHEMA_VERSION = 2

SEARCH_SYNONYMS = {
    "approval": ["approve", "approved", "approval flow", "duyet", "phe duyet"],
    "approver": ["reviewer", "nguoi duyet"],
    "payment": ["payments", "payout", "thanh toan"],
    "merchant": ["seller", "shop"],
    "finance": ["financial", "tai chinh"],
    "director": ["head", "giam doc"],
    "owner": ["product owner", "po"],
    "risk": ["risks", "rui ro"],
    "evidence": ["proof", "bang chung"],
    "revision": ["needs revision", "revise", "chinh sua"],
    "reminder": ["notify", "notification", "nhac nho"],
    "workflow": ["flow", "process", "quy trinh"],
}


def validate_config() -> None:
    required_env_vars = {
        "LLM_MODEL": LLM_MODEL,
        "LLM_BASE_URL": LLM_BASE_URL,
        "LLM_API_KEY": LLM_API_KEY,
    }
    if ENABLE_AGENTBASE_MEMORY:
        required_env_vars["MEMORY_ID"] = MEMORY_ID
    if SOURCE_MODE == "confluence":
        required_env_vars.update(
            {
                "CONFLUENCE_BASE_URL": CONFLUENCE_BASE_URL,
                "CONFLUENCE_EMAIL": CONFLUENCE_EMAIL,
                "CONFLUENCE_API_TOKEN": CONFLUENCE_API_TOKEN,
            }
        )

    missing_env_vars = [name for name, value in required_env_vars.items() if not value]
    if missing_env_vars:
        raise ValueError("Missing required environment variables: " + ", ".join(sorted(missing_env_vars)))
    if SOURCE_MODE not in {"markdown", "confluence"}:
        raise ValueError("PAGEFINDER_SOURCE_MODE must be either 'markdown' or 'confluence'")
    if SOURCE_MODE == "confluence" and not CONFLUENCE_PAGE_IDS:
        raise ValueError("CONFLUENCE_PAGE_IDS must contain at least one page id")
    if SOURCE_MODE == "markdown" and not DOCS_DIR.exists():
        raise ValueError(f"PAGEFINDER_DOCS_DIR does not exist: {DOCS_DIR}")
    if BACKGROUND_SYNC_INTERVAL_SECONDS <= 0:
        raise ValueError("PAGEFINDER_BACKGROUND_SYNC_INTERVAL_SECONDS must be greater than 0")

    DATA_DIR.mkdir(parents=True, exist_ok=True)


validate_config()
