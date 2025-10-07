from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


# Load from .env in local/dev; noop if file is absent
load_dotenv()


@dataclass(frozen=True)
class AppConfig:
    aiblock_passphrase: str
    storage_host: Optional[str]
    mempool_host: Optional[str]
    valence_host: Optional[str]
    log_level: str


def get_config() -> AppConfig:
    return AppConfig(
        aiblock_passphrase=os.environ.get("AIBLOCK_PASSPHRASE", ""),
        storage_host=os.environ.get("AIBLOCK_STORAGE_HOST"),
        mempool_host=os.environ.get("AIBLOCK_MEMPOOL_HOST"),
        valence_host=os.environ.get("AIBLOCK_VALENCE_HOST"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )


