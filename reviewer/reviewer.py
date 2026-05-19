"""Core review engine - orchestrates diff analysis and MiMo review."""

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from .analyzer import parse_diff, build_review_prompt, build_summary_prompt, FileAnalysis
from .mimo_client import MiMoClient, ReviewResponse
from .github_client import GitHubClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are MiMo Code Reviewer, an AI-powered code review assistant built on Xiaomi MiMo V2.5.
You provide thorough, constructive code reviews focused on:
- Finding real bugs and logic errors (not nitpicking)
- Identifying security vulnerabilities
- Suggesting performance improvements
- Recommending best practices

Be specific, cite line numbers, and provide code examples for fixes.
Be constructive - acknowledge good code alongside issues.
Keep reviews concise but thorough."""

MAX_DIFF_SIZE = 50000  # chars
MAX_FILES = 30


@dataclass
class ReviewResult:
    pr_url: str
    summary: str
    review: str
    files_analyzed: int
    total_additions: int
    total_deletions: int
    tokens_used: int
    latency_ms: float
    cost_usd: float
    issues_found: int = 0
    score: Optional[int] = None


@dataclass
class ReviewStats:
    total_reviews: int = 0
    total_files: int = 0
    total_tokens: int = 0
    total_issues: int = 0
    total_cost: float = 0.0
    reviews: list[dict] = field(default_factory=list)


class CodeReviewer:
    """Main code review orchestrator."""

    def __init__(self, mimo: MiMoClient, github: GitHubClient):
        self.mimo = mimo
        self.github = github
        self.stats = ReviewStats()

    def review_pr(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        post_comment: bool = True,
    ) -> ReviewResult:
        """Review a pull request end-to-end."""
        logger.info("Starting review of %s/%s#%d", owner, repo, pr_number)

        # Fetch PR details
        pr = self.github.get_pr(owner, repo, pr_number)
        pr_title = pr.get("title", "")
        pr_body = pr.get("body", "") or ""

        # Fetch diff
        diff = self.github.get_pr_diff(owner, repo, pr_number)
        if len(diff) > MAX_DIFF_SIZE:
            diff = diff[:MAX_DIFF_SIZE]
            logger.warning("Diff truncated to %d chars", MAX_DIFF_SIZE)

        # Parse and analyze
        file_analyses = parse_diff(diff)
        if len(file_analyses) > MAX_FILES:
            file_analyses = file_analyses[:MAX_FILES]
            logger.warning("Limited to %d files", MAX_FILES)

        total_add = sum(f.additions for f in file_analyses)
        total_del = sum(f.deletions for f in file_analyses)

        # Generate summary
        summary_prompt = build_summary_prompt(file_analyses, pr_title, pr_body)
        summary_resp = self.mimo.review(summary_prompt, SYSTEM_PROMPT)

        # Generate detailed review
        review_prompt = build_review_prompt(file_analyses, pr_title, pr_body)
        review_resp = self.mimo.review(review_prompt, SYSTEM_PROMPT)

        total_tokens = summary_resp.tokens_used + review_resp.tokens_used
        total_latency = summary_resp.latency_ms + review_resp.latency_ms
        total_cost = summary_resp.cost_estimate + review_resp.cost_estimate

        # Count issues (rough heuristic)
        issues_found = _count_issues(review_resp.content)

        result = ReviewResult(
            pr_url=pr.get("html_url", ""),
            summary=summary_resp.content,
            review=review_resp.content,
            files_analyzed=len(file_analyses),
            total_additions=total_add,
            total_deletions=total_del,
            tokens_used=total_tokens,
            latency_ms=total_latency,
            cost_usd=total_cost,
            issues_found=issues_found,
        )

        # Post comment to PR
        if post_comment:
            comment_body = _format_review_comment(result)
            try:
                self.github.post_review_comment(owner, repo, pr_number, comment_body)
                logger.info("Posted review comment on %s/%s#%d", owner, repo, pr_number)
            except Exception as e:
                logger.error("Failed to post comment: %s", e)

        # Update stats
        self.stats.total_reviews += 1
        self.stats.total_files += len(file_analyses)
        self.stats.total_tokens += total_tokens
        self.stats.total_issues += issues_found
        self.stats.total_cost += total_cost
        self.stats.reviews.append({
            "pr": f"{owner}/{repo}#{pr_number}",
            "files": len(file_analyses),
            "issues": issues_found,
            "tokens": total_tokens,
            "cost": total_cost,
        })

        return result

    def review_diff(self, diff_text: str, title: str = "") -> ReviewResult:
        """Review a raw diff without GitHub integration."""
        file_analyses = parse_diff(diff_text)
        total_add = sum(f.additions for f in file_analyses)
        total_del = sum(f.deletions for f in file_analyses)

        review_prompt = build_review_prompt(file_analyses, title)
        review_resp = self.mimo.review(review_prompt, SYSTEM_PROMPT)

        summary_prompt = build_summary_prompt(file_analyses, title)
        summary_resp = self.mimo.review(summary_prompt, SYSTEM_PROMPT)

        total_tokens = summary_resp.tokens_used + review_resp.tokens_used

        return ReviewResult(
            pr_url="",
            summary=summary_resp.content,
            review=review_resp.content,
            files_analyzed=len(file_analyses),
            total_additions=total_add,
            total_deletions=total_del,
            tokens_used=total_tokens,
            latency_ms=summary_resp.latency_ms + review_resp.latency_ms,
            cost_usd=summary_resp.cost_estimate + review_resp.cost_estimate,
            issues_found=_count_issues(review_resp.content),
        )

    def get_stats(self) -> dict:
        return {
            "reviewer": {
                "total_reviews": self.stats.total_reviews,
                "total_files_analyzed": self.stats.total_files,
                "total_issues_found": self.stats.total_issues,
                "total_tokens": self.stats.total_tokens,
                "total_cost_usd": round(self.stats.total_cost, 6),
                "recent_reviews": self.stats.reviews[-10:],
            },
            "mimo": self.mimo.get_stats(),
        }


def _count_issues(review_text: str) -> int:
    """Count issues mentioned in review (heuristic)."""
    markers = ["CRITICAL", "WARNING", "bug", "security", "vulnerability", "issue", "error"]
    count = 0
    for line in review_text.splitlines():
        upper = line.upper()
        if any(m.upper() in upper for m in markers):
            count += 1
    return max(count, 0)


def _format_review_comment(result: ReviewResult) -> str:
    """Format review result as a GitHub comment."""
    return "\n".join([
        "## MiMo Code Review",
        "",
        f"*Powered by Xiaomi MiMo V2.5 | "
        f"{result.files_analyzed} files | "
        f"+{result.total_additions} -{result.total_deletions} lines | "
        f"{result.tokens_used} tokens*",
        "",
        "---",
        "",
        "### Summary",
        result.summary,
        "",
        "---",
        "",
        "### Detailed Review",
        result.review,
        "",
        "---",
        f"*Review cost: ${result.cost_usd:.6f} | "
        f"Latency: {result.latency_ms:.0f}ms | "
        f"Issues found: {result.issues_found}*",
    ])
