"""Flask webhook server for automated PR reviews."""

import json
import logging
from flask import Flask, request, jsonify

from .config import AppConfig
from .mimo_client import MiMoClient
from .github_client import GitHubClient
from .reviewer import CodeReviewer

logger = logging.getLogger(__name__)


def create_app(config: AppConfig) -> Flask:
    app = Flask(__name__)
    mimo = MiMoClient(config.mimo)
    github = GitHubClient(config.github)
    reviewer = CodeReviewer(mimo, github)

    @app.route("/health", methods=["GET"])
    def health():
        mimo_ok = mimo.health_check()
        return jsonify({
            "status": "healthy" if mimo_ok else "degraded",
            "mimo_api": "connected" if mimo_ok else "unreachable",
            "version": "1.0.0",
        })

    @app.route("/stats", methods=["GET"])
    def stats():
        return jsonify(reviewer.get_stats())

    @app.route("/review", methods=["POST"])
    def review_pr():
        """Manually trigger a PR review."""
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400

        owner = data.get("owner")
        repo = data.get("repo")
        pr_number = data.get("pr_number")
        post_comment = data.get("post_comment", True)

        if not all([owner, repo, pr_number]):
            return jsonify({"error": "owner, repo, pr_number required"}), 400

        try:
            result = reviewer.review_pr(owner, repo, int(pr_number), post_comment)
            return jsonify({
                "status": "success",
                "pr_url": result.pr_url,
                "files_analyzed": result.files_analyzed,
                "issues_found": result.issues_found,
                "tokens_used": result.tokens_used,
                "cost_usd": result.cost_usd,
                "summary": result.summary,
                "review": result.review,
            })
        except Exception as e:
            logger.exception("Review failed")
            return jsonify({"error": str(e)}), 500

    @app.route("/review/diff", methods=["POST"])
    def review_diff():
        """Review a raw diff."""
        data = request.get_json()
        if not data or "diff" not in data:
            return jsonify({"error": "JSON body with 'diff' field required"}), 400

        try:
            result = reviewer.review_diff(
                data["diff"],
                data.get("title", ""),
            )
            return jsonify({
                "status": "success",
                "files_analyzed": result.files_analyzed,
                "issues_found": result.issues_found,
                "tokens_used": result.tokens_used,
                "cost_usd": result.cost_usd,
                "summary": result.summary,
                "review": result.review,
            })
        except Exception as e:
            logger.exception("Review failed")
            return jsonify({"error": str(e)}), 500

    @app.route("/webhook", methods=["POST"])
    def github_webhook():
        """Handle GitHub webhook events for auto-review."""
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not github.verify_webhook_signature(request.data, signature):
            return jsonify({"error": "Invalid signature"}), 401

        event = request.headers.get("X-GitHub-Event", "")
        if event != "pull_request":
            return jsonify({"status": "ignored", "event": event}), 200

        payload = request.get_json()
        action = payload.get("action", "")
        if action not in ("opened", "synchronize", "reopened"):
            return jsonify({"status": "ignored", "action": action}), 200

        pr = payload.get("pull_request", {})
        repo_full = payload.get("repository", {}).get("full_name", "")
        pr_number = pr.get("number")

        if not repo_full or not pr_number:
            return jsonify({"error": "Invalid payload"}), 400

        owner, repo = repo_full.split("/", 1)
        logger.info("Webhook: %s on %s/%s#%d", action, owner, repo, pr_number)

        try:
            result = reviewer.review_pr(owner, repo, pr_number)
            return jsonify({
                "status": "reviewed",
                "pr": f"{owner}/{repo}#{pr_number}",
                "issues_found": result.issues_found,
            })
        except Exception as e:
            logger.exception("Webhook review failed")
            return jsonify({"error": str(e)}), 500

    return app
