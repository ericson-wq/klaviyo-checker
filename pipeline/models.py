"""Lead data model for the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class Lead:
    """A single e-commerce company lead."""

    domain: str  # Primary dedup key (normalized)
    store_name: str
    source: str  # e.g. "shopify_reviews", "cro_media"
    myshopify_url: str = ""
    country: str = ""
    platform: str = ""  # "shopify", "woocommerce", "bigcommerce"
    klaviyo_verified: bool | None = None
    klaviyo_signals: list[str] = field(default_factory=list)
    wetracked_detected: bool | None = None
    wetracked_signals: list[str] = field(default_factory=list)
    discovered_at: str = field(default_factory=lambda: datetime.now().isoformat())
    review_date: str = ""
    rating: str = ""
    review_text: str = ""
    meta_title: str = ""
    meta_description: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["klaviyo_signals"] = "|".join(d["klaviyo_signals"])
        d["wetracked_signals"] = "|".join(d["wetracked_signals"])
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Lead":
        if isinstance(d.get("klaviyo_signals"), str):
            d["klaviyo_signals"] = [s for s in d["klaviyo_signals"].split("|") if s]
        if isinstance(d.get("klaviyo_verified"), str):
            v = d["klaviyo_verified"].lower()
            d["klaviyo_verified"] = True if v == "true" else (False if v == "false" else None)
        if isinstance(d.get("wetracked_signals"), str):
            d["wetracked_signals"] = [s for s in d["wetracked_signals"].split("|") if s]
        if isinstance(d.get("wetracked_detected"), str):
            v = d["wetracked_detected"].lower()
            d["wetracked_detected"] = True if v == "true" else (False if v == "false" else None)
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
