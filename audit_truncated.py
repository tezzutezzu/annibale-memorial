#!/usr/bin/env python3
"""List the memories Facebook cut at "Altro…", so they can be completed or removed.

A capture taken before the console scraper learned to expand the "Altro" button
stores the preview instead of the whole message: the text stops at an ellipsis.
Those rows are not broken, they are incomplete, and the fix is a second capture
(`import_console_dump.py` replaces a preview with a longer text, see
`fbstore.reconcile_row`). This script says which ones still need that.

    python3 audit_truncated.py                     # summary and every row
    python3 audit_truncated.py --ids               # ids only, for remove_posts.py
    python3 audit_truncated.py --csv /tmp/cut.csv  # full report for a spreadsheet

Truncation is decided by `fbstore.looks_truncated`, the same rule the import
uses, so what is listed here is exactly what a new capture would repair.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fbstore as fbs


def audit(rows: list[dict]) -> list[dict]:
    """One entry per row with a cut message, carrying what decides what to do with it."""
    out: list[dict] = []
    for row in rows:
        text = row.get("text") or ""
        shared = row.get("shared_text") or ""
        cut_text = fbs.looks_truncated(text)
        cut_shared = fbs.looks_truncated(shared)
        if not (cut_text or cut_shared):
            continue
        permalink = (row.get("permalink") or "").strip()
        cut = text if cut_text else shared
        out.append(
            {
                "id": row.get("id") or "",
                "author": row.get("author") or "",
                "chars": len(cut.strip()),
                "where": "text" if cut_text else "shared",
                "permalink": "" if permalink in ("", "#") else permalink,
                "media": len(row.get("media") or []),
                "tail": " ".join(cut.split())[-70:],
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Find memories cut short by Facebook.")
    ap.add_argument("--jsonl", type=Path, default=fbs.JSONL_PATH, help="store to read")
    ap.add_argument("--excluded", type=Path, default=fbs.EXCLUDED_PATH, help="exclusion list, to mark what is already out")
    ap.add_argument("--ids", action="store_true", help="print only the ids, one per line")
    ap.add_argument("--csv", type=Path, default=None, help="write the full report here")
    ap.add_argument("--limit", type=int, default=0, help="show at most N rows (0 = all)")
    args = ap.parse_args(argv)

    store = args.jsonl.expanduser()
    rows = fbs.load_rows(store)
    found = audit(rows)
    excluded = fbs.load_exclusions(args.excluded.expanduser())
    by_id = {row.get("id"): row for row in rows}
    already_out = {e["id"] for e in found if by_id.get(e["id"]) in excluded}

    if args.csv:
        path = args.csv.expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=["id", "author", "chars", "where", "permalink", "media", "tail"])
            writer.writeheader()
            writer.writerows(found)
        print(f"report    : {path}  ({len(found)} rows)")

    if args.ids:
        for entry in found:
            print(entry["id"])
        return 0

    linkable = [e for e in found if e["permalink"]]
    print(f"store     : {store}  ({len(rows)} rows)")
    print(f"cut short : {len(found)} ({len(found) * 100 / max(len(rows), 1):.0f}% of the store)")
    print(f"  in text : {sum(1 for e in found if e['where'] == 'text')}")
    print(f"  in a share: {sum(1 for e in found if e['where'] == 'shared')}")
    print(f"  with a permalink, so it can be reopened and completed: {len(linkable)}")
    print(f"  without a permalink (search the author on Facebook):   {len(found) - len(linkable)}")
    print(f"  with photos: {sum(1 for e in found if e['media'])}")
    print(f"  already excluded: {len(already_out)}")
    shown = found if not args.limit else found[: args.limit]
    if shown:
        print()
        for entry in shown:
            marker = "!" if entry["id"] in already_out else " "
            link = "link" if entry["permalink"] else "    "
            print(
                f"{marker} {entry['id']:<22} {entry['chars']:>4}ch {entry['where']:<6} {link} img={entry['media']}"
                f"  {entry['author'][:24]:<24} …{entry['tail']}"
            )
    if shown and len(shown) < len(found):
        print(f"\n... {len(found) - len(shown)} more (raise --limit)")

    print("\nA preview is repaired, not removed: capture the post again with Altro expanded")
    print("and import the dump, and the longer text replaces the cut one.")
    print("Careful with removal: a post with a permalink keeps its id, so putting it in")
    print("data/excluded.json means the complete version can never be imported later.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
