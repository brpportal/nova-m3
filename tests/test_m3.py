import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nova.extract.m3 import extract_m3

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "feed_sample.html")
BASE = "https://www.facebook.com/ExamplePage"


class TestM3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(FIXTURE, encoding="utf-8") as fh:
            cls.html = fh.read()
        cls.candidates, cls.stats = extract_m3(cls.html, BASE)

    def test_candidate_count(self):
        self.assertEqual(len(self.candidates), 3)

    def test_permalink_preferred_with_high_confidence(self):
        by_id = {c.object_id: c for c in self.candidates}
        story = by_id["123456789012345"]
        self.assertEqual(story.confidence, 0.95)
        self.assertEqual(
            story.normalized_url,
            "https://www.facebook.com/ExamplePage/posts/123456789012345")

    def test_constructed_url_from_verified_format(self):
        by_id = {c.object_id: c for c in self.candidates}
        constructed = by_id["314159265358979"]
        self.assertEqual(
            constructed.normalized_url,
            "https://www.facebook.com/100200300400500/posts/314159265358979")
        self.assertEqual(constructed.confidence, 0.6)

    def test_user_and_comment_ids_rejected(self):
        ids = {c.object_id for c in self.candidates}
        self.assertNotIn("999888777666555", ids)   # post_id on a User object
        self.assertEqual(self.stats["rejected_id_only"], 2)  # User + Comment

    def test_broken_json_does_not_crash(self):
        cands, _ = extract_m3('{"broken": [1,2,,, {"x": ', BASE)
        self.assertEqual(cands, [])

    def test_escaped_urls_decoded(self):
        raw = r'{"__typename":"Story","permalink_url":"https:\/\/www.facebook.com\/P\/posts\/123456789","creation_time":1}'
        cands, _ = extract_m3(raw, BASE)
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0].normalized_url,
                         "https://www.facebook.com/P/posts/123456789")


if __name__ == "__main__":
    unittest.main()
