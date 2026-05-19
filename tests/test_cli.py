"""Tests for CLI URL parser."""

import unittest
from reviewer.cli import parse_pr_url


class TestParsePrUrl(unittest.TestCase):
    def test_standard_url(self):
        owner, repo, num = parse_pr_url("https://github.com/torvalds/linux/pull/42")
        self.assertEqual(owner, "torvalds")
        self.assertEqual(repo, "linux")
        self.assertEqual(num, 42)

    def test_url_with_trailing_slash(self):
        owner, repo, num = parse_pr_url("https://github.com/owner/repo/pull/100/")
        self.assertEqual(owner, "owner")
        self.assertEqual(repo, "repo")
        self.assertEqual(num, 100)

    def test_invalid_url(self):
        with self.assertRaises(ValueError):
            parse_pr_url("https://google.com")

    def test_non_pr_github_url(self):
        with self.assertRaises(ValueError):
            parse_pr_url("https://github.com/owner/repo/issues/5")


if __name__ == "__main__":
    unittest.main()
