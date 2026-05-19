"""MiMo API client for code review inference."""

import json
import time
import logging
from dataclasses import dataclass
from typing import Optional

import requests

from .config import MiMoConfig

logger = logging.getLogger(__name__)


@dataclass
class ReviewResponse:
    content: str
    model: str
    tokens_used: int
    latency_ms: float
    cost_estimate: float


class MiMoClient:
    """Client for Xiaomi MiMo V2.5 API."""

    def __init__(self, config: MiMoConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        })
        self.total_tokens = 0
        self.total_requests = 0
        self.total_cost = 0.0

    def review(self, prompt: str, system_prompt: Optional[str] = None) -> ReviewResponse:
        """Send a review request to MiMo API."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": False,
        }

        start = time.time()
        try:
            resp = self.session.post(
                f"{self.config.api_base}/chat/completions",
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            logger.error("MiMo API request failed: %s", e)
            raise

        latency_ms = (time.time() - start) * 1000
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        tokens = usage.get("total_tokens", 0)
        cost = tokens * 0.0000001  # MiMo is extremely cheap

        self.total_tokens += tokens
        self.total_requests += 1
        self.total_cost += cost

        return ReviewResponse(
            content=content,
            model=data.get("model", self.config.model),
            tokens_used=tokens,
            latency_ms=latency_ms,
            cost_estimate=cost,
        )

    def get_stats(self) -> dict:
        return {
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost, 6),
            "avg_tokens_per_request": (
                self.total_tokens // self.total_requests
                if self.total_requests > 0
                else 0
            ),
        }

    def health_check(self) -> bool:
        """Check if MiMo API is reachable."""
        try:
            resp = self.session.get(
                f"{self.config.api_base}/models",
                timeout=10,
            )
            return resp.status_code == 200
        except requests.exceptions.RequestException:
            return False
