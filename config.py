from __future__ import annotations
import os
from dataclasses import dataclass, asdict
from typing import Optional, Dict

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".IPDelisting")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.toml")

try:
    import tomllib  # type: ignore[reportMissingImports]  # Python 3.11+
except Exception:
    tomllib = None
import toml  # for writing (and reading if tomllib missing)


@dataclass
class AppConfig:
    email: str = ""
    phone: str = ""
    reason: str = "The user was blocked. Spam was stopped. Please delist it."
    headless: bool = True
    timeout_seconds: int = 60

    @classmethod
    def from_dict(cls, d: Dict) -> "AppConfig":
        def _as_str(x, default=""):
            try:
                s = str(x)
                return s if s is not None else default
            except Exception:
                return default

        def _as_bool(x, default=True):
            if isinstance(x, bool):
                return x
            s = str(x).strip().lower()
            if s in ("true", "1", "yes", "y", "on"):
                return True
            if s in ("false", "0", "no", "n", "off"):
                return False
            return default

        def _as_int(x, default=60):
            try:
                return int(str(x).strip())
            except Exception:
                return default

        return cls(
            email=_as_str(d.get("email", "")),
            phone=_as_str(d.get("phone", "")),
            reason=_as_str(d.get("reason", "The user was blocked. Spam was stopped. Please delist it.")),
            headless=_as_bool(d.get("headless", True)),
            timeout_seconds=_as_int(d.get("timeout_seconds", 60)),
        )


def ensure_dir() -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)


def load_config() -> AppConfig:
    ensure_dir()
    if not os.path.exists(CONFIG_FILE):
        return AppConfig()
    with open(CONFIG_FILE, "rb") as f:
        if tomllib is not None:
            data = tomllib.load(f)
        else:
            f.close()
            with open(CONFIG_FILE, "r", encoding="utf-8") as fr:
                data = toml.load(fr)
    return AppConfig.from_dict(data or {})


def save_config(cfg: AppConfig) -> None:
    ensure_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        toml.dump(asdict(cfg), f)
