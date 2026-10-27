#!/usr/bin/env python3
"""Store + media helpers for the DevTools-console workflow.

The console scraper (`console/fb_scrape_console.js`) collects posts inside your
logged-in tab but cannot write image files, because Chrome blocks bulk automatic
downloads. `import_console_dump.py` therefore merges the dump into
`data/posts.jsonl` and fetches the images while the signed CDN URLs still work.

Everything here is plain standard library — no browser, no profile, no CDP.
Saving the images also needs `playwright`, but only its HTTP request client
(never a browser), so `pip install playwright` is enough; `playwright install`
is not required.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
JSONL_PATH = DATA_DIR / "posts.jsonl"
CSV_PATH = DATA_DIR / "posts.csv"
MEDIA_DIR = DATA_DIR / "media"
EXCLUDED_PATH = DATA_DIR / "excluded.json"

MEDIA_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/avif": ".avif",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
}
URL_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".mp4", ".webm", ".mov"}


# --------------------------------------------------------------------------- #
# identity
# --------------------------------------------------------------------------- #
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def content_id(post: dict) -> str:
    """Hash of who wrote it and what it says, for a post we cannot key by permalink.

    Used both for posts collected without a permalink and for a permalink that is
    shared by two different people (the same photo posted by two accounts).
    """
    first_media = (post.get("media") or [{}])[0]
    basis = "|".join(
        [
            post.get("author") or "",
            (post.get("text") or "")[:400],
            (first_media.get("url") or first_media.get("poster") or "")[:120],
        ]
    )
    return "h_" + hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]


def compute_id(post: dict) -> str:
    """Stable identity: the numeric post id when we have a permalink, else a hash."""
    m = re.search(r"(\d{6,})", post.get("permalink") or "")
    if m:
        return "fb_" + m.group(1)
    return content_id(post)


# --------------------------------------------------------------------------- #
# media
# --------------------------------------------------------------------------- #
def guess_ext(url: str, content_type: str) -> str:
    """Pick a file extension from the response type, falling back to the URL path."""
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct in MEDIA_EXT:
        return MEDIA_EXT[ct]
    suffix = Path(urlsplit(url).path).suffix.lower()
    if suffix in URL_SUFFIXES:
        return ".jpg" if suffix == ".jpeg" else suffix
    return ".bin"


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def download_post_media(
    http, post: dict, which: str, timeout_ms: int, max_bytes: int
) -> tuple[int, int]:
    """Save one post's media under data/media/<post id>/ and annotate each item.

    `http` is anything with a Playwright-style .get(url, timeout=, headers=) —
    the standalone request client the importer opens is enough.

    Returns (files_written, bytes_written). Problems are recorded per item as
    `download_error` so one dead CDN link never costs us the post itself.

    Files are named from a hash of the URL rather than the original name, which
    makes re-runs idempotent: an already-downloaded file is skipped, not
    re-fetched or duplicated.
    """
    files = 0
    written = 0
    media = post.get("media") or []
    if which == "none" or not media:
        return files, written

    dest = MEDIA_DIR / str(post.get("id") or "unknown")

    for idx, item in enumerate(media, 1):
        kind = item.get("type")
        if kind not in ("image", "video"):
            continue
        if kind == "video" and which != "all":
            continue  # feed videos are usually blob:/DASH, not fetchable

        url = item.get("url") or ""
        if not url.startswith(("http://", "https://")):
            item.setdefault("download_error", "no direct url (blob or stream)")
            continue

        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
        ext = guess_ext(url, "")
        path = dest / f"{idx:02d}_{digest}{ext}"

        if path.exists() and path.stat().st_size > 0:
            item["local_path"] = _rel(path)
            item.setdefault("bytes", path.stat().st_size)
            continue

        try:
            resp = http.get(
                url, timeout=timeout_ms, headers={"Referer": "https://www.facebook.com/"}
            )
        except Exception as exc:  # network/DNS/timeout
            item["download_error"] = f"request failed ({type(exc).__name__})"
            continue

        if not resp.ok:
            item["download_error"] = f"http {resp.status}"
            continue

        ctype = resp.headers.get("content-type", "")
        if ctype and not ctype.startswith(("image/", "video/", "application/octet-stream")):
            item["download_error"] = f"unexpected content-type: {ctype[:60]}"
            continue

        body = resp.body()
        if not body:
            item["download_error"] = "empty response"
            continue
        if len(body) > max_bytes:
            item["download_error"] = f"too large ({len(body) // 1024} KB)"
            continue

        if ext == ".bin":  # no usable suffix in the URL; trust the response
            ext = guess_ext(url, ctype)
            path = dest / f"{idx:02d}_{digest}{ext}"

        dest.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        item["local_path"] = _rel(path)
        item["bytes"] = len(body)
        files += 1
        written += len(body)

    return files, written


def row_needs_media(row: dict, which: str) -> bool:
    """True when a stored post still has a fetchable item we haven't saved."""
    for item in row.get("media") or []:
        kind = item.get("type")
        if kind not in ("image", "video"):
            continue
        if kind == "video" and which != "all":
            continue
        if item.get("local_path") or item.get("download_error"):
            continue
        if (item.get("url") or "").startswith(("http://", "https://")):
            return True
    return False


