"""Configuration loading: YAML for parameters, .env for secrets."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()  # pull .env into os.environ if present


@dataclass
class Credentials:
    """Secrets sourced exclusively from environment variables."""

    kite_api_key: str = field(default_factory=lambda: os.getenv("KITE_API_KEY", ""))
    kite_api_secret: str = field(default_factory=lambda: os.getenv("KITE_API_SECRET", ""))
    kite_access_token: str = field(default_factory=lambda: os.getenv("KITE_ACCESS_TOKEN", ""))

    delta_api_key: str = field(default_factory=lambda: os.getenv("DELTA_API_KEY", ""))
    delta_api_secret: str = field(default_factory=lambda: os.getenv("DELTA_API_SECRET", ""))
    delta_base_url: str = field(
        default_factory=lambda: os.getenv("DELTA_BASE_URL", "https://api.india.delta.exchange")
    )


def trading_mode() -> str:
    """'paper' (default, safe) or 'live'."""
    return os.getenv("TRADING_MODE", "paper").strip().lower()


def load_config(path: str = "config.yaml") -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)
