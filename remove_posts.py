#!/usr/bin/env python3
"""Take posts out of the store, and record them so no later import brings them back.

Removing a row is not enough: the dump it came from is still on disk, so the
next import of that dump would append the post again. Every removal is therefore
written to data/excluded.json, which `import_console_dump.py` skips over.

Usage:
    python3 remove_posts.py h_65d848f4ffc2d335
    python3 remove_posts.py h_0000 fb_10237650532620953 --reason "auguri di compleanno"
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fbstore as fbs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Remove posts from the store for good.")
    ap.add_argument("ids", nargs="+", help="post ids, as they appear in the URL (#<id>)")
    ap.add_argument("--reason", default="", help="why they are not memories (kept in excluded.json)")
    ap.add_argument("--jsonl", type=Path, default=fbs.JSONL_PATH, help="store to edit")
    ap.add_argument("--excluded", type=Path, default=fbs.EXCLUDED_PATH, help="exclusion list to extend")
    args = ap.parse_args(argv)

    store: Path = args.jsonl.expanduser()
    rows = fbs.load_rows(store)
    by_id = {r.get("id"): r for r in rows}

    unknown = [i for i in args.ids if i not in by_id]
    if unknown:
        raise SystemExit(f"not in {store.name}: {', '.join(unknown)}")

    entries = fbs.read_exclusions(args.excluded.expanduser())
    known = {e.get("id") for e in entries}
    removed: list[dict] = []

    for pid in args.ids:
        row = by_id[pid]
        removed.append(row)
        if pid not in known:
            entries.append(
                {
                    "id": pid,
                    "author": row.get("author"),
                    "message": (row.get("text") or "")[:200],
                    "removed_at": fbs.now_iso(),
                    "reason": args.reason,
                }
            )

    fbs.write_jsonl(store, [r for r in rows if r.get("id") not in set(args.ids)])
    fbs.export_csv(store, store.with_suffix(".csv"))
    fbs.write_exclusions(entries, args.excluded.expanduser())

    # The same memory can be stored twice (a truncated "Altro..." preview under
    # one id, the full text under another). Say so instead of leaving a copy on
    # screen that the next import would happily keep.
    removed_keys = {fbs.message_key(r) for r in removed}
    left_behind = [
        r["id"] for r in rows if r.get("id") not in set(args.ids) and fbs.message_key(r)[1] and fbs.message_key(r) in removed_keys
    ]

    for row in removed:
        folder = fbs.MEDIA_DIR / str(row["id"])
        if folder.is_dir():
            files = [p for p in folder.rglob("*") if p.is_file()]
            shutil.rmtree(folder)
            print(f"  {row['id']}: removed row and {len(files)} file(s)")
        else:
            print(f"  {row['id']}: removed row, no media")

    if left_behind:
        print(f"\nwarn      : the same message is still stored as {', '.join(left_behind)}")
        print("            remove those ids too if it should leave the slideshow")

    print(f"store     : {store}  ({len(rows) - len(removed)} rows)")
    print(f"excluded  : {args.excluded.expanduser()}  ({len(entries)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
