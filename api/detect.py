"""
E-commerce Technology Detection API — Vercel Serverless Function

GET /api/detect?domain=example.com

Fetches the website's HTML and checks for signals from:
- Klaviyo (email marketing)
- Littledata (data layer / analytics)
- Elevar (conversion tracking)
- Shopify (e-commerce platform)
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


def detect_littledata(html: str) -> dict:
    """Check HTML for Littledata-specific signals."""
    soup = BeautifulSoup(html, "html.parser")
    signals = []

    # 1: LittledataLayer variable in inline scripts
    for script in soup.find_all("script", src=False):
        text = script.string or ""
        if re.search(r"(window\.)?LittledataLayer", text):
            signals.append({"type": "littledata_layer", "detail": "LittledataLayer reference found"})
            break

    # 2: Script src containing littledata
    for script in soup.find_all("script", src=True):
        src = script["src"]
        if "littledata" in src.lower():
            signals.append({"type": "littledata_script", "detail": src})

    # 3: References to littledata.io in inline scripts
    for script in soup.find_all("script", src=False):
        text = script.string or ""
        if "littledata.io" in text.lower():
            signals.append({"type": "littledata_domain", "detail": "littledata.io reference found"})
            break

    # 4: Shopify app embed block containing littledata
    for comment in soup.find_all(string=lambda t: isinstance(t, str) and "littledata" in t.lower()):
        parent = comment.parent
        if parent and parent.name and parent.get("id", ""):
            if "app-embed" in parent.get("id", "").lower() or "app-block" in parent.get("id", "").lower():
                signals.append({"type": "littledata_app_embed", "detail": f"Shopify app embed: {parent.get('id', '')}"})
                break
    # Also check data attributes for littledata
    if not any(s["type"] == "littledata_app_embed" for s in signals):
        for el in soup.find_all(attrs={"data-app": re.compile(r"littledata", re.IGNORECASE)}):
            signals.append({"type": "littledata_app_embed", "detail": f"data-app attribute: {el.get('data-app', '')}"})
            break

    return {
        "detected": len(signals) > 0,
        "signals": signals,
    }


def detect_elevar(html: str) -> dict:
    """Check HTML for Elevar-specific signals."""
    soup = BeautifulSoup(html, "html.parser")
    signals = []

    # 1: ElevarDataLayer variable in inline scripts
    for script in soup.find_all("script", src=False):
        text = script.string or ""
        if "window.ElevarDataLayer" in text:
            signals.append({"type": "elevar_datalayer", "detail": "window.ElevarDataLayer reference found"})
            break

    # 2: ElevarGtmSuite variable in inline scripts
    for script in soup.find_all("script", src=False):
        text = script.string or ""
        if "window.ElevarGtmSuite" in text:
            signals.append({"type": "elevar_gtm_suite", "detail": "window.ElevarGtmSuite reference found"})
            break

    # 3: Script src containing elevar or getelevar
    for script in soup.find_all("script", src=True):
        src = script["src"]
        src_lower = src.lower()
        if "elevar" in src_lower or "getelevar" in src_lower:
            signals.append({"type": "elevar_script", "detail": src})

    # 4: References to getelevar.com in inline scripts or script src
    found_domain = False
    for script in soup.find_all("script", src=True):
        if "getelevar.com" in script["src"].lower():
            found_domain = True
            signals.append({"type": "elevar_domain", "detail": script["src"]})
            break
    if not found_domain:
        for script in soup.find_all("script", src=False):
            text = script.string or ""
            if "getelevar.com" in text.lower():
                signals.append({"type": "elevar_domain", "detail": "getelevar.com reference found"})
                break

    return {
        "detected": len(signals) > 0,
        "signals": signals,
    }


def detect_shopify(html: str, headers: dict | None = None) -> dict:
    """Check HTML (and optional response headers) for Shopify-specific signals."""
    soup = BeautifulSoup(html, "html.parser")
    signals = []

    # 1: Script or link src containing cdn.shopify.com
    for tag in soup.find_all(["script", "link"], src=True):
        src = tag["src"]
        if "cdn.shopify.com" in src.lower():
            signals.append({"type": "shopify_cdn", "detail": src})
            break
    if not any(s["type"] == "shopify_cdn" for s in signals):
        for link in soup.find_all("link", href=True):
            href = link["href"]
            if "cdn.shopify.com" in href.lower():
                signals.append({"type": "shopify_cdn", "detail": href})
                break

    # 2: window.Shopify or Shopify. variable in inline scripts
    for script in soup.find_all("script", src=False):
        text = script.string or ""
        if re.search(r"(window\.)?Shopify\s*[=.]", text):
            idx = text.index("Shopify")
            start = max(0, idx - 20)
            end = min(len(text), idx + 40)
            snippet = text[start:end].strip().replace("\n", " ")
            signals.append({"type": "shopify_variable", "detail": snippet})
            break

    # 3: References to myshopify.com
    for tag in soup.find_all(["meta", "link", "a", "script"], True):
        attrs_str = " ".join(str(v) for v in tag.attrs.values())
        text = tag.string or ""
        combined = attrs_str + " " + text
        if "myshopify.com" in combined.lower():
            signals.append({"type": "shopify_myshopify_domain", "detail": "myshopify.com reference found"})
            break

    # 4: shopify-section class in DOM elements
    section_el = soup.find(class_=re.compile(r"shopify-section"))
    if section_el:
        classes = " ".join(section_el.get("class", []))
        signals.append({"type": "shopify_section_class", "detail": classes})

    # 5: X-ShopId response header
    if headers:
        for hdr in ("x-shopid", "x-shopify-stage"):
            val = headers.get(hdr) or headers.get(hdr.title()) or headers.get(hdr.upper())
            if val:
                signals.append({"type": "shopify_header", "detail": f"{hdr}: {val}"})
                break

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
                    "uses_littledata": False,
                    "uses_elevar": False,
                    "uses_shopify": False,
                    "error": "Domain parameter is required",
                })

            domain = normalize_domain(raw_domain)
            if not domain:
                return _json_response(self, 400, {
                    "domain": raw_domain,
                    "uses_klaviyo": False,
                    "uses_littledata": False,
                    "uses_elevar": False,
                    "uses_shopify": False,
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
                    "uses_littledata": False,
                    "uses_elevar": False,
                    "uses_shopify": False,
                    "error": "Website timed out",
                })
            except httpx.HTTPError:
                return _json_response(self, 502, {
                    "domain": domain,
                    "uses_klaviyo": False,
                    "uses_littledata": False,
                    "uses_elevar": False,
                    "uses_shopify": False,
                    "error": "Could not fetch website",
                })

            content_type = resp.headers.get("content-type", "")
            if "html" not in content_type:
                return _json_response(self, 200, {
                    "domain": domain,
                    "uses_klaviyo": False,
                    "signals_matched": [],
                    "uses_littledata": False,
                    "littledata_signals": [],
                    "uses_elevar": False,
                    "elevar_signals": [],
                    "uses_shopify": False,
                    "shopify_signals": [],
                })

            html = resp.text
            resp_headers = dict(resp.headers)
            klaviyo_result = detect_klaviyo(html)
            littledata_result = detect_littledata(html)
            elevar_result = detect_elevar(html)
            shopify_result = detect_shopify(html, resp_headers)

            return _json_response(self, 200, {
                "domain": domain,
                "uses_klaviyo": klaviyo_result["detected"],
                "signals_matched": klaviyo_result["signals"],
                "uses_littledata": littledata_result["detected"],
                "littledata_signals": littledata_result["signals"],
                "uses_elevar": elevar_result["detected"],
                "elevar_signals": elevar_result["signals"],
                "uses_shopify": shopify_result["detected"],
                "shopify_signals": shopify_result["signals"],
            })

        except Exception:
            return _json_response(self, 500, {
                "domain": None,
                "uses_klaviyo": False,
                "uses_littledata": False,
                "uses_elevar": False,
                "uses_shopify": False,
                "error": "Internal error",
            })
