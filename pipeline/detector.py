"""E-commerce technology detection — Klaviyo, Littledata, Elevar, and wetracked.io."""

from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup

log = logging.getLogger("pipeline.detector")


def detect_klaviyo(html: str, headers: dict | None = None) -> dict:
    """
    Check HTML (and optionally response headers) for Klaviyo signals.

    Returns:
        {
            "detected": bool,
            "signals": [{"type": str, "detail": str}, ...],
        }

    8 signals total:
      1. klaviyo_cdn_script     — static.klaviyo.com in <script src>
      2. klaviyo_script         — other "klaviyo" in <script src>
      3. learnq_variable        — _learnq in inline <script>
      4. klaviyo_api_endpoint   — a.klaviyo.com in inline <script>
      5. klaviyo_form_class     — .klaviyo-form in DOM
      6. window_klaviyo         — window.klaviyo / window["klaviyo"] in inline scripts
      7. kla_id_cookie          — __kla_id in Set-Cookie headers
      8. klaviyo_forms_event    — klaviyoForms event references in inline scripts
    """
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

    # 6: window.klaviyo or window["klaviyo"] in inline scripts
    for script in soup.find_all("script", src=False):
        text = script.string or ""
        if re.search(r'window\.klaviyo|window\[.klaviyo.\]', text, re.IGNORECASE):
            signals.append({"type": "window_klaviyo", "detail": "window.klaviyo reference found"})
            break

    # 7: __kla_id cookie in response Set-Cookie headers
    if headers:
        set_cookie = headers.get("set-cookie", "")
        if "__kla_id" in set_cookie:
            signals.append({"type": "kla_id_cookie", "detail": "__kla_id in Set-Cookie"})

    # 8: klaviyoForms event references in inline scripts
    for script in soup.find_all("script", src=False):
        text = script.string or ""
        if "klaviyoForms" in text:
            signals.append({"type": "klaviyo_forms_event", "detail": "klaviyoForms event reference"})
            break

    return {
        "detected": len(signals) > 0,
        "signals": signals,
    }


def detect_littledata(html: str) -> dict:
    """
    Check HTML for Littledata signals.

    Returns:
        {
            "detected": bool,
            "signals": [{"type": str, "detail": str}, ...],
        }

    4 signals:
      1. littledata_layer      — LittledataLayer variable in inline scripts
      2. littledata_script     — <script src> containing littledata
      3. littledata_domain     — littledata.io references in inline scripts
      4. littledata_app_embed  — Shopify app embed block containing littledata
    """
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
    if not any(s["type"] == "littledata_app_embed" for s in signals):
        for el in soup.find_all(attrs={"data-app": re.compile(r"littledata", re.IGNORECASE)}):
            signals.append({"type": "littledata_app_embed", "detail": f"data-app attribute: {el.get('data-app', '')}"})
            break

    return {
        "detected": len(signals) > 0,
        "signals": signals,
    }


def detect_elevar(html: str) -> dict:
    """
    Check HTML for Elevar signals.

    Returns:
        {
            "detected": bool,
            "signals": [{"type": str, "detail": str}, ...],
        }

    4 signals:
      1. elevar_datalayer   — window.ElevarDataLayer in inline scripts
      2. elevar_gtm_suite   — window.ElevarGtmSuite in inline scripts
      3. elevar_script      — <script src> containing elevar or getelevar
      4. elevar_domain      — getelevar.com references
    """
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


def detect_wetracked(html: str) -> dict:
    """
    Check HTML for wetracked.io signals.

    Returns:
        {
            "detected": bool,
            "signals": [{"type": str, "detail": str}, ...],
        }

    6 signals:
      1. wetracked_pixel_script  — pixel.wetracked.io in <script src>
      2. wetracked_script        — other "wetracked.io" in <script src>
      3. wetracked_inline_ref    — wetracked.io in inline <script>
      4. wetracked_wt_options    — wt:options variable in inline <script>
      5. wetracked_app_embed     — Shopify app embed block containing wetracked
      6. wetracked_woo_plugin    — wt-for-woocommerce in HTML
    """
    soup = BeautifulSoup(html, "html.parser")
    signals = []

    # 1: Script src containing pixel.wetracked.io
    for script in soup.find_all("script", src=True):
        src = script["src"]
        if "pixel.wetracked.io" in src.lower():
            signals.append({"type": "wetracked_pixel_script", "detail": src})

    # 2: Script src containing wetracked.io (other CDN variants)
    for script in soup.find_all("script", src=True):
        src = script["src"]
        if "wetracked.io" in src.lower() and "pixel.wetracked.io" not in src.lower():
            signals.append({"type": "wetracked_script", "detail": src})

    # 3: wetracked.io references in inline scripts
    for script in soup.find_all("script", src=False):
        text = script.string or ""
        if "wetracked.io" in text.lower():
            signals.append({"type": "wetracked_inline_ref", "detail": "wetracked.io reference found"})
            break

    # 4: wt:options variable in inline scripts
    for script in soup.find_all("script", src=False):
        text = script.string or ""
        if "wt:options" in text:
            signals.append({"type": "wetracked_wt_options", "detail": "wt:options reference found"})
            break

    # 5: Shopify app embed block containing wetracked
    for comment in soup.find_all(string=lambda t: isinstance(t, str) and "wetracked" in t.lower()):
        parent = comment.parent
        if parent and parent.name and parent.get("id", ""):
            if "app-embed" in parent.get("id", "").lower() or "app-block" in parent.get("id", "").lower():
                signals.append({"type": "wetracked_app_embed", "detail": f"Shopify app embed: {parent.get('id', '')}"})
                break
    if not any(s["type"] == "wetracked_app_embed" for s in signals):
        for el in soup.find_all(attrs={"data-app": re.compile(r"wetracked", re.IGNORECASE)}):
            signals.append({"type": "wetracked_app_embed", "detail": f"data-app attribute: {el.get('data-app', '')}"})
            break

    # 6: wt-for-woocommerce plugin reference in HTML
    if "wt-for-woocommerce" in html.lower():
        signals.append({"type": "wetracked_woo_plugin", "detail": "wt-for-woocommerce plugin detected"})

    return {
        "detected": len(signals) > 0,
        "signals": signals,
    }
