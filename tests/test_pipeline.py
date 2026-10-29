import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nova.engines.fileengine import FileEngine
from nova.exporter import render
from nova.extract.hybrid import extract_hybrid
from nova.scroller import collect
from nova.session import LOGIN_REQUIRED, NOT_RUNNING, check_session
from nova.store import Store

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
BASE = "https://www.facebook.com/ExamplePage"


def load(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as fh:
        return fh.read()


class TestHybrid(unittest.TestCase):
    def test_merge_dedupes_across_methods(self):
        merged, stats = extract_hybrid(load("feed_sample.html"), BASE)
        # M1: 7, M3: 3, shared: post 123456789012345 (x3) + video 777888999000111 (x2)
        self.assertEqual(len(merged), 7)
        shared = [c for c in merged if c.object_id == "123456789012345"]
        self.assertEqual(len(shared), 1)
        self.assertEqual(shared[0].method, "hybrid")


class TestStoreExport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store = Store(os.path.join(self.tmp, "test.db"))
        merged, _ = extract_hybrid(load("feed_sample.html"), BASE)
        self.new_count = sum(1 for c in merged if self.store.upsert(c))
        self.dup_count = sum(1 for c in merged if not self.store.upsert(c))

    def tearDown(self):
        self.store.close()

    def test_upsert_dedup(self):
        self.assertEqual(self.new_count, 7)
        self.assertEqual(self.dup_count, 7)  # second pass: all duplicates
        self.assertEqual(self.store.count(), 7)

    def test_export_txt_unique_urls(self):
        txt = render(self.store.all_records(), "txt")
        lines = [ln for ln in txt.splitlines() if ln.strip()]
        self.assertEqual(len(lines), 7)
        self.assertEqual(len(set(lines)), 7)
        for ln in lines:
            self.assertTrue(ln.startswith("https://"), ln)

    def test_export_csv_and_json(self):
        import csv
        import io
        import json

        rows = list(csv.DictReader(io.StringIO(render(self.store.all_records(), "csv"))))
        self.assertEqual(len(rows), 7)
        self.assertIn("post_url", rows[0])
        data = json.loads(render(self.store.all_records(), "json"))
        self.assertEqual(len(data), 7)
        self.assertEqual(data[0]["validation_status"], "VALID_FORMAT")


class TestScroller(unittest.TestCase):
    def _store(self):
        tmp = tempfile.mkdtemp()
        return Store(os.path.join(tmp, "scroll.db"))

    def test_collects_until_no_new_content(self):
        engine = FileEngine([load("feed_sample.html")], url=BASE)
        engine.start()
        store = self._store()
        result = collect(engine, store, mode="hybrid", max_posts=200,
                         max_seconds=600, idle_rounds=2, wait_seconds=0,
                         sleep=lambda s: None)
        self.assertEqual(result.stored_new, 7)
        self.assertIn("no new content", result.stop_reason)
        store.close()

    def test_scroll_reveals_new_posts(self):
        engine = FileEngine([load("feed_sample.html"),
                             load("feed_sample_page2.html")], url=BASE)
        engine.start()
        store = self._store()
        result = collect(engine, store, mode="m1", max_posts=200,
                         max_seconds=600, idle_rounds=2, wait_seconds=0,
                         sleep=lambda s: None)
        # page1: 6 unique m1 (7 candidates, one internal dup) + page2: 2 new
        self.assertEqual(result.stored_new, 8)
        store.close()

    def test_max_posts_limit(self):
        engine = FileEngine([load("feed_sample.html")], url=BASE)
        engine.start()
        store = self._store()
        result = collect(engine, store, mode="m1", max_posts=3,
                         max_seconds=600, idle_rounds=5, wait_seconds=0,
                         sleep=lambda s: None)
        self.assertEqual(result.stored_new, 3)
        self.assertIn("max posts", result.stop_reason)
        store.close()

    def test_max_seconds_limit(self):
        engine = FileEngine([load("feed_sample.html")], url=BASE)
        engine.start()
        store = self._store()
        ticks = iter([0, 0, 1000])  # start, round1 check, then over the limit
        result = collect(engine, store, mode="m1", max_posts=200,
                         max_seconds=10, idle_rounds=99, wait_seconds=0,
                         sleep=lambda s: None, clock=lambda: next(ticks))
        self.assertIn("max scroll duration", result.stop_reason)
        store.close()


class TestSession(unittest.TestCase):
    def test_not_running(self):
        engine = FileEngine(["<html></html>"], url=BASE)
        state, _ = check_session(engine)
        self.assertEqual(state, NOT_RUNNING)

    def test_login_page_detected(self):
        engine = FileEngine(["<html></html>"],
                            url="https://www.facebook.com/login")
        engine.start()
        state, _ = check_session(engine)
        self.assertEqual(state, LOGIN_REQUIRED)

    def test_checkpoint_detected(self):
        engine = FileEngine(["<html></html>"],
                            url="https://www.facebook.com/checkpoint/")
        engine.start()
        state, _ = check_session(engine)
        self.assertEqual(state, "CHECKPOINT")


if __name__ == "__main__":
    unittest.main()
