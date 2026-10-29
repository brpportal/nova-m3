import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nova.extract.m1 import extract_m1

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "feed_sample.html")
BASE = "https://www.facebook.com/ExamplePage"


class TestM1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(FIXTURE, encoding="utf-8") as fh:
            cls.html = fh.read()
        cls.candidates, cls.stats = extract_m1(cls.html, BASE)

    def test_finds_all_post_like_links(self):
        self.assertEqual(len(self.candidates), 7)

    def test_types(self):
        types = sorted(c.object_type for c in self.candidates)
        self.assertEqual(types, ["photo", "post", "post", "post", "post",
                                 "video", "video"])

    def test_decoys_skipped_and_counted(self):
        self.assertEqual(self.stats["skipped_external"], 1)   # youtube
        self.assertEqual(self.stats["skipped_non_post"], 3)   # profile, comment, /friends
        self.assertEqual(self.stats["skipped_invalid"], 1)    # "#"

    def test_all_valid_format(self):
        for cand in self.candidates:
            self.assertEqual(cand.validation_status, "VALID_FORMAT", cand.raw_url)

    def test_group_permalink_found(self):
        urls = [c.normalized_url for c in self.candidates]
        self.assertIn(
            "https://www.facebook.com/groups/9988776655/permalink/987654321098765",
            urls)

    def test_empty_html(self):
        cands, stats = extract_m1("", BASE)
        self.assertEqual(cands, [])
        self.assertEqual(stats["hrefs_seen"], 0)


if __name__ == "__main__":
    unittest.main()
