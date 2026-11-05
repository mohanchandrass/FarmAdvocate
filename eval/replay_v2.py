"""Replay the logged v1 answers through the v2 failed-answer detector (no GPU, no quota).

The pipeline is deterministic (greedy decoding), and v2 only changes what happens AFTER generation, so
v2's output equals v1's except for answers the detector flags. Flagged answers are replaced exactly as the
live pipeline now does: the top source passage (or the not-found message). English text only; the
translation of the fallback message is not simulated for hi/kn.
Run: python eval/replay_v2.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from farmadvocate import config, rules  # noqa: E402

rag = [json.loads(l) for l in open(ROOT / "eval" / "results" / "rag.jsonl", encoding="utf-8")]
cases = {json.loads(l)["id"]: json.loads(l) for l in open(ROOT / "eval" / "test_cases.jsonl", encoding="utf-8")}
out, changed = [], []
for r in rag:
    r2 = dict(r)
    raw = r.get("raw_answer_en")
    if raw:
        fail = rules.answer_failed(raw, r["question_en"])
        r2["failed_reason"] = fail
        if fail == "declined" and not any(ch.isdigit() for ch in raw):
            r2.update(status="not_found", answer_en=config.MESSAGES["not_found"])
            changed.append(r["id"])
        elif fail:
            r2.update(status="unverified", answer_en=config.MESSAGES["unverified"] + " " + r["sources"][0]["text"])
            changed.append(r["id"])
    out.append(r2)
with open(ROOT / "eval" / "results" / "rag_v2.jsonl", "w", encoding="utf-8") as f:
    for r in out:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print("flagged by the detector:", changed)
for i in changed:
    c = cases[i]
    old = next(r for r in rag if r["id"] == i)
    new = next(r for r in out if r["id"] == i)
    ok = lambda t: bool(c["required_facts"]) and all(re.search(f, t, re.I) for f in c["required_facts"])
    print(f"{i}: reason={new['failed_reason']} | v1 regex={ok(old['answer_en'])} -> v2 regex={ok(new['answer_en'])}")
    print("   v1:", old["answer_en"][:140].replace("\n", " "))
    print("   v2:", new["answer_en"][:200].replace("\n", " "))
