import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nova.extract.urls import (INVALID_URL, VALID_FORMAT, Candidate, classify,
                               normalize_url, validate_candidate)


class TestNormalize(unittest.TestCase):
    def test_strips_tracking_params(self):
        url = normalize_url(
            "https://www.facebook.com/Page/posts/123456789?__cft__[0]=AZ&__tn__=x&fbclid=zzz")
        self.assertEqual(url, "https://www.facebook.com/Page/posts/123456789")

    def test_keeps_destination_params(self):
        url = normalize_url("https://www.facebook.com/watch/?v=123456789&ref=share")
        self.assertEqual(url, "https://www.facebook.com/watch?v=123456789")

    def test_relative_resolved_against_base(self):
        url = normalize_url("/Page/posts/123456789",
                            base="https://www.facebook.com/Page")
        self.assertEqual(url, "https://www.facebook.com/Page/posts/123456789")

    def test_rejects_javascript_and_fragments(self):
        self.assertIsNone(normalize_url("javascript:void(0)"))
        self.assertIsNone(normalize_url("#section"))

    def test_decodes_amp_entities(self):
        url = normalize_url("https://www.facebook.com/photo.php?fbid=123456&amp;set=a.1")
        self.assertIn("fbid=123456", url)
        self.assertIn("set=a.1", url)


class TestClassify(unittest.TestCase):
    def test_post_paths(self):
        self.assertEqual(classify("https://www.facebook.com/Page/posts/123456789"),
                         ("post", "123456789"))
        self.assertEqual(
            classify("https://www.facebook.com/groups/555/permalink/123456789"),
            ("post", "123456789"))
        self.assertEqual(
            classify("https://www.facebook.com/permalink.php?story_fbid=123456789&id=555"),
            ("post", "123456789"))

    def test_photo_and_video(self):
        self.assertEqual(classify("https://www.facebook.com/photo.php?fbid=123456789"),
                         ("photo", "123456789"))
        self.assertEqual(classify("https://www.facebook.com/watch?v=123456789"),
                         ("video", "123456789"))
        kind, _ = classify("https://fb.watch/xK29dPwQ1a")
        self.assertEqual(kind, "video")

    def test_profile_and_comment_are_not_posts(self):
        self.assertEqual(classify("https://www.facebook.com/profile.php?id=100012345"),
                         ("unknown", None))
        kind, _ = classify(
            "https://www.facebook.com/Page/posts/123456789?comment_id=42")
        self.assertEqual(kind, "unknown")

    def test_short_numeric_ids_rejected(self):
        self.assertEqual(classify("https://www.facebook.com/photo.php?fbid=123"),
                         ("unknown", None))


class TestValidate(unittest.TestCase):
    def test_external_host_invalid(self):
        cand = validate_candidate(Candidate(raw_url="https://evil.example.com/posts/123456789"))
        self.assertEqual(cand.validation_status, INVALID_URL)

    def test_valid_post(self):
        cand = validate_candidate(
            Candidate(raw_url="https://www.facebook.com/Page/posts/123456789"))
        self.assertEqual(cand.validation_status, VALID_FORMAT)
        self.assertEqual(cand.object_type, "post")
        self.assertEqual(cand.object_id, "123456789")

    def test_garbage_invalid(self):
        cand = validate_candidate(Candidate(raw_url="not a url"))
        self.assertEqual(cand.validation_status, INVALID_URL)


if __name__ == "__main__":
    unittest.main()
