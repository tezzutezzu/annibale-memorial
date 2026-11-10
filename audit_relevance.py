#!/usr/bin/env python3
"""List the memories the site shows, and flag the ones that look like noise.

The slideshow hides `relevant: false` and shows everything else, so a row that
was never judged — a search result, a page post — reaches the screen on trust.
This script reads the store the way the page does (`relevant !== false`) and
sorts those rows into the cases that can be decided by a rule and the ones that
need a person to read them.

    python3 audit_relevance.py                    # rules, then the rest
    python3 audit_relevance.py --ids --rule all   # ids only, for remove_posts.py
    python3 audit_relevance.py --csv /tmp/review.csv

Rules are only ever a first pass: `remove_posts.py` deletes for good and records
the id in data/excluded.json, so a rule may point at a row but must not decide
for it. Text cut at "Altro…" is never a candidate — that is repaired by a second
capture, not removed (see audit_truncated.py).
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fbstore as fbs

# A greeting on its own says nothing about Annibale: "Buon compleanno!",
# "Auguroni Annibale", "Ciao Annibale.\nGrazie.". Checked word by word, so a
# birthday wish with a memory inside it is not caught.
GREETING_WORDS = {
    "buon", "buona", "buongiorno", "buonasera", "compleanno", "auguri", "auguroni",
    "augurissimo", "tanti", "tantissimi", "mille", "happy", "birthday", "grazie",
    "ciao", "a", "te", "e", "anche", "di", "cuore", "con", "affetto", "un", "grande",
}
NAME_RE = re.compile(r"annibal|d['’`´]?\s?elia", re.IGNORECASE)
MEMORY_RE = re.compile(
    r"te ne (?:sia|sei) andat|non ti rivedr|mancherai|mi manchi|condoglianz|"
    r"bollenti spiriti|principi attivi|ritorno al futuro|camera ardente|funerale|"
    r"scompars|prematura|lutto|ricord|abbracc|non ci credo|se ne va",
    re.IGNORECASE,
)


def normalise(text: str | None) -> str:
    return " ".join((text or "").split()).lower()


def text_of(row: dict) -> str:
    return (row.get("text") or "") + " " + (row.get("shared_text") or "")


def is_visible(row: dict) -> bool:
    """The page's own rule: only an explicit `false` hides a row."""
    return row.get("relevant") is not False


def is_greeting(text: str) -> bool:
    """True when the whole message is a greeting: no content beyond hello and its name."""
    body = NAME_RE.sub(" ", normalise(text))
    words = re.findall(r"[a-zàèéìòù']+", body)
    return bool(words) and len(words) <= 6 and set(words) <= GREETING_WORDS


def judge(row: dict, seen: dict[str, str]) -> tuple[str | None, str]:
    """(rule, why) when a rule settles it, else (None, the reading note)."""
    text = text_of(row).strip()
    body = normalise(text)
    photos = len(row.get("media") or [])

    if not body and not photos:
        return "empty", "no text and no photo"

    if fbs.looks_truncated(row.get("text")) or fbs.looks_truncated(row.get("shared_text")):
        return None, "cut at Altro: repair with a new capture, never remove"

    if not body:
        return None, f"photo only ({photos}), no caption: look at it"

    # A greeting that names him ("Buon compleanno, Annibale!") is still only a
    # greeting: the name alone does not make a memory.
    if is_greeting(text):
        return "greeting", "only a greeting"

    key = body
    if key in seen:
        return "duplicate", f"same message as {seen[key]}"
    seen[key] = str(row.get("id"))

    if not NAME_RE.search(text) and not MEMORY_RE.search(text) and len(body) <= 25:
        return "short", f"{len(body)} chars, no name, no memory word"

    return None, "read it"


