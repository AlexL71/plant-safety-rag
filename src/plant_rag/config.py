"""Load the YAML config, resolve paths, and load the Gemini API key.

The API key is never printed or logged. Only its source ("env" or "file") is reported.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

# src/plant_rag/config.py -> repo root is two levels above the package folder
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "configs" / "config.yaml"


def resolve_path(p: str | Path) -> Path:
    """Absolute paths stay as they are; relative paths are taken from the repo root."""
    p = Path(p)
    return p if p.is_absolute() else REPO_ROOT / p


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Read the YAML config and turn every entry under `paths` into an absolute Path."""
    cfg_path = Path(path) if path else DEFAULT_CONFIG
    if not cfg_path.is_absolute() and not cfg_path.exists():
        cfg_path = REPO_ROOT / cfg_path
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found: {cfg_path}")

    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    cfg["paths"] = {k: resolve_path(v) for k, v in (cfg.get("paths") or {}).items()}
    cfg["_config_path"] = cfg_path
    return cfg


def _parse_key_file(text: str) -> str:
    """Take the first non-empty, non-comment line. Accepts `KEY=value` and quoted values."""
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            line = line.split("=", 1)[1].strip()
        return line.strip("'\"")
    return ""


def load_api_key(cfg: dict[str, Any]) -> tuple[str, str]:
    """Return (key, source). Env var first, then the key file. Raises with a clear message if missing."""
    key_cfg = cfg.get("api_key") or {}
    env_var = key_cfg.get("env_var", "GEMINI_API_KEY")
    key_file = resolve_path(key_cfg.get("file", "secrets/gemini_api_key.txt"))

    key = os.environ.get(env_var, "").strip()
    if key:
        return key, "env"

    if key_file.exists():
        key = _parse_key_file(key_file.read_text(encoding="utf-8-sig"))
        if key:
            if any(c.isspace() for c in key):
                raise ValueError(f"The key in {key_file.name} contains spaces; it should be one token on one line.")
            return key, "file"

    raise RuntimeError(
        f"No Gemini API key found. Set the {env_var} environment variable "
        f"or put the key in {key_file} (one line, key only)."
    )
