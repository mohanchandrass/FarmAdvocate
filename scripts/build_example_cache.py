"""Build data/example_cache.json from the saved evaluation outputs (eval/results/rag_v2.jsonl).

These are real outputs of this system for the 50 test questions, which include every example shown in the UI.
The app serves them without using GPU quota and labels them as saved answers.
Run: python scripts/build_example_cache.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from farmadvocate.cache import CACHE_PATH, cache_key  # noqa: E402

cases = {json.loads(l)["id"]: json.loads(l) for l in open(ROOT / "eval" / "test_cases.jsonl", encoding="utf-8")}
cache = {}
for line in open(ROOT / "eval" / "results" / "rag_v2.jsonl", encoding="utf-8"):
    r = json.loads(line)
    c = cases[r["id"]]
    r.pop("id", None)
    r.pop("mode", None)
    cache[cache_key(c["question"], c["lang"])] = r
CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
print(f"wrote {len(cache)} saved answers to {CACHE_PATH} ({CACHE_PATH.stat().st_size / 1e3:.0f} KB)")
