#!/usr/bin/env python3
"""Merge the thoughts left on the site into the store.

Visitors write from a Tally form embedded in `index.html`; the owner reviews the
submissions in Tally's dashboard and exports the approved ones as CSV. This
script turns those rows into memories, exactly like a Facebook capture:

    ./.venv/bin/python import_thoughts.py ~/Downloads/tally-export.csv
    ./.venv/bin/python import_thoughts.py export.csv --dry-run

- the photo attached to a thought is downloaded into `data/media/<id>/`, so the
  site keeps working after Tally's links expire;
- a row already in the store is matched by author + opening words, so running
  the same export twice does not duplicate anything;
- the email address is never written to the store: it only exists in Tally.

Column names are the form's question labels (Italian or English); `Approved`
and `Consent` columns, when present, filter out rows that must not be
published.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fbstore as fbs

MONTHS = [
    "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
    "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
]

# Aliases are compared against the normalised header: lower case, punctuation
# turned into single spaces.
COLUMNS = {
    "author": ("nome", "name", "firma", "autore"),
    "text": ("pensiero", "messaggio", "message", "testo"),
    "photo": ("foto", "photo", "immagine", "image", "upload", "allegato"),
    "submitted": ("submitted at", "data invio", "inviato il", "timestamp", "created at"),
    "email": ("email", "e mail", "mail"),
    "approved": ("approvato", "approvata", "approved", "pubblica", "publish"),
    "consent": ("consenso", "consent", "acconsento", "accetto", "privacy"),
}

YES = {"si", "sì", "yes", "y", "true", "1", "x", "ok", "approvato", "pubblicare"}


def _norm(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").casefold()).strip()


def _pick_columns(headers: list[str]) -> dict[str, str]:
    """Map our roles to the CSV's headers, exact names before fuzzy ones."""
    picked: dict[str, str] = {}
    normalised = {h: _norm(h) for h in headers}
    taken: set[str] = set()

    for role, aliases in COLUMNS.items():
        for header, key in normalised.items():
            if header in taken:
                continue
            if key in aliases:
                picked[role] = header
                taken.add(header)
                break

    for role, aliases in COLUMNS.items():
        if role in picked:
            continue
        for header, key in normalised.items():
            if header in taken:
                continue
            if any(alias in key for alias in aliases):
                picked[role] = header
                taken.add(header)
                break
    return picked


def _truthy(value: str | None) -> bool:
    return _norm(value) in YES


def _parse_when(value: str | None) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _date_label(value: str | None) -> str | None:
    """Facebook-style Italian date the site already knows how to show."""
    when = _parse_when(value)
    if not when:
        return None
    return f"{when.day} {MONTHS[when.month - 1]} {when.year}"


def _photo_url(cell: str | None) -> str:
    for token in re.split(r"[\s,;]+", cell or ""):
        if token.startswith(("http://", "https://")):
            return token
    return ""


def _local_photo(cell: str | None, folder: Path) -> Path | None:
    name = Path((cell or "").strip()).name
    if not name:
        return None
    candidate = folder / name
    return candidate if candidate.exists() else None


def _media_item(cell: str | None) -> dict:
    url = _photo_url(cell)
    return {"type": "image", "url": url, "alt": ""} if url else {}


def build_row(author: str, text: str, date_label: str | None, media: dict) -> dict:
    digest = hashlib.sha1(f"{author}\n{text}\n{date_label or ''}".encode("utf-8")).hexdigest()[:8]
    return {
        "id": f"site_{digest}",
        "collected_at": fbs.now_iso(),
        "author": author,
        "author_url": None,
        "time_text": date_label,
        "permalink": None,
        "reactions": None,
        "reactions_summary": None,
        "comments": None,
        "shares": None,
        "is_ad": False,
        "posinset": None,
        "shared_author": None,
        "shared_text": None,
        "text": text,
        "media": [media] if media else [],
        "relevant": True,
        "source": "site",
    }


def read_export(path: Path, photo_dir: Path) -> tuple[list[dict], dict]:
    """Rows that may be published, plus a count of what was left out and why."""
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        headers = list(reader.fieldnames or [])
        cols = _pick_columns(headers)
        missing = [r for r in ("author", "text") if r not in cols]
        if missing:
            raise SystemExit(
                f"{path.name}: colonna mancante per {', '.join(missing)}.\n"
                f"intestazioni trovate: {', '.join(headers) or '(nessuna)'}"
            )

        rows: list[dict] = []
        stats = {"total": 0, "unapproved": 0, "no_consent": 0, "incomplete": 0}
        for raw in reader:
            stats["total"] += 1
            if "approved" in cols and not _truthy(raw.get(cols["approved"])):
                stats["unapproved"] += 1
                continue
            if "consent" in cols and not _truthy(raw.get(cols["consent"])):
                stats["no_consent"] += 1
                continue

            author = (raw.get(cols["author"]) or "").strip()
            text = (raw.get(cols["text"]) or "").strip()
            if not author or not text:
                stats["incomplete"] += 1
                continue

            photo_cell = raw.get(cols["photo"]) if "photo" in cols else ""
            media = _media_item(photo_cell)
            if not media:
                local = _local_photo(photo_cell, photo_dir)
                if local:
                    media = {"type": "image", "url": "", "_file": str(local)}

            when = raw.get(cols["submitted"]) if "submitted" in cols else ""
            rows.append(build_row(author, text, _date_label(when), media))

    return rows, stats


