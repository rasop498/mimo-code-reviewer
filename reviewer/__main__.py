"""Entry point for MiMo Code Review Agent."""

import sys
import logging
from dotenv import load_dotenv

from .config import AppConfig
from .server import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

load_dotenv()


def main():
    config = AppConfig.from_env()

    if not config.mimo.api_key:
        print("Error: MIMO_API_KEY not set. Get one from https://platform.xiaomimimo.com")
        sys.exit(1)

    app = create_app(config)
    print(f"MiMo Code Review Agent v1.0.0")
    print(f"Listening on {config.server.host}:{config.server.port}")
    print(f"Model: {config.mimo.model}")
    print(f"Endpoints:")
    print(f"  POST /review        - Review a PR")
    print(f"  POST /review/diff   - Review raw diff")
    print(f"  POST /webhook       - GitHub webhook")
    print(f"  GET  /health        - Health check")
    print(f"  GET  /stats         - Usage statistics")
    app.run(
        host=config.server.host,
        port=config.server.port,
        debug=config.server.debug,
    )


if __name__ == "__main__":
    main()
