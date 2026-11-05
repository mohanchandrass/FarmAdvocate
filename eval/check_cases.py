"""Verify every answerable gold fact really appears in a chunk covering the gold page."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
chunks = [json.loads(l) for l in open(ROOT / "data" / "chunks.jsonl", encoding="utf-8")]
bad = 0
for name in ("test_cases.jsonl", "dev_cases.jsonl"):
    for line in open(ROOT / "eval" / name, encoding="utf-8"):
        c = json.loads(line)
        if c["should_refuse"]:
            continue
        pool = [k for k in chunks if k["crop"] == c["crop"] and k["page_start"] <= c["gold_page"] <= k["page_end"]]
        text = " ".join(k["text"] for k in pool)
        miss = [f for f in c["required_facts"] if not re.search(f, text, re.I)]
        if not pool or miss:
            bad += 1
            print(f"FAIL {c['id']} page {c['gold_page']}: chunks={len(pool)} missing={miss}")
print("gold check:", "all facts found on gold pages" if not bad else f"{bad} problem(s)")
sys.exit(1 if bad else 0)
