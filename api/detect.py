"""
Klaviyo Detection API — Vercel Serverless Function

GET /api/detect?domain=example.com

Fetches the website's HTML and checks for Klaviyo-specific signals:
- Script tags loading from static.klaviyo.com or containing "klaviyo"
- _learnq variable (Klaviyo's legacy tracking object) in inline scripts
- References to a.klaviyo.com (Klaviyo API endpoint)
- .klaviyo-form class in the DOM
"""

import json
import re
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

import httpx
from bs4 import BeautifulSoup

_DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
    r"[a-zA-Z]{2,63}$"
)

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


def detect_klaviyo(html: str) -> bool:
    """Check HTML for Klaviyo-specific signals."""
    soup = BeautifulSoup(html, "html.parser")

    # 1 & 2: Script src containing klaviyo
    for script in soup.find_all("script", src=True):
        src = script["src"].lower()
        if "static.klaviyo.com" in src or "klaviyo" in src:
            return True

    # 3 & 4: Inline scripts referencing _learnq or a.klaviyo.com
    for script in soup.find_all("script", src=False):
        text = script.string or ""
        if "_learnq" in text or "a.klaviyo.com" in text:
            return True

    # 5: .klaviyo-form class in DOM
    if soup.find(class_=re.compile(r"klaviyo-form")):
        return True

    return False


def _json_response(handler, status: int, body: dict):
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(json.dumps(body).encode())


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            query = parse_qs(urlparse(self.path).query)
            raw_domain = query.get("domain", [None])[0]

            if not raw_domain:
                return _json_response(self, 400, {
                    "domain": None,
                    "uses_klaviyo": False,
                    "error": "Domain parameter is required",
                })

            domain = normalize_domain(raw_domain)
            if not domain:
                return _json_response(self, 400, {
                    "domain": raw_domain,
                    "uses_klaviyo": False,
                    "error": "Invalid domain format",
                })

            url = f"https://{domain}/"
            try:
                with httpx.Client(
                    timeout=httpx.Timeout(8.0, connect=5.0),
                    follow_redirects=True,
                    max_redirects=5,
                ) as client:
                    resp = client.get(url, headers=HEADERS)
            except httpx.TimeoutException:
                return _json_response(self, 504, {
                    "domain": domain,
                    "uses_klaviyo": False,
                    "error": "Website timed out",
                })
            except httpx.HTTPError:
                return _json_response(self, 502, {
                    "domain": domain,
                    "uses_klaviyo": False,
                    "error": "Could not fetch website",
                })

            content_type = resp.headers.get("content-type", "")
            if "html" not in content_type:
                return _json_response(self, 200, {
                    "domain": domain,
                    "uses_klaviyo": False,
                })

            uses_klaviyo = detect_klaviyo(resp.text)
            return _json_response(self, 200, {
                "domain": domain,
                "uses_klaviyo": uses_klaviyo,
            })

        except Exception:
            return _json_response(self, 500, {
                "domain": None,
                "uses_klaviyo": False,
                "error": "Internal error",
            })