def backfill_media(http, args: argparse.Namespace, jsonl_path: Path | None = None) -> None:
    """Download media for posts already in posts.jsonl (rows are rewritten in place).

    Items that previously failed are skipped, so a permanently dead blob: URL
    isn't retried on every run.
    """
    path = jsonl_path or JSONL_PATH
    if not path.exists():
        print(f"backfill: no {path.name} yet, nothing to do")
        return

    rows = load_rows(path)

    todo = [r for r in rows if r.get("id") and row_needs_media(r, args.media)]
    if not todo:
        print("backfill: every stored post already has its media")
        return

    print(f"backfill: fetching media for {len(todo)} posts")
    files = 0
    size = 0
    max_bytes = args.max_media_mb * 1024 * 1024
    for n, row in enumerate(todo, 1):
        f, b = download_post_media(http, row, args.media, args.media_timeout, max_bytes)
        files += f
        size += b
        if n % 25 == 0:
            print(f"  {n}/{len(todo)} posts...")

    write_jsonl(path, rows)
    print(f"backfill: saved {files} files ({size / 1048576:.1f} MB)")


# --------------------------------------------------------------------------- #
# reconciling a new capture with what the store already has
# --------------------------------------------------------------------------- #
# Facebook cuts long messages behind an "Altro..." button. Dumps taken before
# the console scraper learned to expand it stop at that preview, with the button
# label glued to the end of the text; strip it before comparing so a full
# capture still matches the preview that came before it.
TRUNCATION_RE = re.compile(
    r"\s*(?:…|\.\.\.)\s*(?:altro|vedi altro|mostra altro|see more)\s*(?:…|\.\.\.)?\s*$",
    re.IGNORECASE,
)

# Once the button label is gone a cut message just ends in the ellipsis, which
# is the signal that a later capture may have more of it.
PREVIEW_END_RE = re.compile(r"(?:…|\.\.\.)\s*$")


def looks_truncated(text: str | None) -> bool:
    """True when the message stops at Facebook's cut, not at its end."""
    return bool(PREVIEW_END_RE.search(text or ""))


def message_signature(text: str, limit: int = 300) -> str:
    """Comparable head of a message: case, spacing and the "Altro..." cut removed."""
    clean = TRUNCATION_RE.sub("", text or "")
    clean = re.sub(r"\s+", " ", clean).strip().rstrip(".… ").strip()
    return clean.casefold()[:limit]


def _author_key(name: str | None) -> str:
    return (name or "").strip().casefold()


def message_key(post: dict) -> tuple[str, str]:
    """Who wrote it and how it opens: what makes two captures the same memory."""
    return (_author_key(post.get("author")), message_signature(post.get("text") or ""))


def _authors_compatible(a: str | None, b: str | None) -> bool:
    ka, kb = _author_key(a), _author_key(b)
    return not ka or not kb or ka == kb


def _permalink_key(post: dict) -> str:
    link = (post.get("permalink") or "").strip()
    return "" if link in ("", "#") else link


class RowMatcher:
    """Find the stored row a freshly captured post belongs to.

    `id` alone is not enough: posts collected without a permalink are keyed by a
    hash that includes the signed image URL, which changes on every collection,
    so the very same message comes back under a new id. Matching on the message
    keeps the store from filling up with copies.
    """

    def __init__(self, rows: list[dict]):
        self.rows = rows
        self.by_id: dict[str, int] = {}
        self.by_signature: dict[tuple[str, str], int] = {}
        self.by_permalink: dict[str, int] = {}
        for i, row in enumerate(rows):
            self.index(i)

    def index(self, i: int) -> None:
        row = self.rows[i]
        pid = row.get("id")
        if pid:
            self.by_id.setdefault(pid, i)
        key = message_key(row)
        if key[1]:
            self.by_signature.setdefault(key, i)
        link = _permalink_key(row)
        if link:
            self.by_permalink.setdefault(link, i)

    def find(self, post: dict) -> tuple[int | None, str]:
        """Return (row index, how) — `how` is 'id', 'message', 'permalink', 'similar' or 'new'."""
        pid = post.get("id")
        if pid and pid in self.by_id and self._author_fits(self.by_id[pid], post):
            return self.by_id[pid], "id"

        key = message_key(post)
        if key[1] and key in self.by_signature:
            return self.by_signature[key], "message"

        link = _permalink_key(post)
        if link and link in self.by_permalink and self._author_fits(self.by_permalink[link], post):
            return self.by_permalink[link], "permalink"

        if key[1]:
            close = self._closest_by_text(post, key[1])
            if close is not None:
                return close, "similar"
        return None, "new"

    def _author_fits(self, i: int, post: dict) -> bool:
        """A permalink identifies a photo, not a person: two accounts can share it."""
        return _authors_compatible(post.get("author"), self.rows[i].get("author"))

    def _closest_by_text(self, post: dict, signature: str, threshold: float = 0.9) -> int | None:
        """Same author, nearly the same words: a preview next to its full text."""
        best: int | None = None
        best_ratio = 0.0
        for i, row in enumerate(self.rows):
            if not _authors_compatible(post.get("author"), row.get("author")):
                continue
            other = message_signature(row.get("text") or "")
            if not other:
                continue
            ratio = SequenceMatcher(None, other[:400], signature[:400]).ratio()
            if ratio > best_ratio:
                best, best_ratio = i, ratio
        return best if best_ratio >= threshold else None