def collect(rows: list[dict], only_visible: bool) -> list[dict]:
    out: list[dict] = []
    seen: dict[str, str] = {}
    for row in rows:
        if only_visible and not is_visible(row):
            continue
        rule, why = judge(row, seen)
        text = text_of(row).strip()
        out.append(
            {
                "id": row.get("id") or "",
                "author": row.get("author") or "",
                "date": row.get("time_text") or "",
                "flag": str(row.get("relevant")),
                "source": row.get("source") or "",
                "chars": len(text),
                "media": len(row.get("media") or []),
                "rule": rule or "",
                "why": why,
                "excerpt": " ".join(text.split())[:330],
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Find the rows that should be read before showing.")
    ap.add_argument("--jsonl", type=Path, default=fbs.JSONL_PATH, help="store to read")
    ap.add_argument("--all", action="store_true", help="include rows already hidden by relevant:false")
    ap.add_argument("--csv", type=Path, default=None, help="write the full review sheet here")
    ap.add_argument("--ids", action="store_true", help="print only the ids a rule flags")
    ap.add_argument("--rule", default="all", choices=["all", "greeting", "short", "empty", "duplicate", "none"],
                    help="which rule to list with --ids (none = everything to read)")
    ap.add_argument("--excerpts", action="store_true", help="print the rows to read, in batches")
    ap.add_argument("--offset", type=int, default=0, help="skip the first N rows with --excerpts")
    ap.add_argument("--limit", type=int, default=0, help="show at most N rows (0 = all)")
    args = ap.parse_args(argv)

    store = args.jsonl.expanduser()
    rows = fbs.load_rows(store)
    entries = collect(rows, only_visible=not args.all)
    flagged = [e for e in entries if e["rule"]]
    reading = [e for e in entries if not e["rule"]]

    if args.csv:
        path = args.csv.expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(entries[0].keys()) if entries else ["id"])
            writer.writeheader()
            writer.writerows(entries)
        print(f"report    : {path}  ({len(entries)} rows)")

    if args.ids:
        wanted = flagged if args.rule != "none" else reading
        if args.rule not in ("all", "none"):
            wanted = [e for e in flagged if e["rule"] == args.rule]
        for entry in wanted:
            print(entry["id"])
        return 0

    if args.excerpts:
        batch = reading[args.offset:]
        if args.limit:
            batch = batch[: args.limit]
        for n, e in enumerate(batch, start=args.offset + 1):
            meta = f"{e['author'] or '?'} · {e['date'] or 'no date'} · {e['source'] or '?'} · {e['media']} img"
            print(f"[{n}/{len(reading)}] {e['id']}  ({meta})")
            print(f"    {e['excerpt']}")
            if e["chars"] > len(e["excerpt"]):
                print(f"    … +{e['chars'] - len(e['excerpt'])} chars")
        print(f"\nrows {args.offset + 1}-{args.offset + len(batch)} of {len(reading)} to read")
        return 0

    print(f"store     : {store}  ({len(rows)} rows)")
    print(f"shown     : {len(entries)} ({'all rows' if args.all else 'relevant is not false'})")
    print(f"by rule   : " + ", ".join(
        f"{name}={sum(1 for e in flagged if e['rule'] == name)}"
        for name in ("greeting", "short", "empty", "duplicate")
    ))
    print(f"to read   : {len(reading)}")
    print(f"cut short : {sum(1 for e in entries if e['why'].startswith('cut at Altro'))}"
          " (repair with a new capture, do not remove)")

    def show(title: str, items: list[dict]) -> None:
        if not items:
            return
        print(f"\n{title}")
        for e in items[: args.limit or None]:
            print(f"  {e['id']:<22} {e['author'][:20]:<20} {e['chars']:>4}ch {e['media']}img  {e['why']}")

    show("rule: only a greeting", [e for e in flagged if e["rule"] == "greeting"])
    show("rule: too short to be a memory", [e for e in flagged if e["rule"] == "short"])
    show("rule: nothing in it", [e for e in flagged if e["rule"] == "empty"])
    show("rule: duplicate message", [e for e in flagged if e["rule"] == "duplicate"])

    if not args.limit:
        show("to read", reading)
    elif reading:
        print(f"\nto read   : {len(reading)} rows (--limit shows {args.limit})")

    print("\nA rule only lists; the deletion is a decision. Read the row, then")
    print("python3 remove_posts.py <id>… --reason \"controllo rilevanza: non pertinente\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
