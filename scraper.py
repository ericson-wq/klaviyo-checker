#!/usr/bin/env python3
"""
Shopify App Store Klaviyo Reviews Scraper

Scrapes reviews from the Klaviyo app listing on the Shopify App Store
to build a list of verified Shopify + Klaviyo users.

Source: https://apps.shopify.com/klaviyo-email-marketing/reviews

Usage:
    python scraper.py                    # Scrape all pages
    python scraper.py --max-pages 5      # Scrape first 5 pages only
    python scraper.py --debug            # Print HTML structure of first page (for debugging selectors)
    python scraper.py --start-page 10    # Resume from page 10
"""

import argparse
import csv
import json
import logging
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_URL = "https://apps.shopify.com/klaviyo-email-marketing/reviews"
REQUEST_DELAY = 1.5  # seconds between page requests
MAX_RETRIES = 3

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

TARGET_COUNTRIES = {"united states", "united kingdom", "australia", "canada"}

OUTPUT_DIR = Path(__file__).parent / "output"

log = logging.getLogger("klaviyo_scraper")

# ---------------------------------------------------------------------------
# Domain helpers
# ---------------------------------------------------------------------------

_DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
    r"[a-zA-Z]{2,63}$"
)


def normalize_domain(raw: str) -> str:
    """Strip protocol/path, lowercase, validate, return clean domain."""
    raw = raw.strip().lower()
    if "://" in raw:
        raw = raw.split("://", 1)[1]
    raw = raw.split("/")[0].split("?")[0].split("#")[0]
    raw = raw.split(":")[0]
    raw = raw.rstrip(".")
    if not _DOMAIN_RE.match(raw):
        return ""
    return raw


