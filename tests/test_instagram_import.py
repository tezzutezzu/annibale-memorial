"""Offline regression checks: identity, repeat imports and media preservation."""
import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fbstore as store
import import_console_dump as importer


def ig(code="ABC123456789", text="Un ricordo per Annibale"):
    return {"platform": "instagram", "permalink": f"https://www.instagram.com/reel/{code}/?x=1",
            "author": "amico", "text": text, "media": [], "capture_warnings": [],
            "carousel_complete": True}


class InstagramImportTests(unittest.TestCase):
    def test_shortcode_is_not_a_facebook_numeric_id(self):
        self.assertEqual(store.compute_id(ig()), "ig_ABC123456789")
        self.assertEqual(importer.normalise([ig()])[0]["permalink"],
                         "https://www.instagram.com/p/ABC123456789/")
        named = ig()
        named["permalink"] = "https://www.instagram.com/amico/p/ABC123456789/"
        self.assertEqual(store.compute_id(named), "ig_ABC123456789")
        self.assertIsNone(store.instagram_code({"permalink": "https://instagram.com.evil/p/ABC/"}))
        self.assertEqual(store.compute_id({"permalink": "https://facebook.com/a/posts/123456789/"}),
                         "fb_123456789")

    def test_same_caption_different_posts_and_platforms_stay_separate(self):
        facebook = {"id": "fb_123456789", "author": "amico", "text": "Un ricordo per Annibale",
                    "permalink": "https://facebook.com/a/posts/123456789/", "media": []}
        for batch in ([facebook, ig("one"), ig("two")], [ig("one"), ig("two"), facebook]):
            rows = []
            report = store.merge_posts(rows, importer.normalise(batch))
            self.assertEqual(report["appended"], 3)
            self.assertEqual(len(rows), 3)

    def test_full_capture_and_reimport_are_idempotent(self):
        short = ig(text="Un ricordo")
        full = ig(text="Un ricordo molto lungo per Annibale")
        full["media"] = [{"type": "image", "url": "https://cdn.example/1.jpg"},
                         {"type": "image", "url": "https://cdn.example/2.jpg"}]
        rows = []
        store.merge_posts(rows, importer.normalise([short, full]))
        self.assertEqual(len(rows), 1)
        before = copy.deepcopy(rows)
        report = store.merge_posts(rows, importer.normalise([short, full]))
        self.assertEqual(report["updated"], 0)
        self.assertEqual(rows, before)
        self.assertEqual(rows[0]["text"], full["text"])
        self.assertEqual(len(rows[0]["media"]), 2)

    def test_facebook_preview_still_merges_by_text(self):
        rows = importer.normalise([{"author": "amico", "text": "Un ricordo lungo e preciso",
                                    "media": [{"type": "image", "url": "https://old/image.jpg"}]}])
        fresh = importer.normalise([{"author": "amico", "text": "Un ricordo lungo e preciso",
                                    "media": [{"type": "image", "url": "https://new/image.jpg"}]}])
        self.assertEqual(store.merge_posts(rows, fresh)["appended"], 0)
        self.assertEqual(rows[0]["media"][0]["url"], "https://new/image.jpg")

    def test_invalid_instagram_identity_aborts(self):
        with self.assertRaises(SystemExit):
            importer.normalise([{"platform": "instagram", "text": "senza link"}])

    def test_cli_envelope_dry_run_and_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            dump = Path(temp) / "capture.json"
            target = Path(temp) / "posts.jsonl"
            dump.write_text(json.dumps({"posts": [ig(), ig("two")], "links": [], "version": 1}))
            with contextlib.redirect_stdout(io.StringIO()):
                importer.main([str(dump), "--jsonl", str(target), "--dry-run"])
                self.assertFalse(target.exists())
                importer.main([str(dump), "--jsonl", str(target), "--media", "none"])
                before = target.read_bytes()
                importer.main([str(dump), "--jsonl", str(target), "--media", "none"])
            self.assertEqual(target.read_bytes(), before)
            self.assertEqual(len(store.load_rows(target)), 2)
            self.assertTrue(target.with_suffix(".csv").exists())

    def test_download_uses_instagram_referer_and_retains_local_file(self):
        class Response:
            ok = True
            headers = {"content-type": "image/jpeg"}
            def body(self):
                return b"fixture image"
        class HTTP:
            calls = []
            def get(self, url, **kwargs):
                self.calls.append((url, kwargs))
                return Response()
        with tempfile.TemporaryDirectory() as temp, patch.object(store, "MEDIA_DIR", Path(temp)):
            row = importer.normalise([ig()])[0]
            row["media"] = [{"type": "image", "url": "https://cdn.example/photo.jpg"}]
            http = HTTP()
            self.assertEqual(store.download_post_media(http, row, "images", 1000, 1000)[0], 1)
            self.assertEqual(http.calls[0][1]["headers"]["Referer"], "https://www.instagram.com/")
            row["media"][0]["url"] += "?fresh=1"
            self.assertEqual(store.download_post_media(http, row, "images", 1000, 1000)[0], 0)
            self.assertEqual(len(http.calls), 1)


if __name__ == "__main__":
    unittest.main()
