"""CLI orchestrator for the multi-source Klaviyo scraper pipeline."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from pipeline.config import OUTPUT_DIR
from pipeline.dedup import deduplicate
from pipeline.detector import detect_klaviyo, detect_wetracked
from pipeline.domain_discovery import discover_domains
from pipeline.enricher import enrich_from_html
from pipeline.exporter import export_csv, load_csv
from pipeline.http_client import RateLimitedClient
from pipeline.models import Lead
from pipeline.sources.base import BaseSource
from pipeline.sources.cro_media import CroMediaSource
from pipeline.sources.google_search import GoogleSearchSource
from pipeline.sources.myip_ms import MyIpMsSource
from pipeline.sources.shopify_adjacent_apps import ShopifyAdjacentAppsSource
from pipeline.sources.shopify_reviews import ShopifyReviewsSource
from pipeline.sources.store_lists import StoreListsSource
from pipeline.sources.tech_stack_pages import TechStackPagesSource
from pipeline.state import PipelineState

log = logging.getLogger("pipeline.runner")

# Registry of all available sources
ALL_SOURCES: dict[str, type[BaseSource]] = {
    "shopify_reviews": ShopifyReviewsSource,
    "cro_media": CroMediaSource,
    "store_lists": StoreListsSource,
    "tech_stack_pages": TechStackPagesSource,
    "shopify_adjacent_apps": ShopifyAdjacentAppsSource,
    "google_search": GoogleSearchSource,
    "myip_ms": MyIpMsSource,
}

# Default source order (high-value first)
DEFAULT_SOURCES = [
    "shopify_reviews",
    "shopify_adjacent_apps",
    "cro_media",
    "tech_stack_pages",
    "store_lists",
]


async def run_gather(
    sources: list[BaseSource],
    state: PipelineState,
    max_pages: int | None = None,
) -> list[Lead]:
    """Stage 1: Gather leads from all sources."""
    all_leads: list[Lead] = []

    async with RateLimitedClient() as client:
        for source in sources:
            log.info("=" * 60)
            log.info("GATHER: %s", source.name)
            log.info("=" * 60)

            try:
                leads = await source.gather(client, state, max_pages=max_pages)
                all_leads.extend(leads)
                state.append_leads([l.to_dict() for l in leads])
                log.info("Source %s: %d leads gathered", source.name, len(leads))
            except Exception as exc:
                log.error("Source %s failed: %s", source.name, exc, exc_info=True)

    return all_leads


async def run_verify(
    leads: list[Lead],
    state: PipelineState,
    max_verify: int | None = None,
) -> list[Lead]:
    """Stage 3: Verify Klaviyo usage by fetching and detecting."""
    to_verify = [l for l in leads if l.klaviyo_verified is None and l.domain]
    already_verified = [l for l in leads if l.klaviyo_verified is not None]

    if max_verify:
        to_verify = to_verify[:max_verify]

    log.info("Verifying %d domains (%d already verified)", len(to_verify), len(already_verified))

    verified_count = 0
    detected_count = 0

    async with RateLimitedClient() as client:
        for i, lead in enumerate(to_verify):
            log.info("[%d/%d] Verifying %s...", i + 1, len(to_verify), lead.domain)

            url = f"https://{lead.domain}/"
            html, resp = await client.get_with_response(url)

            if not html:
                lead.klaviyo_verified = False
                verified_count += 1
                continue

            # Detect Klaviyo
            headers = dict(resp.headers) if resp else {}
            result = detect_klaviyo(html, headers=headers)

            lead.klaviyo_verified = result["detected"]
            lead.klaviyo_signals = [s["type"] for s in result["signals"]]

            if result["detected"]:
                detected_count += 1
                log.info("  ✓ Klaviyo detected: %s", ", ".join(lead.klaviyo_signals))

            # Detect wetracked.io
            wt_result = detect_wetracked(html)
            lead.wetracked_detected = wt_result["detected"]
            lead.wetracked_signals = [s["type"] for s in wt_result["signals"]]

            if wt_result["detected"]:
                log.info("  ✓ wetracked.io detected: %s", ", ".join(lead.wetracked_signals))

            # Enrich from the same HTML (no extra requests)
            enrich_from_html(lead, html)

            verified_count += 1

    log.info(
        "Verification complete: %d verified, %d Klaviyo detected (%.1f%%)",
        verified_count, detected_count,
        (detected_count / verified_count * 100) if verified_count else 0,
    )

    state.update_counts(verified=verified_count + len(already_verified))
    return leads


async def run_pipeline(args):
    """Run the full pipeline: Gather → Dedup → Verify → Export."""
    # Determine state (new or resume)
    if args.resume:
        state = PipelineState.find_latest()
        if not state:
            log.error("No checkpoint found to resume from")
            return
        log.info("Resuming run: %s", state.run_id)
    else:
        state = PipelineState()
        log.info("Starting new run: %s", state.run_id)

    # Determine sources
    if args.sources:
        source_names = [s.strip() for s in args.sources.split(",")]
    else:
        source_names = DEFAULT_SOURCES

    # Add lower-priority sources if explicitly requested
    if args.all_sources:
        source_names = list(ALL_SOURCES.keys())

    sources = []
    for name in source_names:
        if name not in ALL_SOURCES:
            log.error("Unknown source: %s (available: %s)", name, ", ".join(ALL_SOURCES))
            return
        sources.append(ALL_SOURCES[name]())

    # Handle verify-only mode
    if args.verify_only:
        log.info("Verify-only mode: loading %s", args.verify_only)
        leads = load_csv(Path(args.verify_only))
        for lead in leads:
            lead.klaviyo_verified = None  # Force re-verification
        leads = await run_verify(leads, state, max_verify=args.max_verify)
        # Export only verified leads
        verified_leads = [l for l in leads if l.klaviyo_verified]
        output_path = export_csv(verified_leads, Path(args.output) if args.output else None)
        _print_summary(verified_leads, output_path)
        return

    # Stage 1: Gather
    if state.stage in ("gather", ""):
        log.info("=" * 60)
        log.info("STAGE 1: GATHER")
        log.info("=" * 60)
        leads = await run_gather(sources, state, max_pages=args.max_pages)
        state.stage = "dedup"
    else:
        # Load from checkpoint
        leads = [Lead.from_dict(d) for d in state.load_leads()]
        log.info("Loaded %d leads from checkpoint", len(leads))

    # Stage 2: Deduplicate
    if state.stage == "dedup":
        log.info("=" * 60)
        log.info("STAGE 2: DEDUPLICATE")
        log.info("=" * 60)
        leads = deduplicate(leads)
        state.stage = "discover"

    # Stage 2.5: Domain Discovery (resolve store names → domains)
    if state.stage == "discover":
        no_domain = sum(1 for l in leads if not l.domain)
        if no_domain > 0 and not args.skip_discovery:
            log.info("=" * 60)
            log.info("STAGE 2.5: DOMAIN DISCOVERY (%d leads without domains)", no_domain)
            log.info("=" * 60)
            async with RateLimitedClient() as client:
                await discover_domains(
                    leads, client, max_discover=args.max_discover,
                )
        else:
            log.info("Skipping domain discovery (%s)",
                     "no leads without domains" if no_domain == 0 else "--skip-discovery")
        state.stage = "verify"

    # Stage 3: Verify
    if state.stage == "verify":
        log.info("=" * 60)
        log.info("STAGE 3: VERIFY")
        log.info("=" * 60)
        leads = await run_verify(leads, state, max_verify=args.max_verify)
        state.stage = "export"

    # Stage 4: Export
    log.info("=" * 60)
    log.info("STAGE 4: EXPORT")
    log.info("=" * 60)

    # Export all leads (full dataset)
    output_path = export_csv(leads, Path(args.output) if args.output else None)

    # Also export verified-only subset
    verified_leads = [l for l in leads if l.klaviyo_verified]
    if verified_leads:
        verified_path = output_path.with_stem(output_path.stem + "_verified")
        export_csv(verified_leads, verified_path)

    state.update_counts(exported=len(leads))
    state.stage = "done"

    _print_summary(leads, output_path)


def _print_summary(leads: list[Lead], output_path: Path):
    """Print final summary stats."""
    total = len(leads)
    verified = sum(1 for l in leads if l.klaviyo_verified)
    wetracked = sum(1 for l in leads if l.wetracked_detected)
    with_domain = sum(1 for l in leads if l.domain)
    with_platform = sum(1 for l in leads if l.platform)

    sources_count: dict[str, int] = {}
    for l in leads:
        sources_count[l.source] = sources_count.get(l.source, 0) + 1

    print(f"\n{'=' * 60}")
    print(f"Pipeline Complete!")
    print(f"{'=' * 60}")
    print(f"  Total leads:       {total}")
    print(f"  Klaviyo verified:  {verified}")
    print(f"  wetracked.io:      {wetracked}")
    print(f"  With domain:       {with_domain}")
    print(f"  With platform:     {with_platform}")
    print(f"\n  By source:")
    for source, count in sorted(sources_count.items()):
        print(f"    {source}: {count}")
    print(f"\n  Output: {output_path}")
    print(f"{'=' * 60}\n")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Multi-source Klaviyo e-commerce company scraper",
    )
    parser.add_argument(
        "--sources", type=str, default=None,
        help="Comma-separated source names (default: shopify_reviews,cro_media,tech_stack_pages,store_lists)",
    )
    parser.add_argument(
        "--all-sources", action="store_true",
        help="Run all sources including lower-priority ones",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Resume from last checkpoint",
    )
    parser.add_argument(
        "--verify-only", type=str, default=None,
        help="Skip gathering, just verify domains from a CSV file",
    )
    parser.add_argument(
        "--max-pages", type=int, default=None,
        help="Max pages to scrape per source",
    )
    parser.add_argument(
        "--max-discover", type=int, default=None,
        help="Max number of store names to resolve to domains",
    )
    parser.add_argument(
        "--skip-discovery", action="store_true",
        help="Skip domain discovery stage",
    )
    parser.add_argument(
        "--max-verify", type=int, default=None,
        help="Max number of domains to verify",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output CSV path",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    asyncio.run(run_pipeline(args))


if __name__ == "__main__":
    main()
