"""
Helpers for reading Files2Book configuration without exploding when the
config file is missing. Right now the only public API we need is
`get_font_path`, which returns an absolute path to the preferred font.
"""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_FONT_CANDIDATES = [
    PROJECT_ROOT / "FONTS" / "3270NerdFontMono-Regular.ttf",
    PROJECT_ROOT / "FONTS" / "3270NerdFont-Regular.ttf",
    PROJECT_ROOT / "FONTS" / "3270NerdFontPropo-Regular.ttf",
]


def _config_path() -> Path:
    """Resolve the config.json path (env override > repo root)."""
    env_override = os.getenv("FILES2BOOK_CONFIG")
    if env_override:
        return Path(env_override).expanduser()
    return PROJECT_ROOT / "config.json"


@lru_cache(maxsize=1)
def load_config() -> Dict[str, Any]:
    """Return parsed config.json (empty dict when missing/broken)."""
    cfg_path = _config_path()
    if not cfg_path.exists():
        return {}
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive logging
        logging.warning("Failed to read config.json at %s: %s", cfg_path, exc)
        return {}


def _resolve_path(value: str) -> Path:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return candidate


def get_font_path() -> str:
    """Return the configured font path or fall back to bundled fonts."""
    config = load_config()
    font_config: Optional[str] = None
    if isinstance(config.get("fonts"), dict):
        font_config = config["fonts"].get("primary") or config["fonts"].get("default")
    if not font_config:
        font_config = config.get("font_path")

    paths_to_try = []
    if font_config:
        paths_to_try.append(_resolve_path(font_config))
    paths_to_try.extend(DEFAULT_FONT_CANDIDATES)

    for path in paths_to_try:
        if path and path.exists():
            return str(path)

    # Last resort: let PIL pick whatever default font it has
    logging.warning("No configured font found; falling back to PIL default.")
    return ""


__all__ = ["load_config", "get_font_path"]
