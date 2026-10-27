#!/usr/bin/env python3
"""Merge a JSON dump produced by console/fb_scrape_console.js into the store.

The console snippet collects posts inside your logged-in tab but cannot write
image files (Chrome blocks bulk automatic downloads). This importer merges the
dump into data/posts.jsonl and then reuses the tested downloader to fetch the
images while the signed CDN URLs are still fresh.

Importing is a merge, not an append: a post seen again is reconciled with the
row already in the store (a full message replaces Facebook's "Altro..." preview,
a fresh image URL replaces an expired one) and only genuinely new posts are
added at the end.

Usage:
    python3 import_console_dump.py ~/Downloads/fb_posts_2026-10-24T....json
    python3 import_console_dump.py dump1.json dump2.json dump3.json
    python3 import_console_dump.py dump.json --media none
    python3 import_console_dump.py dump.json --media all

`--media none` needs nothing beyond Python 3.10+. Downloading images needs
`playwright` for its HTTP request client (see requirements.txt) — but no
browser and no Chrome profile.

Ids are recomputed with compute_id() from fbstore.py, so a re-import of the same
posts merges into the store without duplicates.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fbstore as fbs


def load_dump(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"no such file: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path.name} is not valid JSON: {exc}") from exc

    # Tolerate {posts: [...]} as well as a bare array.
    if isinstance(data, dict):
        data = data.get("posts", [])
    if not isinstance(data, list):
        raise SystemExit("expected a JSON array of posts (or {posts: [...]})")

    posts = [p for p in data if isinstance(p, dict)]
    if not posts:
        raise SystemExit("the dump contains no post objects")
    return posts


def normalise(posts: list[dict]) -> list[dict]:
    """Recompute ids and fill required fields so the rows match the tool's schema."""
    out: list[dict] = []
    for raw in posts:
        post = dict(raw)
        post["id"] = fbs.compute_id(post)
        post.setdefault("collected_at", fbs.now_iso())
        if not isinstance(post.get("media"), list):
            post["media"] = []
        out.append(post)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Merge DevTools-console dumps into posts.jsonl."
    )
    ap.add_argument(
        "dump",
        type=Path,
        nargs="+",
        help="JSON file(s) downloaded by fbScrape.saveJSON()",
    )
    ap.add_argument(
        "--jsonl",
        type=Path,
        default=fbs.JSONL_PATH,
        help=f"target store (default: {fbs.JSONL_PATH})",
    )
    ap.add_argument(
        "--media",
        choices=["none", "images", "all"],
        default="images",
        help="download images for the imported posts (default: images)",
    )
    ap.add_argument("--media-timeout", type=int, default=30000, help="per-file download timeout in ms")
    ap.add_argument("--max-media-mb", type=int, default=50, help="skip individual files larger than this")
    args = ap.parse_args(argv)

    target: Path = args.jsonl.expanduser()

    rows: list[dict] = []
    for dump in args.dump:
        rows.extend(normalise(load_dump(dump.expanduser())))

    existing = fbs.load_rows(target)
    excluded = fbs.load_exclusions()
    report = fbs.merge_posts(existing, rows, excluded)

    print(f"dump      : {len(args.dump)} file(s), {len(rows)} posts")
    print(f"in store  : {len(existing) - report['appended']} rows before")
    if report["skipped"]:
        print(f"skipped   : {report['skipped']} posts removed on purpose (data/excluded.json)")
    if report["duplicates"]:
        print(f"repeats   : {report['duplicates']} posts captured twice in the dumps")
    if report["matched"]:
        how = ", ".join(f"{n} by {k}" for k, n in sorted(report["matched"].items()))
        print(f"matched   : {sum(report['matched'].values())} already stored ({how})")
        print(f"updated   : {report['updated']} rows, {report['unchanged']} already complete")
        if report["fields"]:
            fields = ", ".join(f"{k} {n}" for k, n in report["fields"].most_common())
            print(f"  changed : {fields}")
    print(f"new       : {report['appended']} posts appended")

    written = fbs.write_jsonl(target, existing)
    csv_path = target.with_suffix(".csv")
    fbs.export_csv(target, csv_path)
    print(f"jsonl     : {target}  ({written} rows)")
    print(f"csv       : {csv_path}")

    if args.media == "none":
        return 0

    # Playwright's request client needs no browser; it gives us the same .get()
    # surface the downloader already uses.
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit(
            "Downloading the images needs playwright (no browser involved):\n"
            "  python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt\n"
            "or import the posts only with --media none."
        )

    with sync_playwright() as pw:
        http = pw.request.new_context(
            extra_http_headers={"Referer": "https://www.facebook.com/"}
        )
        try:
            fbs.backfill_media(http, args, target)  # type: ignore[arg-type]
        finally:
            http.dispose()

    print(f"media dir : {fbs.MEDIA_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
