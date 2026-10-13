"""Admin credentials: PBKDF2-SHA256 password hash in a git-ignored JSON file.

Create or change the admin account (asks for the password twice; nothing is echoed or logged):

    python -m app.auth --username admin
"""
from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import hmac
import json
import os
from pathlib import Path

from plant_rag.config import load_config, resolve_path

ITERATIONS = 310_000  # OWASP recommendation for PBKDF2-HMAC-SHA256


def hash_password(password: str, salt: bytes | None = None) -> dict[str, str | int]:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return {"algo": "pbkdf2_sha256", "iterations": ITERATIONS,
            "salt": base64.b64encode(salt).decode(), "hash": base64.b64encode(digest).decode()}


def credentials_path(cfg: dict) -> Path:
    return resolve_path(cfg["web"]["admin_credentials"])


def load_credentials(cfg: dict) -> dict | None:
    path = credentials_path(cfg)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def verify(cfg: dict, username: str, password: str) -> bool:
    creds = load_credentials(cfg)
    if not creds or not hmac.compare_digest(username.encode(), creds["username"].encode()):
        # still spend the time, so a wrong username is not faster than a wrong password
        hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), b"x" * 16, ITERATIONS)
        return False
    salt = base64.b64decode(creds["salt"])
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(creds["iterations"]))
    return hmac.compare_digest(base64.b64encode(digest).decode(), creds["hash"])


def save_credentials(cfg: dict, username: str, password: str) -> Path:
    path = credentials_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"username": username, **hash_password(password)}, indent=1), encoding="utf-8")
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description="Create or change the DocAgent admin account.")
    ap.add_argument("--username", default="admin")
    ap.add_argument("--config", default="configs/config.yaml")
    args = ap.parse_args()
    cfg = load_config(args.config)
    pw = getpass.getpass("New admin password (min 10 characters): ")
    if len(pw) < 10:
        raise SystemExit("Password too short (min 10 characters).")
    if getpass.getpass("Repeat password: ") != pw:
        raise SystemExit("Passwords do not match.")
    path = save_credentials(cfg, args.username, pw)
    print(f"Admin account '{args.username}' saved to {path} (password hash only).")


if __name__ == "__main__":
    main()
