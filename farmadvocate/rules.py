"""Pure-Python rules: scope router, crop detection, numeric verifier. No model dependencies."""
import re

from . import config


def _has_term(text, terms):
    t = text.lower()
    return any(re.search(rf"\b{re.escape(w)}\b", t) for w in terms)


def route(question_en):
    """Return 'out_of_scope', 'unsupported_crop' or None (continue to retrieval)."""
    if _has_term(question_en, config.PEST_TERMS) or _has_term(question_en, config.OFF_TOPIC_TERMS):
        return "out_of_scope"
    return None


def detect_crop(question_en):
    """Return (crop or None, unsupported: bool). Supported crops win over unsupported mentions."""
    t = question_en.lower()
    for crop, aliases in config.CROP_ALIASES.items():
        if any(re.search(rf"\b{re.escape(a)}\b", t) for a in aliases):
            return crop, False
    if _has_term(question_en, config.OUT_OF_CORPUS_CROPS):
        return None, True
    return None, False


# ---------------------------------------------------------------- numeric verifier
_UNITS = r"(?:kg|g|mg|ml|litres?|liters?|l|tonnes?|t|q|quintals?|%|per\s*cent|percent|cm|mm|m|days?|weeks?|hrs?|hours?|ha|hectares?|acres?|cents?|dap|das|dat)"
_NUM = r"\d+(?:,\d{3})*(?:\.\d+)?"
_QTY = re.compile(rf"(?<![\w.])({_NUM})(?:\s*(?:-|–|to)\s*({_NUM}))?\s*(?:{_UNITS})(?![A-Za-z])", re.I)
_RATIO = re.compile(r"(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)(?:\s*:\s*(\d+(?:\.\d+)?))?")
_ANYNUM = re.compile(rf"(?<![\w.])({_NUM})(?![\w])")


def _norm(n):
    n = n.replace(",", "")
    if "." in n:
        n = n.rstrip("0").rstrip(".")
    return n


def _numbers(text):
    return {_norm(m.group(1)) for m in _ANYNUM.finditer(text)}


def _ratios(text):
    out = set()
    for m in _RATIO.finditer(text):
        out.add(":".join(_norm(g) for g in m.groups() if g))
    return out


def verify_numbers(answer, context):
    """Every quantity-with-unit and every ratio in the answer must appear in the context.

    Unit variants (kg/ha, kg per hectare) are handled by matching on the number, so they
    cannot cause false alarms. Returns (ok, list_of_missing_items).
    """
    ctx_nums = _numbers(context)
    ctx_ratios = _ratios(context)
    missing = []
    for m in _QTY.finditer(answer):
        for g in (m.group(1), m.group(2)):
            if g and _norm(g) not in ctx_nums:
                missing.append(m.group(0).strip())
                break
    for r in _ratios(answer):
        if r not in ctx_ratios:
            missing.append(r)
    return (not missing), missing
