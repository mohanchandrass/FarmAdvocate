"""Saved answers for the example and test questions, so common demo queries need no GPU quota."""
import json
import re

from . import config

CACHE_PATH = config.ROOT / "data" / "example_cache.json"
_WS = re.compile(r"\s+")


def cache_key(question, lang):
    return lang + "|" + _WS.sub(" ", question).strip().lower()


def is_quota_error(exc):
    """True if an exception from the GPU call is Hugging Face's ZeroGPU quota error."""
    msg = str(exc).lower()
    return "quota" in msg or "zerogpu" in msg


def load():
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