def extract_domain_from_url(url: str) -> str:
    """Extract and normalize domain from a full URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split("/")[0]
        return normalize_domain(domain)
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# HTTP fetching
# ---------------------------------------------------------------------------


def fetch_page(url: str, params: Optional[Dict] = None) -> Optional[httpx.Response]:
    """Fetch a URL with retries and exponential backoff."""
    timeout = httpx.Timeout(15.0, connect=10.0)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with httpx.Client(
                timeout=timeout,
                follow_redirects=True,
                max_redirects=5,
            ) as client:
                resp = client.get(url, headers=HEADERS, params=params)
                resp.raise_for_status()
                return resp
        except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException) as exc:
            if attempt == MAX_RETRIES:
                log.error("Failed after %d attempts: %s — %s", MAX_RETRIES, url, exc)
                return None
            wait = 2 ** attempt
            log.warning("Request failed (attempt %d/%d): %s — retrying in %ds",
                        attempt, MAX_RETRIES, exc, wait)
            time.sleep(wait)
    return None


# ---------------------------------------------------------------------------
# HTML parsing — review extraction
# ---------------------------------------------------------------------------

def debug_page_structure(html: str):
    """Print the HTML structure of the reviews page to help identify selectors."""
    soup = BeautifulSoup(html, "html.parser")

    print("\n" + "=" * 80)
    print("DEBUG: Page Structure Analysis")
    print("=" * 80)

    # Look for JSON-LD structured data
    for script in soup.find_all("script", type="application/ld+json"):
        print("\n--- JSON-LD ---")
        try:
            data = json.loads(script.string)
            print(json.dumps(data, indent=2)[:2000])
        except (json.JSONDecodeError, TypeError):
            print(script.string[:500] if script.string else "(empty)")

    # Look for common review container patterns
    print("\n--- Looking for review containers ---")

    # Strategy 1: Find elements with 'review' in class or id
    review_elements = soup.find_all(
        lambda tag: tag.get("class") and any("review" in c.lower() for c in tag.get("class", []))
    )
    seen_classes = set()
    for el in review_elements[:20]:
        classes = " ".join(el.get("class", []))
        if classes not in seen_classes:
            seen_classes.add(classes)
            # Show tag, classes, and a snippet of content
            text = el.get_text(strip=True)[:100]
            print(f"  <{el.name} class=\"{classes}\"> → {text}")

    # Strategy 2: Find elements with data attributes containing 'review'
    print("\n--- Elements with data-* review attributes ---")
    for el in soup.find_all(lambda tag: any("review" in str(v).lower() for v in tag.attrs.values())):
        attrs = {k: v for k, v in el.attrs.items() if "review" in str(v).lower()}
        text = el.get_text(strip=True)[:80]
        print(f"  <{el.name} {attrs}> → {text}")
        if len(attrs) > 10:
            break

    # Strategy 3: Look for rating-related elements
    print("\n--- Rating elements ---")
    for el in soup.find_all(lambda tag: tag.get("class") and any("star" in c.lower() or "rating" in c.lower() for c in tag.get("class", []))):
        classes = " ".join(el.get("class", []))
        attrs = {k: v for k, v in el.attrs.items() if k.startswith("aria") or k.startswith("data")}
        print(f"  <{el.name} class=\"{classes}\" {attrs}>")
        if len(seen_classes) > 15:
            break

    # Strategy 4: Look for pagination
    print("\n--- Pagination ---")
    for el in soup.find_all(lambda tag: tag.get("class") and any("paginat" in c.lower() for c in tag.get("class", []))):
        classes = " ".join(el.get("class", []))
        links = el.find_all("a")
        print(f"  <{el.name} class=\"{classes}\"> — {len(links)} links")
        for a in links[:5]:
            print(f"    <a href=\"{a.get('href', '')}\"> {a.get_text(strip=True)}")

    # Strategy 5: Look for any links containing .myshopify.com or store references
    print("\n--- Store/shop links ---")
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if "myshopify" in href or "/store/" in href:
            print(f"  <a href=\"{href}\"> {a.get_text(strip=True)[:60]}")

    # Print a raw snippet of the body for manual inspection
    print("\n--- Raw HTML snippet (first 5000 chars of body) ---")
    body = soup.find("body")
    if body:
        print(str(body)[:5000])

    print("\n" + "=" * 80)


def parse_reviews_page(html: str) -> List[Dict]:
    """
    Parse a reviews page and extract review data.

    Shopify App Store review structure (as of 2026-03):
    - Container: <div data-merchant-review="" data-review-content-id="XXXXX">
    - Rating: <div aria-label="X out of 5 stars" role="img">
    - Grid layout with tw-order-1 (sidebar: store name, country, usage)
      and tw-order-2 (content: date, review text)
    """
    soup = BeautifulSoup(html, "html.parser")
    reviews = []

    containers = soup.find_all("div", attrs={"data-merchant-review": ""})
    if not containers:
        log.warning("No review containers found (data-merchant-review)")
        return reviews

    for container in containers:
        review = _extract_review(container)
        if review and review.get("store_name"):
            reviews.append(review)

    return reviews


def _extract_review(container) -> Optional[Dict]:
    """Extract review data from a data-merchant-review container."""
    review = {
        "store_name": "",
        "domain": "",
        "myshopify_url": "",
        "review_date": "",
        "rating": "",
        "review_text": "",
        "country": "",
    }

    # --- Rating from aria-label ---
    stars_el = container.find(attrs={"aria-label": True, "role": "img"})
    if stars_el:
        aria = stars_el.get("aria-label", "")
        match = re.search(r"(\d+)\s+out of\s+(\d+)\s+stars?", aria)
        if match:
            review["rating"] = match.group(1)

    # --- Find the two grid columns ---
    # order-1 = sidebar (store name, country, usage duration)
    # order-2 = content (date, review text)
    cols = container.find_all("div", recursive=False)

    sidebar_text = ""
    content_text = ""

    for col in cols:
        classes = " ".join(col.get("class", []))
        if "order-1" in classes:
            sidebar_text = col.get_text("\n", strip=True)
        elif "order-2" in classes:
            content_text = col.get_text("\n", strip=True)

    # --- Parse sidebar: store_name, country, usage ---
    if sidebar_text:
        sidebar_lines = [l.strip() for l in sidebar_text.split("\n") if l.strip()]
        if sidebar_lines:
            review["store_name"] = sidebar_lines[0]
        if len(sidebar_lines) >= 2:
            review["country"] = sidebar_lines[1]
        # sidebar_lines[2] would be usage duration if present

    # --- Parse content: date, review text ---
    if content_text:
        content_lines = [l.strip() for l in content_text.split("\n") if l.strip()]

        # First line is the date
        date_pattern = re.compile(
            r"(January|February|March|April|May|June|July|August|September|"
            r"October|November|December)\s+\d{1,2},\s+\d{4}"
        )

        for i, line in enumerate(content_lines):
            date_match = date_pattern.search(line)
            if date_match:
                review["review_date"] = date_match.group()
                # Review text is everything after the date line, excluding UI elements
                body_lines = [
                    l for l in content_lines[i + 1:]
                    if l not in ("Show more", "Show less", "Helpful", "Report")
                    and not re.match(r"^\d+ (person|people) found this", l, re.IGNORECASE)
                ]
                review["review_text"] = " ".join(body_lines).strip()
                break

    # --- Look for store links ---
    for a in container.find_all("a", href=True):
        href = a["href"]
        if "myshopify" in href:
            review["myshopify_url"] = href
            review["domain"] = extract_domain_from_url(href)
            break

    return review if review["store_name"] else None


def get_total_pages(html: str) -> int:
    """Extract total number of review pages from pagination."""
    soup = BeautifulSoup(html, "html.parser")

    # Look for pagination links
    page_links = soup.select("a[href*='page=']")
    max_page = 1
    for link in page_links:
        href = link.get("href", "")
        match = re.search(r"page=(\d+)", href)
        if match:
            page_num = int(match.group(1))
            max_page = max(max_page, page_num)

    # Also check aria-label or text content for page numbers
    for el in soup.find_all(string=re.compile(r"^\d+$")):
        parent = el.parent
        if parent and parent.name == "a" and parent.get("href", "").find("page=") >= 0:
            try:
                max_page = max(max_page, int(el.strip()))
            except ValueError:
                pass

    return max_page


# ---------------------------------------------------------------------------
# Main scraping logic
# ---------------------------------------------------------------------------


def scrape_reviews(max_pages: Optional[int] = None, start_page: int = 1,
                   filter_countries: bool = False) -> List[Dict]:
    """Scrape Klaviyo reviews from the Shopify App Store."""

    log.info("Fetching first page to determine total pages...")
    resp = fetch_page(BASE_URL, params={"page": 1})
    if not resp:
        log.error("Could not fetch the first review page. Exiting.")
        return []

    total_pages = get_total_pages(resp.text)
    log.info("Total review pages: %d", total_pages)

    end_page = total_pages
    if max_pages:
        end_page = min(start_page + max_pages - 1, total_pages)

    log.info("Scraping pages %d to %d", start_page, end_page)

    all_reviews = []
    consecutive_empty = 0

    for page_num in range(start_page, end_page + 1):
        log.info("[Page %d/%d] Fetching...", page_num, end_page)

        if page_num == 1 and start_page == 1:
            html = resp.text  # Reuse the first page we already fetched
        else:
            resp = fetch_page(BASE_URL, params={"page": page_num})
            if not resp:
                log.warning("Skipping page %d — fetch failed", page_num)
                consecutive_empty += 1
                if consecutive_empty >= 5:
                    log.error("5 consecutive failed pages — stopping")
                    break
                time.sleep(REQUEST_DELAY)
                continue

            html = resp.text

        reviews = parse_reviews_page(html)

        if not reviews:
            log.warning("No reviews found on page %d", page_num)
            consecutive_empty += 1
            if consecutive_empty >= 5:
                log.error("5 consecutive empty pages — stopping")
                break
        else:
            consecutive_empty = 0
            log.info("  Extracted %d reviews", len(reviews))

        all_reviews.extend(reviews)

        # Rate limiting
        if page_num < end_page:
            time.sleep(REQUEST_DELAY)

    log.info("Total reviews scraped: %d", len(all_reviews))
    return all_reviews


# ---------------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------------


def deduplicate_reviews(reviews: List[Dict]) -> List[Dict]:
    """Deduplicate reviews by store name (keep first occurrence)."""
    seen = set()
    unique = []
    for r in reviews:
        key = r["store_name"].lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(r)
    log.info("Deduplicated: %d → %d unique stores", len(reviews), len(unique))
    return unique


def filter_by_country(reviews: List[Dict]) -> List[Dict]:
    """Filter reviews to target markets (US, UK, AU, CA)."""
    filtered = [
        r for r in reviews
        if not r["country"] or r["country"].lower() in TARGET_COUNTRIES
    ]
    log.info("Country filter: %d → %d reviews", len(reviews), len(filtered))
    return filtered


# ---------------------------------------------------------------------------
# Domain discovery — store name → myshopify slug → real domain
# ---------------------------------------------------------------------------


def store_name_to_slugs(name: str) -> List[str]:
    """
    Generate candidate myshopify slugs from a store name.

    Examples:
        "Kitty Poo Club"   → ["kitty-poo-club"]
        "Dr. Clark Store"  → ["dr-clark-store", "drclarkstore", "dr-clark"]
        "anitaherbert.com" → ["anitaherbert"]
        "Sasshole®"        → ["sasshole"]
        "The Happy Plant"  → ["the-happy-plant", "happy-plant"]
        "L'Oréal Paris"   → ["loreal-paris", "lorealparis"]
    """
    # Strip common domain suffixes if the name looks like a domain
    name = re.sub(r"\.(com|co|net|org|io|store|shop|us|uk|au|ca)$", "", name, flags=re.IGNORECASE)

    # Lowercase and normalize unicode
    slug = name.lower().strip()

    # Replace accented chars with ASCII equivalents
    replacements = {
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "á": "a", "à": "a", "â": "a", "ä": "a", "ã": "a",
        "í": "i", "ì": "i", "î": "i", "ï": "i",
        "ó": "o", "ò": "o", "ô": "o", "ö": "o", "õ": "o",
        "ú": "u", "ù": "u", "û": "u", "ü": "u",
        "ñ": "n", "ç": "c",
    }
    for src, dst in replacements.items():
        slug = slug.replace(src, dst)

    # Remove all non-alphanumeric chars except spaces and hyphens
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)

    # Collapse whitespace/hyphens into single hyphens
    slug = re.sub(r"[\s-]+", "-", slug).strip("-")

    if not slug:
        return []

    slugs = [slug]

    # Variation: no hyphens (e.g., "drclarkstore")
    no_hyphens = slug.replace("-", "")
    if no_hyphens != slug:
        slugs.append(no_hyphens)

    # Variation: drop "the-" prefix
    if slug.startswith("the-"):
        slugs.append(slug[4:])

    # Variation: drop trailing "-store", "-shop", "-co", "-official"
    for suffix in ("-store", "-shop", "-co", "-official", "-us", "-uk"):
        if slug.endswith(suffix):
            trimmed = slug[:-len(suffix)]
            if trimmed and trimmed not in slugs:
                slugs.append(trimmed)

    return slugs


def probe_myshopify(slug: str, client: httpx.Client) -> Optional[str]:
    """
    Check if {slug}.myshopify.com is a valid Shopify store.
    Returns the final domain (custom or myshopify) if valid, None if not.
    """
    url = "https://{}.myshopify.com".format(slug)
    try:
        resp = client.get(url, headers=HEADERS)
        # A valid store returns 200 or redirects to a custom domain
        # A non-existent store returns 404 or a Shopify error page
        if resp.status_code in (200, 301, 302):
            final_url = str(resp.url)
            final_domain = extract_domain_from_url(final_url)

            # Check it's not a Shopify error/login page
            if "shopify.com/password" in final_url:
                # Password-protected store — still valid, use the myshopify domain
                return slug + ".myshopify.com"

            if final_domain and final_domain != "apps.shopify.com":
                return final_domain

        return None
    except (httpx.HTTPError, httpx.TimeoutException):
        return None


def discover_domains(reviews: List[Dict], delay: float = 1.0) -> int:
    """
    For each review without a domain, try to discover it by probing
    myshopify.com with slugs derived from the store name.

    Returns the number of domains discovered.
    """
    to_resolve = [r for r in reviews if not r["domain"]]
    if not to_resolve:
        log.info("All reviews already have domains")
        return 0

    log.info("Discovering domains for %d stores...", len(to_resolve))
    found = 0

    with httpx.Client(
        timeout=httpx.Timeout(10.0, connect=5.0),
        follow_redirects=True,
        max_redirects=5,
    ) as client:
        for i, review in enumerate(to_resolve):
            slugs = store_name_to_slugs(review["store_name"])
            if not slugs:
                log.debug("  [%d/%d] %s — no valid slugs", i + 1, len(to_resolve), review["store_name"])
                continue

            log.info("  [%d/%d] %s — trying %s",
                     i + 1, len(to_resolve), review["store_name"], ", ".join(slugs))

            for slug in slugs:
                domain = probe_myshopify(slug, client)
                if domain:
                    myshopify_url = "https://{}.myshopify.com".format(slug)
                    review["myshopify_url"] = myshopify_url

                    if "myshopify.com" not in domain:
                        review["domain"] = domain
                        log.info("    ✓ %s → %s", slug, domain)
                    else:
                        review["domain"] = ""
                        review["myshopify_url"] = myshopify_url
                        log.info("    ✓ %s (myshopify only, no custom domain)", slug)
                    found += 1
                    break
                time.sleep(0.5)  # Short delay between slug attempts

            time.sleep(delay)

    log.info("Domain discovery complete: found %d / %d", found, len(to_resolve))
    return found


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

CSV_COLUMNS = [
    "store_name",
    "domain",
    "myshopify_url",
    "review_date",
    "rating",
    "review_text",
    "country",
]


def export_csv(reviews: List[Dict], output_path: Path):
    """Export reviews to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(reviews)

    log.info("Exported %d reviews to %s", len(reviews), output_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scrape Klaviyo reviews from the Shopify App Store",
    )
    parser.add_argument("--max-pages", type=int, default=None,
                        help="Max number of pages to scrape (default: all)")
    parser.add_argument("--start-page", type=int, default=1,
                        help="Page number to start from (default: 1)")
    parser.add_argument("--filter-countries", action="store_true",
                        help="Only keep US, UK, AU, CA stores")
    parser.add_argument("--discover-domains", action="store_true",
                        help="Discover domains by probing {store-name}.myshopify.com")
    parser.add_argument("--output", type=str, default=None,
                        help="Output CSV path (default: output/shopify_klaviyo_leads_YYYY-MM-DD.csv)")
    parser.add_argument("--debug", action="store_true",
                        help="Print HTML structure of first page and exit")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable debug logging")
    return parser.parse_args()


