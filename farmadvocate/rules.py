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
_ANYNUM = re.compile(rf"(?<![\w.])({_NUM})(?!\d)")  # letters may follow: tables glue units ('20kgperhectare')


def _norm(n):
    n = n.replace(",", "")
    if "." in n:
        n = n.rstrip("0").rstrip(".")
    return n


# Unit families: a number only counts as supported if the context uses it with a compatible unit.
_FAMILY = {}
for _fam, _us in {"mass": "kg g mg t tonne tonnes q quintal quintals", "volume": "ml l litre litres liter liters",
                  "pct": "% percent per cent", "length": "cm mm m", "time": "day days week weeks hr hrs hour hours das dat dap",
                  "area": "ha hectare hectares acre acres cent cents"}.items():
    for _u in _us.split():
        _FAMILY[_u] = _fam
_UNIT_ALT = "|".join(sorted((re.escape(u) for u in _FAMILY), key=len, reverse=True))
# After a number: multi-letter units may be glued to following text ('20kgperhectare'); single letters may not.
_AFTER = re.compile(rf"\s*(?:({_UNIT_ALT})(?![a-z])|((?:kg|mg|ml|cm|mm|ha|das|dat|dap)))", re.I)


def _family_after(text, end):
    m = _AFTER.match(text, end)
    if not m:
        return None  # bare number, e.g. a table cell
    return _FAMILY.get((m.group(1) or m.group(2)).lower())


def _numbers(text):
    return {_norm(m.group(1)) for m in _ANYNUM.finditer(text)}


def _supported(text):
    """Set of (number, family) pairs in text; family is None for numbers with no unit."""
    return {(_norm(m.group(1)), _family_after(text, m.end())) for m in _ANYNUM.finditer(text)}


_ORD = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth", 7: "seventh",
        8: "eighth", 9: "ninth", 10: "tenth", 11: "eleventh", 12: "twelfth"}


def normalize_ordinals(text):
    """'1st week' -> 'first week' so translators that write ordinals in words keep the meaning."""
    def sub(m):
        n = int(m.group(1))
        return _ORD.get(n, m.group(0))
    return re.sub(r"\b(\d{1,2})(?:st|nd|rd|th)\b", sub, text)


def _ratios(text):
    out = set()
    for m in _RATIO.finditer(text):
        out.add(":".join(_norm(g) for g in m.groups() if g))
    return out


def verify_numbers(answer, context):
    """Every quantity-with-unit and every ratio in the answer must appear in the context.

    A number must appear in the context with a compatible unit family (so '125 kg' is not
    supported by '125 ml'), or with no unit at all (table cells). Unit spellings such as
    kg/ha and kg per hectare share a family. Returns (ok, list_of_missing_items).
    """
    ctx_sup = _supported(context)
    ctx_ratios = _ratios(context)
    missing = []
    for m in _QTY.finditer(answer):
        fam = _family_after(answer, m.start(1) + len(m.group(1)) if not m.group(2) else m.start(2) + len(m.group(2)))
        for g in (m.group(1), m.group(2)):
            if g and (_norm(g), fam) not in ctx_sup and (_norm(g), None) not in ctx_sup:
                missing.append(m.group(0).strip())
                break
    for r in _ratios(answer):
        if r not in ctx_ratios:
            missing.append(r)
    return (not missing), missing
