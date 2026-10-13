"""Shared Gemini client: one client per process, retries with exponential backoff, and a minimum gap between calls.

Used by generate.py (answers) and embed.py (embeddings). Nothing else should call the Gemini SDK directly.
"""
from __future__ import annotations

import logging
import random
import time
from typing import Any, Callable, TypeVar

import httpx
from google import genai
from google.genai import errors, types

from plant_rag.config import load_api_key

log = logging.getLogger(__name__)
T = TypeVar("T")

RETRY_STATUS = {429, 500, 502, 503, 504}

_client: genai.Client | None = None
_last_call = 0.0
_api_calls = 0


def get_client(cfg: dict[str, Any]) -> genai.Client:
    global _client
    if _client is None:
        key, source = load_api_key(cfg)
        timeout_ms = int(float(cfg["api"]["timeout_s"]) * 1000)
        _client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=timeout_ms))
        log.info("Gemini client ready (API key from %s)", source)
    return _client


def api_call_count() -> int:
    """Number of real API requests sent in this process (cache hits don't count)."""
    return _api_calls


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, errors.APIError):
        return exc.code in RETRY_STATUS
    return isinstance(exc, (httpx.TimeoutException, httpx.TransportError))


def call_with_retry(fn: Callable[[], T], cfg: dict[str, Any], what: str = "Gemini call") -> T:
    """Run `fn` with rate limiting and retries on temporary errors (429, 5xx, timeouts, network)."""
    global _last_call, _api_calls
    api = cfg["api"]
    max_retries = int(api["max_retries"])

    for attempt in range(max_retries + 1):
        wait = float(api["min_interval_s"]) - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()
        _api_calls += 1
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - re-raised below unless retryable
            if not _is_retryable(exc) or attempt == max_retries:
                raise
            delay = min(float(api["backoff_base_s"]) * 2**attempt, float(api["backoff_max_s"]))
            delay *= random.uniform(0.8, 1.2)
            code = getattr(exc, "code", type(exc).__name__)
            log.warning("%s failed (%s); retry %d/%d in %.1fs", what, code, attempt + 1, max_retries, delay)
            time.sleep(delay)
    raise AssertionError("unreachable")
