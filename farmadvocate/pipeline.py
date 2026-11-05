"""End-to-end pipeline: translate -> route -> detect crop -> retrieve -> generate -> verify -> translate."""
import time

import torch

from . import config, rules
from .generate import Generator
from .retrieve import Retriever
from .translate import Translator

_state = {}


def load():
    """Load all models once (at import time on a ZeroGPU Space)."""
    if _state:
        return _state
    device = "cuda" if torch.cuda.is_available() else "cpu"
    _state.update(device=device, retriever=Retriever(), translator=Translator(device),
                  generator=Generator(device))
    return _state


def _refusal(status, lang, tr):
    en = config.MESSAGES[status]
    local, ok = tr.from_en(en, lang)
    return local if ok else en, en


def _source(score, c):
    pages = c["page_start"] if c["page_start"] == c["page_end"] else f"{c['page_start']}-{c['page_end']}"
    return {"crop": c["crop"], "system": c.get("system", ""), "section": c["section"], "page": pages,
            "score": round(score, 3), "text": c["text"]}


def quick_refusal(question, lang):
    """Refuse an English pest, off-topic or unsupported-crop question without touching a GPU.

    Returns the same result dict as answer(), or None if the question should go through the full pipeline.
    Hindi and Kannada need the translator first, so they always take the full path.
    """
    if lang != "en":
        return None
    if rules.route(question):
        status = "out_of_scope"
    elif rules.detect_crop(question)[1]:
        status = "unsupported_crop"
    else:
        return None
    msg = config.MESSAGES[status]
    return {"status": status, "answer": msg, "answer_en": msg, "sources": [], "question_en": question,
            "crop": None, "top_score": None, "raw_answer_en": None, "verifier_ok": None, "missing_numbers": [],
            "failed_reason": None, "numbers_preserved": True, "seconds": 0.0}


def answer(question, lang="en", mode="rag"):
    """mode='rag' is the full system; mode='closed_book' is baseline A (no router, no retrieval)."""
    s = load()
    tr, gen, ret = s["translator"], s["generator"], s["retriever"]
    t0 = time.time()
    q_en = tr.to_en(question, lang)
    out = {"status": "", "answer": "", "answer_en": "", "sources": [], "question_en": q_en,
           "crop": None, "top_score": None, "raw_answer_en": None, "verifier_ok": None,
           "missing_numbers": [], "failed_reason": None, "numbers_preserved": True, "seconds": 0.0}

    if mode == "closed_book":
        out.update(status="closed_book", raw_answer_en=gen.answer_closed_book(q_en))
        out["answer_en"] = out["answer"] = out["raw_answer_en"]
        out["seconds"] = round(time.time() - t0, 1)
        return out

    verdict = rules.route(q_en)
    crop, unsupported = rules.detect_crop(q_en)
    if verdict == "out_of_scope":
        status = "out_of_scope"
    elif unsupported:
        status = "unsupported_crop"
    else:
        status = None
    if status:
        out["status"] = status
        out["answer"], out["answer_en"] = _refusal(status, lang, tr)
        out["seconds"] = round(time.time() - t0, 1)
        return out

    hits = ret.search(q_en, crop=crop)
    out["crop"], out["top_score"] = crop, round(hits[0][0], 3) if hits else None
    if not hits or hits[0][0] < config.SCORE_THRESHOLD:
        out["status"] = "not_found"
        out["answer"], out["answer_en"] = _refusal("not_found", lang, tr)
        out["seconds"] = round(time.time() - t0, 1)
        return out

    raw, used = gen.answer_with_context(q_en, [c["text"] for _, c in hits])
    out["raw_answer_en"] = raw
    out["sources"] = [_source(sc, c) for sc, c in hits[:max(1, len(used))]]
    ok, missing = rules.verify_numbers(raw, " ".join(used))
    fail = rules.answer_failed(raw, q_en)
    out["verifier_ok"], out["missing_numbers"], out["failed_reason"] = ok, missing, fail

    if fail == "declined" and not any(ch.isdigit() for ch in raw):
        out["status"], out["answer_en"] = "not_found", config.MESSAGES["not_found"]
        out["answer"], _ = tr.from_en(out["answer_en"], lang)
        out["seconds"] = round(time.time() - t0, 1)
        return out
    if ok and not fail:
        out["status"], out["answer_en"] = "verified", raw
    else:
        top = hits[0][1]["text"]
        out["status"] = "unverified"
        out["answer_en"] = config.MESSAGES["unverified"] + " " + top
    local, preserved = tr.from_en(out["answer_en"], lang)
    out["numbers_preserved"] = preserved
    out["answer"] = local if preserved else (
        out["answer_en"] + "\n\n(Translation withheld: numbers could not be preserved. Please rely on the English text.)")
    out["seconds"] = round(time.time() - t0, 1)
    return out
