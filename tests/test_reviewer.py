"""Tests for review engine."""

import unittest
from unittest.mock import MagicMock, patch
from reviewer.reviewer import CodeReviewer, _count_issues, _format_review_comment, ReviewResult
from reviewer.mimo_client import MiMoClient, ReviewResponse
from reviewer.github_client import GitHubClient
from reviewer.config import MiMoConfig, GitHubConfig


class TestCountIssues(unittest.TestCase):
    def test_counts_critical(self):
        text = "Line 10: CRITICAL - SQL injection\nLine 20: WARNING - no error handling"
        self.assertEqual(_count_issues(text), 2)

    def test_counts_bug(self):
        text = "Found a bug in the parsing logic"
        self.assertEqual(_count_issues(text), 1)

    def test_counts_security(self):
        text = "Security vulnerability: hardcoded password"
        self.assertEqual(_count_issues(text), 1)

    def test_no_issues(self):
        text = "Code looks good. No problems found."
        self.assertEqual(_count_issues(text), 0)

    def test_multiple_markers_per_line(self):
        text = "CRITICAL security vulnerability: error in auth"
        count = _count_issues(text)
        self.assertGreaterEqual(count, 1)


class TestFormatReviewComment(unittest.TestCase):
    def test_format_includes_header(self):
        result = ReviewResult(
            pr_url="https://github.com/test/repo/pull/1",
            summary="Good changes",
            review="Looks fine",
            files_analyzed=3,
            total_additions=50,
            total_deletions=10,
            tokens_used=1500,
            latency_ms=2000,
            cost_usd=0.00015,
            issues_found=2,
        )
        comment = _format_review_comment(result)
        self.assertIn("MiMo Code Review", comment)
        self.assertIn("3 files", comment)
        self.assertIn("+50", comment)
        self.assertIn("-10", comment)

    def test_format_includes_summary(self):
        result = ReviewResult(
            pr_url="",
            summary="Test summary content",
            review="Test review content",
            files_analyzed=1,
            total_additions=5,
            total_deletions=2,
            tokens_used=500,
            latency_ms=1000,
            cost_usd=0.00005,
            issues_found=0,
        )
        comment = _format_review_comment(result)
        self.assertIn("Test summary content", comment)
        self.assertIn("Test review content", comment)


class TestCodeReviewer(unittest.TestCase):
    def setUp(self):
        self.mimo = MiMoClient(MiMoConfig(api_key="test"))
        self.github = GitHubClient(GitHubConfig(token="test"))
        self.reviewer = CodeReviewer(self.mimo, self.github)

    def test_stats_initial(self):
        stats = self.reviewer.get_stats()
        self.assertEqual(stats["reviewer"]["total_reviews"], 0)
        self.assertEqual(stats["reviewer"]["total_files_analyzed"], 0)

    def test_review_diff_mock(self):
        mock_resp = ReviewResponse(
            content="Looks good",
            model="mimo-v2.5",
            tokens_used=100,
            latency_ms=500,
            cost_estimate=0.00001,
        )
        self.mimo.review = MagicMock(return_value=mock_resp)
        diff = """diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
@@ -1,3 +1,4 @@
 def hello():
+    print("world")
     return True
"""
        result = self.reviewer.review_diff(diff, "Add print")
        self.assertEqual(result.files_analyzed, 1)
        self.assertEqual(result.tokens_used, 200)  # 2 calls

    def test_stats_after_diff_review(self):
        mock_resp = ReviewResponse(
            content="No issues",
            model="mimo-v2.5",
            tokens_used=50,
            latency_ms=300,
            cost_estimate=0.000005,
        )
        self.mimo.review = MagicMock(return_value=mock_resp)
        self.reviewer.review_diff("diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-old\n+new")
        stats = self.reviewer.get_stats()
        self.assertEqual(stats["reviewer"]["total_reviews"], 0)  # diff review doesn't increment


if __name__ == "__main__":
    unittest.main()