def _merge_relevance(a, b):
    """`relevant` is a judgement, not a measurement.

    True beats everything (a memory named by any capture stays one), and an
    explicit "no" beats "not judged", so a row taken out of the slideshow stays
    out when the same post is captured again.
    """
    rank = {True: 2, False: 1, None: 0}
    return {2: True, 1: False, 0: None}[max(rank.get(a, 0), rank.get(b, 0))]


def _saved(item: dict) -> bool:
    local = item.get("local_path")
    return bool(local) and (ROOT / local).exists()


def _media_url(item: dict) -> str:
    return item.get("url") or item.get("poster") or ""


def merged_media_items(stored: list[dict], fresh: list[dict]) -> list[dict]:
    """Keep files already on disk, take the new (still signed) URL for the rest."""
    out: list[dict] = []
    for idx in range(max(len(stored), len(fresh))):
        old = stored[idx] if idx < len(stored) else None
        new = fresh[idx] if idx < len(fresh) else None
        if old is not None and _saved(old):
            out.append(old)
        elif new is not None:
            item = dict(new)
            if old is not None:
                for key, value in old.items():
                    if key != "download_error" and not item.get(key) and value:
                        item[key] = value
                # A fresh URL is worth another try; the same dead one is not.
                if (
                    _media_url(old) == _media_url(new)
                    and old.get("download_error")
                    and not item.get("download_error")
                ):
                    item["download_error"] = old["download_error"]
            out.append(item)
        elif old is not None:
            out.append(old)
    return out


def reconcile_row(row: dict, post: dict) -> None:
    """Fold a newer capture into a stored row, keeping the better of the two."""

    def put(field: str, value) -> None:
        if row.get(field) != value:
            row[field] = value

    # A message is only replaced while the stored one is still a Facebook
    # preview. Once it is complete the store wins, so a correction made by hand
    # (a name fixed, a typo) is not undone the next time the dump is imported.
    for field in ("text", "shared_text"):
        stored = row.get(field) or ""
        fresh = post.get(field) or ""
        if not fresh.strip() or len(fresh) <= len(stored):
            continue
        if not stored.strip() or looks_truncated(stored):
            put(field, fresh)

    # Everything else is only ever filled in: a capture that did not load a
    # field shows up as null and must not erase what the store already knows.
    for field in (
        "author", "author_url", "shared_author", "permalink", "time_text",
        "reactions", "reactions_summary", "comments", "shares",
    ):
        if not row.get(field) and post.get(field):
            put(field, post[field])

    put("relevant", _merge_relevance(row.get("relevant"), post.get("relevant")))

    media = merged_media_items(row.get("media") or [], post.get("media") or [])
    if media != (row.get("media") or []):
        put("media", media)


def _collapse_batch(posts: list[dict]) -> list[dict]:
    """One post per memory: a dump often holds the same message twice (search + feed).

    The second capture is folded into the first instead of matching the same
    stored row twice, which would otherwise report a change on every import.
    """
    out: list[dict] = []
    seen: dict[tuple[str, str], dict] = {}
    for post in posts:
        key = message_key(post)
        if not key[1]:
            out.append(post)
            continue
        first = seen.get(key)
        if first is None:
            seen[key] = post
            out.append(post)
        else:
            reconcile_row(first, post)
    return out


