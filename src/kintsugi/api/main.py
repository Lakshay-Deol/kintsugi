"""Entry point for Kintsugi API server."""
from __future__ import annotations
import logging
import os

import uvicorn
from kintsugi.api.app import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = create_app()


def run() -> None:
    cfg_host = os.environ.get("API_HOST", "0.0.0.0")
    cfg_port = int(os.environ.get("API_PORT", "8080"))
    uvicorn.run(
        "kintsugi.api.main:app",
        host=cfg_host,
        port=cfg_port,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    run()