def main():
    args = parse_args()

    # Logging setup
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Debug mode — print page structure and exit
    if args.debug:
        log.info("Debug mode: fetching first page to analyze structure...")
        resp = fetch_page(BASE_URL)
        if resp:
            debug_page_structure(resp.text)
        else:
            log.error("Could not fetch page for debugging")
        return

    # Scrape
    reviews = scrape_reviews(
        max_pages=args.max_pages,
        start_page=args.start_page,
        filter_countries=args.filter_countries,
    )

    if not reviews:
        log.warning("No reviews scraped. Run with --debug to inspect page structure.")
        return

    # Deduplicate
    reviews = deduplicate_reviews(reviews)

    # Country filter
    if args.filter_countries:
        reviews = filter_by_country(reviews)

    # Discover domains by probing myshopify.com
    if args.discover_domains:
        discover_domains(reviews)

    # Export
    if args.output:
        output_path = Path(args.output)
    else:
        today = datetime.now().strftime("%Y-%m-%d")
        output_path = OUTPUT_DIR / f"shopify_klaviyo_leads_{today}.csv"

    export_csv(reviews, output_path)

    # Summary
    with_domain = sum(1 for r in reviews if r["domain"])
    with_country = sum(1 for r in reviews if r["country"])
    print(f"\nDone! {len(reviews)} unique stores exported to {output_path}")
    print(f"  With domain: {with_domain}")
    print(f"  With country: {with_country}")


if __name__ == "__main__":
    main()
