"""MongoDB Atlas client - single shared connection."""
from __future__ import annotations

import logging
import time
from functools import lru_cache
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection

from kintsugi.config import get_config

log = logging.getLogger(__name__)

_last_ping_time: float = 0.0
_last_ping_result: bool = False


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    cfg = get_config()
    client: MongoClient = MongoClient(cfg.mongodb_uri, serverSelectionTimeoutMS=2000)
    log.info("MongoDB Atlas client created (db=%s)", cfg.mongodb_db)
    return client


def get_db() -> Database:
    cfg = get_config()
    return get_client()[cfg.mongodb_db]


def get_collection(name: str) -> Collection:
    return get_db()[name]


def ping_atlas(force: bool = False) -> bool:
    """Return True if Atlas is reachable. Caches result for 60 seconds to prevent per-query timeouts."""
    global _last_ping_time, _last_ping_result
    now = time.monotonic()
    if not force and (now - _last_ping_time < 60.0):
        return _last_ping_result

    _last_ping_time = now
    try:
        get_client().admin.command("ping")
        _last_ping_result = True
    except Exception as exc:
        log.warning("Atlas ping failed (cached for 60s): %s", exc)
        _last_ping_result = False
    return _last_ping_result
