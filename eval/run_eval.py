"""Evaluation runner.

  python eval/run_eval.py retrieval   # CPU only: router + retrieval on English meanings (no LLM)
  python eval/run_eval.py full        # GPU: full pipeline on all 50 cases + closed-book baseline
  python eval/run_eval.py metrics     # compute metrics from eval/results/*.jsonl

Configurations compared on the same 24 English questions:
  A closed book (AgriParam alone) | B RAG, raw answer | C RAG + numeric verifier (final answer)
"""
import json
import re
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
RES = ROOT / "eval" / "results"
RES.mkdir(exist_ok=True)


def load_cases(name):
    return [json.loads(l) for l in open(ROOT / "eval" / name, encoding="utf-8")]


def facts_ok(case, text):
    return bool(text) and all(re.search(f, text, re.I) for f in case["required_facts"])


def read_jsonl(path):
    return [json.loads(l) for l in open(path, encoding="utf-8")] if path.exists() else []


def append(path, row):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------ retrieval stage (CPU)
def retrieval():
    from farmadvocate import config, rules
    from farmadvocate.retrieve import Retriever
    ret = Retriever()

    def probe(c):
        q = c["question_en"]
        if rules.route(q):
            return {"pred": "out_of_scope", "score": None, "hit": None, "crop": None}
        crop, unsup = rules.detect_crop(q)
        if unsup:
            return {"pred": "unsupported_crop", "score": None, "hit": None, "crop": None}
        hits = ret.search(q, crop=crop)
        score = hits[0][0] if hits else 0.0
        hit = None
        if c["gold_page"] is not None:
            hit = any(h[1]["crop"] == c["crop"] and h[1]["page_start"] <= c["gold_page"] <= h[1]["page_end"] for h in hits)
        return {"pred": "retrieved", "score": round(score, 3), "hit": hit, "crop": crop}

    dev = [(c, probe(c)) for c in load_cases("dev_cases.jsonl")]
    pos = [p["score"] for c, p in dev if not c["should_refuse"] and p["score"] is not None]
    neg = [p["score"] for c, p in dev if c["should_refuse"] and p["score"] is not None]
    print("DEV answerable scores:", pos, "| DEV unanswerable (reached retrieval):", neg)
    for c, p in dev:
        print("  dev", c["id"], p)

    test = [(c, probe(c)) for c in load_cases("test_cases.jsonl")]
    ans = [(c, p) for c, p in test if not c["should_refuse"]]
    neg_t = [(c, p) for c, p in test if c["should_refuse"]]
    hit = sum(1 for _, p in ans if p["hit"])
    print(f"\nHit@3 (English meaning, answerable): {hit}/{len(ans)}")
    for c, p in ans:
        if not p["hit"]:
            print("  MISS", c["id"], p)
    print("min/median score among answerable:", min(p["score"] for _, p in ans), st.median(p["score"] for _, p in ans))
    print("refusal routing:", {c["id"]: p["pred"] for c, p in neg_t})
    json.dump({"dev": [{"id": c["id"], **p} for c, p in dev], "test": [{"id": c["id"], **p} for c, p in test]},
              open(RES / "retrieval.json", "w"), indent=1)


# ------------------------------------------------------------------ full stage (GPU)
def full():
    from farmadvocate import pipeline
    pipeline.load()
    cases = load_cases("test_cases.jsonl")
    for name, mode, subset in (("rag.jsonl", "rag", cases),
                               ("closed_book.jsonl", "closed_book", [c for c in cases if c["lang"] == "en" and not c["should_refuse"]])):
        path = RES / name
        done = {r["id"] for r in read_jsonl(path)}
        for c in subset:
            if c["id"] in done:
                continue
            out = pipeline.answer(c["question"], c["lang"], mode=mode)
            append(path, {"id": c["id"], "mode": mode, **out})
            print(name, c["id"], out["status"], out["seconds"], flush=True)


# ------------------------------------------------------------------ space stage (evaluate the deployed app)
def space():
    """Run the evaluation against the deployed Space API. Resumable if the GPU quota runs out."""
    from gradio_client import Client
    from huggingface_hub import get_token
    client = Client("DaMCSS/FarmAdvocate", token=get_token(), verbose=False)
    label = {"en": "English", "hi": "हिन्दी (Hindi)", "kn": "ಕನ್ನಡ (Kannada)"}
    cases = load_cases("test_cases.jsonl")
    plans = (("rag.jsonl", "/ask", cases),
             ("closed_book.jsonl", "/closed_book", [c for c in cases if c["lang"] == "en" and not c["should_refuse"]]))
    for name, api, subset in plans:
        path = RES / name
        done = {r["id"] for r in read_jsonl(path)}
        for c in subset:
            if c["id"] in done:
                continue
            try:
                res = client.predict(c["question"], label[c["lang"]], api_name=api)
            except Exception as e:  # most likely the daily ZeroGPU quota
                print("STOPPED at", name, c["id"], type(e).__name__, str(e)[:300], flush=True)
                return
            out = res[4] if isinstance(res, (list, tuple)) else res
            append(path, {"id": c["id"], "mode": "rag" if api == "/ask" else "closed_book", **out})
            print(name, c["id"], out["status"], out["seconds"], flush=True)
    print("SPACE EVAL COMPLETE")


