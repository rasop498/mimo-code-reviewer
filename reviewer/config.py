"""Configuration management for MiMo Code Review Agent."""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MiMoConfig:
    api_key: str = ""
    api_base: str = "https://platform.xiaomimimo.com/api/v1"
    model: str = "mimo-v2.5-instruct"
    max_tokens: int = 4096
    temperature: float = 0.3


@dataclass
class GitHubConfig:
    token: str = ""
    webhook_secret: str = ""
    api_base: str = "https://api.github.com"


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 9900
    debug: bool = False


@dataclass
class AppConfig:
    mimo: MiMoConfig = field(default_factory=MiMoConfig)
    github: GitHubConfig = field(default_factory=GitHubConfig)
    server: ServerConfig = field(default_factory=ServerConfig)

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            mimo=MiMoConfig(
                api_key=os.getenv("MIMO_API_KEY", ""),
                api_base=os.getenv("MIMO_API_BASE", "https://platform.xiaomimimo.com/api/v1"),
                model=os.getenv("MIMO_MODEL", "mimo-v2.5-instruct"),
            ),
            github=GitHubConfig(
                token=os.getenv("GITHUB_TOKEN", ""),
                webhook_secret=os.getenv("GITHUB_WEBHOOK_SECRET", ""),
            ),
            server=ServerConfig(
                host=os.getenv("HOST", "0.0.0.0"),
                port=int(os.getenv("PORT", "9900")),
                debug=os.getenv("DEBUG", "").lower() == "true",
            ),
        )
