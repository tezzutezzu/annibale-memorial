#!/usr/bin/env python3
"""Integrate reviewed Instagram matches without losing source texts or media.

The review explicitly maps known cross-platform copies. Similarity never
decides a merge here. Inputs stay untouched; --apply writes the store only
after every Instagram attachment is available on disk.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import shutil
import subprocess
import unicodedata
import urllib.request
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import fbstore as store

ROOT = Path(__file__).resolve().parent
DEFAULT_DUMP = ROOT / 'instagram/import/2026-10-27.json'
DEFAULT_REVIEW = ROOT / 'instagram/import/2026-10-27-matches.json'
MERGE_CATEGORIES = {'stesso_testo_o_variante_minima', 'testo_parziale_in_comune'}


def content_key(text):
    value = unicodedata.normalize('NFKC', text or '').casefold()
    return ' '.join(re.findall(r'[^\W_]+', value))


def source_record(post):
    result = copy.deepcopy({k: v for k, v in post.items()
                            if k not in ('sources', 'aliases', 'integration', 'collection_url')})
    result.setdefault('platform', 'instagram' if store.is_instagram(post) else 'facebook')
    return result


def media_key(item):
    path = ROOT / (item.get('local_path') or '__missing__')
    if path.is_file():
        return item.get('type'), hashlib.sha256(path.read_bytes()).hexdigest()
    # Unavailable legacy streams must not be removed or mixed with a new video.
    return item.get('type'), item.get('url') or item.get('poster') or json.dumps(item, sort_keys=True)


def merge_record(row, incoming):
    """Keep the canonical id, record both full sources and form a media union."""
    if not row.get('sources'):
        row['sources'] = [source_record(row)]
    incoming_sources = incoming.get('sources') or [source_record(incoming)]
    source_ids = {p['id'] for p in row['sources']}
    for source in incoming_sources:
        if source['id'] not in source_ids:
            row['sources'].append(copy.deepcopy(source))
            source_ids.add(source['id'])
    aliases = list(row.get('aliases') or [])
    for value in [incoming['id'], *(incoming.get('aliases') or [])]:
        if value != row['id'] and value not in aliases:
            aliases.append(value)
    row['aliases'] = aliases
    if len(content_key(incoming.get('text'))) > len(content_key(row.get('text'))):
        row['text'] = incoming.get('text') or ''
        row['text_source_id'] = incoming.get('text_source_id') or incoming['id']
    else:
        row.setdefault('text_source_id', row['id'])
    for field in ('author', 'author_url', 'published_at', 'time_text'):
        if not row.get(field) and incoming.get(field):
            row[field] = incoming[field]
    row.setdefault('platform', 'instagram' if store.is_instagram(row) else 'facebook')
    keys = {media_key(item): item for item in row.get('media') or []}
    for item in incoming.get('media') or []:
        key = media_key(item)
        if key not in keys:
            cloned = copy.deepcopy(item)
            row.setdefault('media', []).append(cloned)
            keys[key] = cloned
        else:
            # Preserve the extra attribution even when the bytes are identical.
            existing = keys[key]
            variants = existing.setdefault('also_from', [])
            reference = {'post_id': incoming['id'], 'url': item.get('url') or '',
                         'local_path': item.get('local_path') or ''}
            if reference not in variants:
                variants.append(reference)
    row['relevant'] = True


def integrate(rows, incoming, review):
    rows = copy.deepcopy(rows)
    decisions = {r['instagram_id']: r for r in review['posts']}
    report = {'facebook_merges': [], 'instagram_merges': [], 'appended': [], 'already_present': []}
    # The two Puglia Culture accounts published the same reviewed statement.
    internal = {'ig_DevvSZzs54Z': 'ig_Dev0CHpo0ON'}
    for post in incoming:
        canonical = {}
        for row in rows:
            for pid in [row['id'], *(row.get('aliases') or [])]:
                canonical[pid] = row
        if post['id'] in canonical:
            report['already_present'].append(post['id'])
            continue
        decision = decisions[post['id']]
        target = decision.get('facebook_id') if decision['category'] in MERGE_CATEGORIES else internal.get(post['id'])
        if target:
            if target not in canonical:
                raise ValueError('Reviewed target missing: ' + target)
            row = canonical[target]
            if target == internal.get(post['id']) and content_key(row.get('text')) != content_key(post.get('text')):
                raise ValueError('The two Instagram statements no longer match')
            before = len(row.get('media') or [])
            merge_record(row, post)
            kind = 'facebook_merges' if decision['category'] in MERGE_CATEGORIES else 'instagram_merges'
            report[kind].append({'instagram_id': post['id'], 'canonical_id': row['id'],
                                 'media_added': len(row.get('media') or []) - before})
        else:
            row = copy.deepcopy(post)
            row.pop('collection_url', None)
            row['sources'] = [source_record(post)]
            row['aliases'] = []
            row['text_source_id'] = post['id']
            row['relevant'] = True
            rows.append(row)
            report['appended'].append(post['id'])
    return rows, report


def stage_one(post, index, item):
    kind = item.get('type')
    if kind not in ('image', 'video'):
        raise ValueError('Unexpected Instagram media type')
    old = ROOT / (item.get('local_path') or '__missing__')
    directory = ROOT / 'data/media' / post['id']
    directory.mkdir(parents=True, exist_ok=True)
    if old.is_file():
        body = old.read_bytes()
        ext = old.suffix
    else:
        url = item.get('url') or ''
        if not url.startswith('https://'):
            raise ValueError(post['id'] + ': no local file or HTTPS media URL')
        request = urllib.request.Request(url, headers={'Referer': 'https://www.instagram.com/',
                                                       'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(request, timeout=30) as response:
            ctype = response.headers.get('content-type', '')
            if not ctype.startswith(('image/', 'video/')):
                raise ValueError(post['id'] + ': unexpected content type ' + ctype)
            body = response.read(50 * 1024 * 1024 + 1)
            ext = store.guess_ext(url, ctype)
    if not body or len(body) > 50 * 1024 * 1024:
        raise ValueError(post['id'] + ': invalid media size')
    digest = hashlib.sha256(body).hexdigest()
    target = directory / f'{index + 1:02d}_{digest[:12]}{ext}'
    if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
        temporary = target.with_suffix(target.suffix + '.tmp')
        temporary.write_bytes(body)
        temporary.replace(target)
    result = copy.deepcopy(item)
    result.update(local_path=str(target.relative_to(ROOT)), bytes=len(body), sha256=digest,
                  origin_platform='instagram', origin_post_id=post['id'])
    result.pop('download_error', None)
    if kind == 'video':
        poster = directory / f'{index + 1:02d}_{digest[:12]}_poster.jpg'
        if not poster.exists():
            subprocess.run([str(ROOT / '.venv/bin/ffmpeg'), '-v', 'error', '-ss', '1',
                            '-i', str(target), '-frames:v', '1', '-q:v', '3', str(poster)],
                           check=True, capture_output=True)
        result['poster_local_path'] = str(poster.relative_to(ROOT))
    return post['id'], index, result


def stage_media(posts):
    out = copy.deepcopy(posts)
    by_id = {p['id']: p for p in out}
    work = [(p, i, m) for p in posts for i, m in enumerate(p.get('media') or [])]
    errors = []
    completed = 0
    with ThreadPoolExecutor(max_workers=4) as executor:
        pending = {executor.submit(stage_one, *item): item for item in work}
        for task in as_completed(pending):
            post, index, _ = pending[task]
            try:
                pid, i, item = task.result()
                by_id[pid]['media'][i] = item
            except Exception as exc:
                errors.append({'post_id': post['id'], 'media_index': index, 'error': str(exc)})
            completed += 1
            if completed % 20 == 0 or completed == len(work):
                print(f'Media {completed}/{len(work)}, errors {len(errors)}', flush=True)
    if errors:
        raise RuntimeError(json.dumps(errors, ensure_ascii=False))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dump', type=Path, default=DEFAULT_DUMP)
    ap.add_argument('--review', type=Path, default=DEFAULT_REVIEW)
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    posts = json.loads(args.dump.read_text())['posts']
    review = json.loads(args.review.read_text())
    existing = store.load_rows(store.JSONL_PATH)
    present = {pid for row in existing for pid in [row['id'], *(row.get('aliases') or [])]}
    if all(p['id'] in present for p in posts):
        print('All Instagram source ids are already integrated; no files changed.')
        return
    if args.apply:
        posts = stage_media(posts)
    integrated, report = integrate(existing, posts, review)
    print(json.dumps({key: len(value) for key, value in report.items()}, indent=2))
    if not args.apply:
        print('Dry run: store unchanged; media not downloaded.')
        return
    # Never overwrite a row file that changed while the network work ran.
    if store.load_rows(store.JSONL_PATH) != existing:
        raise RuntimeError('Store changed during staging; apply cancelled')
    backup = ROOT / '.backups' / ('instagram-data-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    backup.mkdir(parents=True)
    shutil.copy2(store.JSONL_PATH, backup / 'posts.jsonl')
    if store.CSV_PATH.exists():
        shutil.copy2(store.CSV_PATH, backup / 'posts.csv')
    store.write_jsonl(store.JSONL_PATH, integrated)
    store.export_csv(store.JSONL_PATH, store.CSV_PATH)
    output = ROOT / 'instagram/verifiche/2026-10-27/integration.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'source': str(args.dump.relative_to(ROOT)),
                                 'rows_before': len(existing), 'rows_after': len(integrated),
                                 'backup': str(backup.relative_to(ROOT)),
                                 'visible_after': sum(p.get('relevant') is not False for p in integrated),
                                 **report}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