# ------------------------------------------------------------------ metrics stage
def pct(a, b):
    return f"{a}/{b} ({100 * a / b:.0f}%)" if b else "n/a"


def metrics():
    cases = {c["id"]: c for c in load_cases("test_cases.jsonl")}
    rag = {r["id"]: r for r in read_jsonl(RES / "rag.jsonl")}
    cb = {r["id"]: r for r in read_jsonl(RES / "closed_book.jsonl")}
    labels = json.load(open(RES / "labels.json")) if (RES / "labels.json").exists() else {}
    ret = {r["id"]: r for r in json.load(open(RES / "retrieval.json"))["test"]} if (RES / "retrieval.json").exists() else {}
    lines = [f"Cases run: {len(rag)}/50 (RAG), {len(cb)}/24 (closed book)\n"]

    en = [c for c in cases.values() if c["lang"] == "en" and not c["should_refuse"]]
    a = sum(facts_ok(c, cb[c["id"]]["raw_answer_en"]) for c in en if c["id"] in cb)
    b = sum(facts_ok(c, rag[c["id"]]["raw_answer_en"]) for c in en if c["id"] in rag)
    cc = sum(facts_ok(c, rag[c["id"]]["answer_en"]) for c in en if c["id"] in rag)
    lines += ["| Configuration (24 English questions) | Factual correctness (regex) |", "|---|---|",
              f"| A. AgriParam alone | {pct(a, len([c for c in en if c['id'] in cb]))} |",
              f"| B. RAG, raw answer | {pct(b, len([c for c in en if c['id'] in rag]))} |",
              f"| C. RAG + verifier (final answer) | {pct(cc, len([c for c in en if c['id'] in rag]))} |\n"]

    lines += ["| Language | Factual correctness, final English answer, paired subset |", "|---|---|"]
    for lang in ("en", "hi", "kn"):
        sub = [c for c in cases.values() if c["lang"] == lang and not c["should_refuse"] and c["id"] in rag]
        if lang == "en":  # restrict to the questions that have hi/kn pairs
            paired = {c["pair_id"] for c in cases.values() if c["pair_id"]}
            sub = [c for c in sub if c["id"] in paired]
        lines.append(f"| {lang} | {pct(sum(facts_ok(c, rag[c['id']]['answer_en']) for c in sub), len(sub))} |")
    lines.append("")

    gen = [(c, rag[c["id"]]) for c in cases.values() if not c["should_refuse"] and c["id"] in rag and rag[c["id"]]["raw_answer_en"]]
    lines.append(f"Fallback rate (verifier replaced answer): {pct(sum(1 for _, r in gen if r['status'] == 'unverified'), len(gen))}")
    lab = [(c, labels.get(c["id"])) for c, r in gen if r["status"] == "verified" and labels.get(c["id"])]
    sup = sum(1 for _, l in lab if l == "supported")
    lines.append(f"Groundedness on generated (non-fallback) answers, labelled by Claude: {pct(sup, len(lab))} fully supported")
    lines.append(f"Verifier pass rate on generated answers: {pct(sum(1 for _, r in gen if r['verifier_ok']), len(gen))}")

    ans = [c for c in cases.values() if not c["should_refuse"] and c["id"] in rag]
    neg = [c for c in cases.values() if c["should_refuse"] and c["id"] in rag]
    refused = lambda r: r["status"] in ("out_of_scope", "unsupported_crop", "not_found")
    lines.append(f"Refusal accuracy (should refuse): {pct(sum(refused(rag[c['id']]) for c in neg), len(neg))}")
    lines.append(f"False refusals (answerable refused): {pct(sum(refused(rag[c['id']]) for c in ans), len(ans))}")
    if ret:
        hits = [ret[c["id"]]["hit"] for c in ans if ret.get(c["id"]) and ret[c["id"]]["hit"] is not None]
        lines.append(f"Retrieval Hit@3 (English meaning): {pct(sum(hits), len(hits))}")
    nl = [rag[c["id"]] for c in ans if c["lang"] != "en"]
    lines.append(f"Numbers preserved through translation (hi/kn answers): {pct(sum(1 for r in nl if r['numbers_preserved']), len(nl))}")
    secs = [r["seconds"] for r in rag.values()]
    if secs:
        lines.append(f"Median seconds per query: {st.median(secs):.1f}")
    out = "\n".join(lines)
    (RES / "summary.md").write_text(out, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    {"retrieval": retrieval, "full": full, "space": space, "metrics": metrics}[sys.argv[1]]()