def attach_local_photos(posts: list[dict], dry_run: bool) -> int:
    """Move a photo sitting next to the CSV into the store's media folder."""
    moved = 0
    for post in posts:
        for item in post.get("media") or []:
            source = item.pop("_file", None)
            if not source:
                continue
            src = Path(source)
            dest = fbs.MEDIA_DIR / str(post["id"])
            target = dest / src.name
            if not dry_run:
                dest.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    shutil.copy2(src, target)
            item["local_path"] = target.relative_to(fbs.ROOT).as_posix()
            moved += 1
    return moved


def download_photos(posts: list[dict], timeout_ms: int, max_bytes: int) -> int:
    """Fetch the uploaded images before Tally's links expire."""
    pending = [
        p for p in posts
        if any(m.get("url") and not m.get("local_path") for m in (p.get("media") or []))
    ]
    if not pending:
        return 0

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "! playwright non installato: le foto restano collegate all'URL di Tally\n"
            "  (./.venv/bin/pip install -r requirements.txt, poi rilancia lo script)"
        )
        return 0

    files = 0
    with sync_playwright() as pw:
        http = pw.request.new_context()
        try:
            for post in pending:
                written, _ = fbs.download_post_media(http, post, "images", timeout_ms, max_bytes)
                files += written
        finally:
            http.dispose()
    return files


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Merge a Tally CSV export of site thoughts into posts.jsonl."
    )
    ap.add_argument("export", type=Path, help="CSV exported from the Tally dashboard")
    ap.add_argument(
        "--jsonl",
        type=Path,
        default=fbs.JSONL_PATH,
        help="target store (default: data/posts.jsonl)",
    )
    ap.add_argument(
        "--photo-dir",
        type=Path,
        default=None,
        help="folder with the photos renamed as in the CSV (default: the CSV's folder)",
    )
    ap.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    ap.add_argument("--media", choices=["none", "images"], default="images")
    ap.add_argument("--media-timeout", type=int, default=30000)
    ap.add_argument("--max-media-mb", type=int, default=25)
    args = ap.parse_args(argv)

    export = args.export.expanduser()
    if not export.exists():
        raise SystemExit(f"no such file: {export}")

    photo_dir = (args.photo_dir or export.parent).expanduser()
    posts, stats = read_export(export, photo_dir)
    if not posts:
        print(f"righe nel CSV: {stats['total']} — nessuna pubblicabile")
        for key, label in (("unapproved", "non approvate"), ("no_consent", "senza consenso"),
                           ("incomplete", "senza nome o testo")):
            if stats[key]:
                print(f"  scartate {label}: {stats[key]}")
        return 0

    moved = attach_local_photos(posts, args.dry_run)
    files = 0
    if not args.dry_run and args.media == "images":
        files = download_photos(posts, args.media_timeout, args.max_media_mb * 1024 * 1024)

    target: Path = args.jsonl.expanduser()
    rows = fbs.load_rows(target)
    before = len(rows)
    report = fbs.merge_posts(rows, posts, fbs.load_exclusions())

    print(f"thoughts  : {stats['total']} rows in {export.name}")
    for key, label in (("unapproved", "non approvate"), ("no_consent", "senza consenso"),
                       ("incomplete", "senza nome o testo")):
        if stats[key]:
            print(f"skipped   : {stats[key]} {label}")
    print(f"imported  : {len(posts)}")
    print(f"new       : {report['appended']} posts")
    print(f"matched   : {sum(report['matched'].values())} already stored ({dict(report['matched'])})")
    print(f"updated   : {report['updated']} rows, {report['unchanged']} unchanged")
    if moved:
        print(f"photos    : {moved} dal disco locale")
    if files:
        print(f"photos    : {files} scaricate da Tally")

    if args.dry_run:
        print(f"dry-run   : {target} resta a {before} righe (sarebbe {len(rows)})")
        return 0

    fbs.write_jsonl(target, rows)
    csv_path = target.with_suffix(".csv")
    fbs.export_csv(target, csv_path)
    print(f"jsonl     : {target}  ({before} -> {len(rows)} rows)")
    print(f"csv       : {csv_path}")
    print(f"media dir : {fbs.MEDIA_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