# --------------------------------------------------------------------------- #
# the posts that were deliberately left out
# --------------------------------------------------------------------------- #
class Exclusions:
    """Posts that were removed on purpose, so a re-import does not bring them back.

    The id alone is not enough: a post collected without a permalink is keyed by
    a hash of the image URL, which changes between collections. The author and
    the opening words are stored alongside, and either one matching is enough.
    """

    def __init__(self, entries: list[dict]):
        self.ids: set[str] = set()
        self.signatures: set[tuple[str, str]] = set()
        for entry in entries:
            pid = (entry.get("id") or "").strip()
            if pid:
                self.ids.add(pid)
            key = message_key({"author": entry.get("author"), "text": entry.get("message")})
            if key[1]:
                self.signatures.add(key)

    def __len__(self) -> int:
        return len(self.ids)

    def __contains__(self, post: dict) -> bool:
        pid = post.get("id")
        if pid and pid in self.ids:
            return True
        key = message_key(post)
        return bool(key[1]) and key in self.signatures


def read_exclusions(path: Path | None = None) -> list[dict]:
    """The exclusion list as written on disk."""
    path = path or EXCLUDED_PATH
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path.name} is not valid JSON: {exc}") from exc
    if isinstance(data, dict):  # tolerate {"posts": [...]}
        data = data.get("posts", [])
    return [e for e in data if isinstance(e, dict)]


def load_exclusions(path: Path | None = None) -> Exclusions:
    return Exclusions(read_exclusions(path))


def write_exclusions(entries: list[dict], path: Path | None = None) -> int:
    path = path or EXCLUDED_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(entries)


def free_id(post: dict, taken: set[str]) -> str:
    """An id no row uses yet, for a post whose permalink id belongs to someone else."""
    pid = post.get("id") or content_id(post)
    if pid not in taken:
        return pid
    candidate = content_id(post)
    suffix = 2
    while candidate in taken:
        candidate = f"{content_id(post)}_{suffix}"
        suffix += 1
    return candidate


def merge_posts(rows: list[dict], incoming: list[dict], excluded: Exclusions | None = None) -> dict:
    """Reconcile `incoming` posts into `rows` in place and report what happened."""
    matcher = RowMatcher(rows)
    report: dict = {
        "matched": Counter(),
        "fields": Counter(),
        "updated": 0,
        "unchanged": 0,
        "appended": 0,
        "duplicates": 0,
        "skipped": 0,
        "renamed": 0,
    }

    excluded = excluded or Exclusions([])
    kept = [p for p in incoming if p not in excluded]
    report["skipped"] = len(incoming) - len(kept)

    collapsed = _collapse_batch(kept)
    report["duplicates"] = len(kept) - len(collapsed)

    before: dict[int, dict] = {}
    taken = set(matcher.by_id)
    for post in collapsed:
        idx, how = matcher.find(post)
        if idx is None:
            row = dict(post)
            # The permalink may already belong to a row written by someone
            # else; keep both memories instead of overwriting one with the other.
            row["id"] = free_id(row, taken)
            taken.add(row["id"])
            rows.append(row)
            matcher.index(len(rows) - 1)  # so a repeat inside the same batch matches
            report["appended"] += 1
            if row["id"] != post.get("id"):
                report["renamed"] += 1
            continue

        if idx not in before:
            before[idx] = dict(rows[idx])
        reconcile_row(rows[idx], post)
        report["matched"][how] += 1

    # Report what the batch actually changed, not what each post tried to
    # change: two captures of one memory can take turns and end up where they
    # started, and a re-import must read as "nothing to do".
    for idx, previous in before.items():
        row = rows[idx]
        changed = [k for k in set(previous) | set(row) if previous.get(k) != row.get(k)]
        if changed:
            report["updated"] += 1
            report["fields"].update(changed)
        else:
            report["unchanged"] += 1

    return report


# --------------------------------------------------------------------------- #
# store
# --------------------------------------------------------------------------- #
def load_rows(path: Path) -> list[dict]:
    """Read the store, skipping blank and unparseable lines."""
    rows: list[dict] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> int:
    """Rewrite the store atomically, so an interrupted run never truncates it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        fh.flush()
    tmp.replace(path)
    return len(rows)


def load_seen(path: Path) -> set[str]:
    seen: set[str] = set()
    if not path.exists():
        return seen
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                seen.add(json.loads(line)["id"])
            except (json.JSONDecodeError, KeyError):
                continue
    return seen


def append_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        fh.flush()


def export_csv(jsonl_path: Path, csv_path: Path) -> int:
    if not jsonl_path.exists():
        return 0
    rows = []
    with jsonl_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if not rows:
        return 0

    cols = [
        "id", "collected_at", "author", "author_url", "time_text", "permalink",
        "reactions", "comments", "shares", "media_count", "media_local", "media_urls",
        "is_ad", "posinset", "shared_author", "text", "shared_text",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            media = r.get("media") or []
            w.writerow(
                {
                    **r,
                    "media_count": len(media),
                    "media_local": " | ".join(m.get("local_path") or "" for m in media),
                    "media_urls": " | ".join(m.get("url") or m.get("poster") or "" for m in media),
                }
            )
    return len(rows)
