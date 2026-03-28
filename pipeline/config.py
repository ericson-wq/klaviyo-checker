"""Pipeline configuration constants."""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
CHECKPOINT_DIR = PROJECT_ROOT / "checkpoints"

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
DEFAULT_DELAY = 2.0  # seconds between requests per domain
GLOBAL_CONCURRENCY = 5  # max concurrent outbound requests
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # exponential backoff multiplier

# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
REQUEST_TIMEOUT = 15.0
CONNECT_TIMEOUT = 10.0

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
]

DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------
SHOPIFY_REVIEWS_BASE_URL = "https://apps.shopify.com/klaviyo-email-marketing/reviews"
SHOPIFY_REVIEWS_DELAY = 3.0

CRO_MEDIA_BASE_URL = "https://cro.media"
CRO_MEDIA_DELAY = 2.0

GOOGLE_SEARCH_DELAY = 12.0  # conservative to avoid CAPTCHAs

# ---------------------------------------------------------------------------
# Klaviyo detection
# ---------------------------------------------------------------------------
TARGET_COUNTRIES = {"united states", "united kingdom", "australia", "canada"}

# ---------------------------------------------------------------------------
# CSV export columns
# ---------------------------------------------------------------------------
EXPORT_COLUMNS = [
    "domain",
    "store_name",
    "source",
    "myshopify_url",
    "country",
    "platform",
    "klaviyo_verified",
    "klaviyo_signals",
    "wetracked_detected",
    "wetracked_signals",
    "discovered_at",
    "meta_title",
    "meta_description",
]
