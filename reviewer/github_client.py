"""GitHub API client for PR operations."""

import hmac
import hashlib
import logging
from typing import Optional

import requests

from .config import GitHubConfig

logger = logging.getLogger(__name__)


class GitHubClient:
    """Client for GitHub API - fetches PRs, posts reviews."""

    def __init__(self, config: GitHubConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {config.token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    def get_pr(self, owner: str, repo: str, pr_number: int) -> dict:
        """Fetch pull request details."""
        url = f"{self.config.api_base}/repos/{owner}/{repo}/pulls/{pr_number}"
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> str:
        """Fetch pull request diff."""
        url = f"{self.config.api_base}/repos/{owner}/{repo}/pulls/{pr_number}"
        headers = {"Accept": "application/vnd.github.v3.diff"}
        resp = self.session.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.text

    def get_pr_files(self, owner: str, repo: str, pr_number: int) -> list[dict]:
        """Fetch list of files changed in PR."""
        url = f"{self.config.api_base}/repos/{owner}/{repo}/pulls/{pr_number}/files"
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def post_review_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
    ) -> dict:
        """Post a general review comment on PR."""
        url = f"{self.config.api_base}/repos/{owner}/{repo}/issues/{pr_number}/comments"
        resp = self.session.post(url, json={"body": body}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def post_inline_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        commit_sha: str,
        file_path: str,
        line: int,
        body: str,
    ) -> dict:
        """Post an inline review comment on a specific line."""
        url = f"{self.config.api_base}/repos/{owner}/{repo}/pulls/{pr_number}/comments"
        payload = {
            "body": body,
            "commit_id": commit_sha,
            "path": file_path,
            "line": line,
            "side": "RIGHT",
        }
        resp = self.session.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def submit_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
        event: str = "COMMENT",
        comments: Optional[list[dict]] = None,
    ) -> dict:
        """Submit a full PR review with optional inline comments."""
        url = f"{self.config.api_base}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        payload = {
            "body": body,
            "event": event,
        }
        if comments:
            payload["comments"] = comments
        resp = self.session.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify GitHub webhook signature."""
        if not self.config.webhook_secret:
            return True
        expected = "sha256=" + hmac.new(
            self.config.webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
