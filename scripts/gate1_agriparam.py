"""Gate 1b: validate AgriParam with real weights on a GPU: quality, peak memory, speed.

Usage: python gate1_agriparam.py <output.json>
"""
import json
import sys
import time
import traceback

import torch
import transformers
from huggingface_hub import HfApi
from transformers import AutoModelForCausalLM, AutoTokenizer

OUT = sys.argv[1]
REPO = "bharatgenai/AgriParam"
INSTRUCTION = ("Answer using only the context above. Include exact quantities and units. "
               "If the context does not contain the answer, say you do not know.")

# Passages quoted from TNAU Crop Production Guide: Agriculture 2020 (printed pp. 17, 18, 21, 79).
SEED = ("Crop: Rice | Section: Nursery management. Seed rate: 30 kg for long duration, "
        "40 kg for medium duration, 60 kg for short duration varieties and 20 kg for hybrids.")
WATER = ("Crop: Rice | Section: Nursery water management. Drain the water 18 to 24 hrs after sowing. "
         "Allow enough water to saturate the soil from 3rd to 5th day. From 5th day onwards, increase "
         "the water depth to 1.5 cm depending on the height of the seedlings. Thereafter maintain "
         "2.5 cm depth of water.")
NUTRIENT = ("Crop: Rice | Section: Nutrient Management. Stubble incorporation: Apply 10 kg N/ha "
            "(22 kg urea) at the time of first puddling while incorporating the stubbles of the "
            "previous crop to compensate immobilization of N by the stubbles.")
SORGHUM = ("Crop: Sorghum | Section: Seed production. Fertilizer requirement: as basal application "
           "NPK @ 100 : 50 : 50 kg / ha. Spacing: 45 x 10 cm.")

CASES = [
    {"id": "seed_hybrid", "context": [SEED, WATER], "q": "What is the seed rate for hybrid rice?", "expect": "20 kg"},
    {"id": "seed_short", "context": [SEED, NUTRIENT], "q": "How much seed is needed for short duration rice varieties?", "expect": "60 kg"},
    {"id": "water_depth", "context": [WATER, SEED], "q": "What water depth should be kept in the rice nursery after the seedlings grow?", "expect": "2.5 cm"},
    {"id": "urea_stubble", "context": [NUTRIENT, SEED], "q": "How much urea should I apply when incorporating stubble in rice?", "expect": "22 kg"},
    {"id": "npk_ratio", "context": [SORGHUM, SEED], "q": "What basal NPK dose is recommended for sorghum seed production?", "expect": "100"},
    {"id": "unanswerable", "context": [SEED, WATER], "q": "What is the market price of rice in Chennai?", "expect": "do not know"},
]
CLOSED_BOOK = "How much urea should I apply when incorporating stubble in rice?"

report = {"device": None, "stage": "start", "cases": []}


def save():
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)


def run(tok, model, prompt, max_new=200):
    enc = tok(prompt, return_tensors="pt", add_special_tokens=True)
    enc.pop("token_type_ids", None)
    enc = enc.to(model.device)
    n_in = enc["input_ids"].shape[1]
    torch.cuda.reset_peak_memory_stats()
    t = time.time()
    with torch.inference_mode():
        out = model.generate(**enc, max_new_tokens=max_new, do_sample=False,
                             repetition_penalty=1.1, use_cache=True,
                             eos_token_id=tok.eos_token_id, pad_token_id=tok.eos_token_id)
    secs = time.time() - t
    n_out = out.shape[1] - n_in
    text = tok.decode(out[0][n_in:], skip_special_tokens=True).split("<user>")[0].strip()
    return {"answer": text, "tokens_in": n_in, "tokens_out": int(n_out), "seconds": round(secs, 1),
            "tokens_per_s": round(n_out / secs, 1),
            "peak_gib": round(torch.cuda.max_memory_allocated() / 2**30, 2)}


try:
    report.update(device=torch.cuda.get_device_name(0), torch=torch.__version__,
                  transformers=transformers.__version__, python=sys.version.split()[0],
                  vram_total_gib=round(torch.cuda.get_device_properties(0).total_memory / 2**30, 1),
                  commit=HfApi().model_info(REPO).sha)
    report["stage"] = "load"; save()
    t = time.time()
    tok = AutoTokenizer.from_pretrained(REPO, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        REPO, trust_remote_code=True, torch_dtype=torch.bfloat16).to("cuda").eval()
    report["load_s"] = round(time.time() - t, 1)
    report["weights_gib"] = round(torch.cuda.memory_allocated() / 2**30, 2)

    report["stage"] = "context_qa"; save()
    for case in CASES:
        ctx = "\n\n".join(case["context"])
        res = run(tok, model, f"<context> {ctx} <user> {INSTRUCTION}\nQuestion: {case['q']} <assistant>")
        res.update(id=case["id"], q=case["q"], expect=case["expect"],
                   passed=case["expect"].lower() in res["answer"].lower())
        report["cases"].append(res); save()

    report["stage"] = "closed_book"; save()
    report["closed_book"] = run(tok, model, f"<user> {CLOSED_BOOK} <assistant>")

    # Worst case for memory: a prompt at the 1,700-token budget.
    report["stage"] = "full_budget"; save()
    filler, n = "", 0
    while n < 1640:
        filler += "\n\n" + SEED + "\n\n" + WATER + "\n\n" + NUTRIENT
        n = len(tok(filler)["input_ids"])
    report["full_budget"] = run(
        tok, model, f"<context> {filler} <user> {INSTRUCTION}\nQuestion: {CASES[0]['q']} <assistant>", max_new=200)

    passed = sum(c["passed"] for c in report["cases"])
    report["score"] = f"{passed}/{len(report['cases'])}"
    report["stage"] = "passed"
except Exception:
    report["error"] = traceback.format_exc()
    report["stage"] = "failed:" + report["stage"]
save()
print(json.dumps(report, ensure_ascii=False, indent=1))
