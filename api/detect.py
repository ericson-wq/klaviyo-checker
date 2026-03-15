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


def detect_klaviyo(html: str) -> dict:
    """Check HTML for Klaviyo-specific signals. Returns dict with result and matched signals."""
    soup = BeautifulSoup(html, "html.parser")
    signals = []

    # 1: Script src containing static.klaviyo.com
    for script in soup.find_all("script", src=True):
        src = script["src"]
        if "static.klaviyo.com" in src.lower():
            signals.append({"type": "klaviyo_cdn_script", "detail": src})

    # 2: Script src containing klaviyo (other CDN variants)
    for script in soup.find_all("script", src=True):
        src = script["src"]
        if "klaviyo" in src.lower() and "static.klaviyo.com" not in src.lower():
            signals.append({"type": "klaviyo_script", "detail": src})

    # 3: _learnq variable in inline scripts
    for script in soup.find_all("script", src=False):
        text = script.string or ""
        if "_learnq" in text:
            # Extract a short snippet around the match
            idx = text.index("_learnq")
            start = max(0, idx - 20)
            end = min(len(text), idx + 40)
            snippet = text[start:end].strip().replace("\n", " ")
            signals.append({"type": "learnq_variable", "detail": snippet})
            break

    # 4: References to a.klaviyo.com in inline scripts
    for script in soup.find_all("script", src=False):
        text = script.string or ""
        if "a.klaviyo.com" in text:
            signals.append({"type": "klaviyo_api_endpoint", "detail": "a.klaviyo.com"})
            break

    # 5: .klaviyo-form class in DOM
    form_el = soup.find(class_=re.compile(r"klaviyo-form"))
    if form_el:
        classes = " ".join(form_el.get("class", []))
        signals.append({"type": "klaviyo_form_class", "detail": classes})

    return {
        "detected": len(signals) > 0,
        "signals": signals,
    }


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
                    "signals_matched": [],
                })

            result = detect_klaviyo(resp.text)
            return _json_response(self, 200, {
                "domain": domain,
                "uses_klaviyo": result["detected"],
                "signals_matched": result["signals"],
            })

        except Exception:
            return _json_response(self, 500, {
                "domain": None,
                "uses_klaviyo": False,
                "error": "Internal error",
            })
