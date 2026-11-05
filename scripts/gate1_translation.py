"""Gate 1a: validate IndicTrans2 translation in all directions before any app code.

Usage: python gate1_translation.py <output.json> [revision_mode]
revision_mode: "pr" (maintainer fix branches, default) or "main".
"""
import json
import re
import sys
import time
import traceback

import torch
import transformers
from huggingface_hub import HfApi, whoami
from IndicTransToolkit import IndicProcessor
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

OUT = sys.argv[1]
MODE = sys.argv[2] if len(sys.argv) > 2 else "pr"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

MODELS = {
    "en_indic": ("ai4bharat/indictrans2-en-indic-dist-200M", "refs/pr/15"),
    "indic_en": ("ai4bharat/indictrans2-indic-en-dist-200M", "refs/pr/4"),
}
HI, KN, EN = "hin_Deva", "kan_Knda", "eng_Latn"

QUERIES = {
    HI: ["धान की फसल में कितना यूरिया डालना चाहिए?", "गेहूं की सिंचाई कब करनी चाहिए?"],
    KN: ["ಭತ್ತದ ಬೆಳೆಗೆ ಎಷ್ಟು ಯೂರಿಯಾ ಹಾಕಬೇಕು?", "ರಾಗಿ ಬೆಳೆಗೆ ಎಷ್ಟು ಬೀಜ ಬೇಕು?"],
}
ANSWERS = [
    "Apply 10 kg N/ha (22 kg urea) at the time of first puddling.",
    "Apply NPK @ 100 : 50 : 50 kg / ha as a basal dose.",
    "Maintain 2.5 cm depth of water after transplanting.",
    "Use a seed rate of 60 kg for short duration varieties and 20 kg for hybrids.",
]

report = {"mode": MODE, "device": DEVICE, "torch": torch.__version__,
          "transformers": transformers.__version__, "python": sys.version.split()[0],
          "user": whoami()["name"], "stage": "start", "tests": {}}


def save():
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)


def digits(text):
    # Indic digits are normalised to ASCII by int().
    return sorted(str(int(d)) for d in re.findall(r"\d+", text))


def load(name):
    repo, pr = MODELS[name]
    rev = pr if MODE == "pr" else "main"
    tok = AutoTokenizer.from_pretrained(repo, trust_remote_code=True, revision=rev)
    model = AutoModelForSeq2SeqLM.from_pretrained(
        repo, trust_remote_code=True, revision=rev).to(DEVICE).eval()
    return tok, model


def translate(tok, model, ip, text, src, tgt):
    # One sentence at a time: the PR notes batched beam output issues on 4.53.2.
    batch = ip.preprocess_batch([text], src_lang=src, tgt_lang=tgt)
    enc = tok(batch, truncation=True, padding="longest", max_length=256,
              return_tensors="pt", return_attention_mask=True).to(DEVICE)
    with torch.inference_mode():
        out = model.generate(**enc, use_cache=True, min_length=0, max_length=256,
                             num_beams=3, num_return_sequences=1)
    dec = tok.batch_decode(out, skip_special_tokens=True, clean_up_tokenization_spaces=True)
    return ip.postprocess_batch(dec, lang=tgt)[0]


try:
    api = HfApi()
    report["pr_commits"] = {}
    for name, (repo, pr) in MODELS.items():
        refs = api.list_repo_refs(repo, include_pull_requests=True)
        report["pr_commits"][name] = {
            "main": next(b.target_commit for b in refs.branches if b.name == "main"),
            "pr": next((p.target_commit for p in refs.pull_requests if p.ref == pr), None),
        }
    save()

    ip = IndicProcessor(inference=True)
    report["stage"] = "load_en_indic"; save()
    t = time.time(); en_tok, en_model = load("en_indic")
    report["load_en_indic_s"] = round(time.time() - t, 1)
    report["stage"] = "load_indic_en"; save()
    t = time.time(); in_tok, in_model = load("indic_en")
    report["load_indic_en_s"] = round(time.time() - t, 1)

    report["stage"] = "directions"; save()
    for lang, qs in QUERIES.items():
        report["tests"][f"{lang}_to_en"] = []
        for q in qs:
            t = time.time()
            res = translate(in_tok, in_model, ip, q, lang, EN)
            report["tests"][f"{lang}_to_en"].append(
                {"in": q, "out": res, "s": round(time.time() - t, 2)})
            save()

    for lang in (HI, KN):
        key = f"en_to_{lang}_roundtrip"
        report["tests"][key] = []
        for a in ANSWERS:
            t = time.time()
            fwd = translate(en_tok, en_model, ip, a, EN, lang)
            back = translate(in_tok, in_model, ip, fwd, lang, EN)
            report["tests"][key].append({
                "in": a, "translated": fwd, "back": back,
                "digits_kept_in_translation": digits(a) == digits(fwd),
                "digits_kept_round_trip": digits(a) == digits(back),
                "s": round(time.time() - t, 2)})
            save()

    report["stage"] = "repeat"; save()
    t = time.time()
    results = [translate(en_tok, en_model, ip, ANSWERS[0], EN, KN) for _ in range(20)]
    report["tests"]["repeat_20"] = {"ok": True, "distinct_outputs": len(set(results)),
                                    "total_s": round(time.time() - t, 1)}
    report["stage"] = "passed"
except Exception:
    report["error"] = traceback.format_exc()
    report["stage"] = "failed:" + report["stage"]
save()
print(report["stage"])
