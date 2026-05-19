"""CLI interface for reviewing PRs and diffs from command line."""

import sys
import argparse
import subprocess
import logging

from dotenv import load_dotenv

from .config import AppConfig
from .mimo_client import MiMoClient
from .github_client import GitHubClient
from .reviewer import CodeReviewer

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")


def parse_pr_url(url: str) -> tuple[str, str, int]:
    """Parse a GitHub PR URL into (owner, repo, number)."""
    # https://github.com/owner/repo/pull/123
    parts = url.rstrip("/").split("/")
    if "github.com" in url and "pull" in parts:
        idx = parts.index("pull")
        owner = parts[idx - 2]
        repo = parts[idx - 1]
        number = int(parts[idx + 1])
        return owner, repo, number
    raise ValueError(f"Invalid PR URL: {url}")


def get_local_diff() -> str:
    """Get the staged diff from git."""
    result = subprocess.run(
        ["git", "diff", "--staged"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        result = subprocess.run(
            ["git", "diff"],
            capture_output=True,
            text=True,
        )
    return result.stdout


def main():
    parser = argparse.ArgumentParser(
        description="MiMo Code Reviewer - AI-powered code review",
    )
    sub = parser.add_subparsers(dest="command")

    # review PR
    pr_cmd = sub.add_parser("pr", help="Review a GitHub PR")
    pr_cmd.add_argument("url", help="GitHub PR URL")
    pr_cmd.add_argument("--no-comment", action="store_true", help="Don't post comment")

    # review diff
    diff_cmd = sub.add_parser("diff", help="Review local diff")
    diff_cmd.add_argument("--file", help="Diff file path (default: git diff)")
    diff_cmd.add_argument("--title", default="", help="PR/change title")

    # server
    srv_cmd = sub.add_parser("serve", help="Start webhook server")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    config = AppConfig.from_env()
    if not config.mimo.api_key:
        print("Error: MIMO_API_KEY not set")
        sys.exit(1)

    mimo = MiMoClient(config.mimo)
    github = GitHubClient(config.github)
    reviewer = CodeReviewer(mimo, github)

    if args.command == "pr":
        owner, repo, number = parse_pr_url(args.url)
        print(f"Reviewing {owner}/{repo}#{number}...")
        result = reviewer.review_pr(owner, repo, number, not args.no_comment)
        print(f"\n{'='*60}")
        print(f"Files: {result.files_analyzed} | "
              f"+{result.total_additions} -{result.total_deletions}")
        print(f"Issues: {result.issues_found} | "
              f"Tokens: {result.tokens_used} | "
              f"Cost: ${result.cost_usd:.6f}")
        print(f"{'='*60}\n")
        print("## Summary\n")
        print(result.summary)
        print(f"\n## Review\n")
        print(result.review)

    elif args.command == "diff":
        if args.file:
            with open(args.file) as f:
                diff_text = f.read()
        else:
            diff_text = get_local_diff()
            if not diff_text:
                print("No diff found. Stage changes with 'git add' first.")
                sys.exit(1)

        print("Reviewing diff...")
        result = reviewer.review_diff(diff_text, args.title)
        print(f"\nFiles: {result.files_analyzed} | "
              f"Issues: {result.issues_found} | "
              f"Tokens: {result.tokens_used}")
        print(f"\n## Summary\n")
        print(result.summary)
        print(f"\n## Review\n")
        print(result.review)

    elif args.command == "serve":
        from .server import create_app
        app = create_app(config)
        app.run(host=config.server.host, port=config.server.port)


if __name__ == "__main__":
    main()
