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

# Embedding model (OpenAI-compatible). Defaults to the LLM endpoint/key so a single
# credential can serve both. When the model/key/base url are not all present, the
# service falls back to the deterministic cheap_embedding() so it still runs offline.
EMBEDDING_MODEL = os.environ.get("PAGEFINDER_EMBEDDING_MODEL", "")
EMBEDDING_BASE_URL = os.environ.get("PAGEFINDER_EMBEDDING_BASE_URL", LLM_BASE_URL)
EMBEDDING_API_KEY = os.environ.get("PAGEFINDER_EMBEDDING_API_KEY", LLM_API_KEY)
EMBEDDING_DIM = int(os.environ.get("PAGEFINDER_EMBEDDING_DIM", "1536"))
EMBEDDING_BATCH_SIZE = int(os.environ.get("PAGEFINDER_EMBEDDING_BATCH_SIZE", "64"))

# Confluence is the only supported source. The local Markdown mode has been removed.
SOURCE_MODE = "confluence"

CONFLUENCE_BASE_URL = os.environ.get("CONFLUENCE_BASE_URL", "")
CONFLUENCE_EMAIL = os.environ.get("CONFLUENCE_EMAIL", "")
CONFLUENCE_API_TOKEN = os.environ.get("CONFLUENCE_API_TOKEN", "")
CONFLUENCE_PAGE_IDS = [
    page_id.strip()
    for page_id in os.environ.get("CONFLUENCE_PAGE_IDS", "").split(",")
    if page_id.strip()
]
# Optional auto-discovery: index every page in these space keys (comma-separated).
# When set, the target page set is discovered each sync (union with CONFLUENCE_PAGE_IDS),
# so new pages are picked up and deleted pages are pruned automatically.
CONFLUENCE_SPACE_KEYS = [
    space_key.strip()
    for space_key in os.environ.get("CONFLUENCE_SPACE_KEYS", "").split(",")
    if space_key.strip()
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
VEC_CANDIDATE_LIMIT = int(os.environ.get("PAGEFINDER_VEC_CANDIDATE_LIMIT", "50"))
FTS_CANDIDATE_LIMIT = int(os.environ.get("PAGEFINDER_FTS_CANDIDATE_LIMIT", "50"))
INDEX_SCHEMA_VERSION = 4

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
    if not CONFLUENCE_PAGE_IDS and not CONFLUENCE_SPACE_KEYS:
        raise ValueError("Set CONFLUENCE_PAGE_IDS (explicit pages) or CONFLUENCE_SPACE_KEYS (index whole spaces)")
    if BACKGROUND_SYNC_INTERVAL_SECONDS <= 0:
        raise ValueError("PAGEFINDER_BACKGROUND_SYNC_INTERVAL_SECONDS must be greater than 0")

    DATA_DIR.mkdir(parents=True, exist_ok=True)


validate_config()
