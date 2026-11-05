"""IndicTrans2 translation (en <-> hi/kn), one sentence at a time."""
import re

import torch
from IndicTransToolkit import IndicProcessor
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from . import config

_SENT = re.compile(r"(?<=[.!?।])\s+")


def digits(text):
    """Sorted list of numbers in text; Indic digits are normalised to ASCII by int()."""
    return sorted(str(int(d)) for d in re.findall(r"\d+", text))


def _tighten(text):
    # IndicProcessor masks ratios such as '100 : 50 : 50' as placeholders, and the Kannada model
    # then drops the numbers (verified at Gate 1). Spelling the ratio out keeps every number.
    return re.sub(r"(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)", r"\1, \2 and \3", text)


class Translator:
    def __init__(self, device):
        self.device = device
        self.ip = IndicProcessor(inference=True)
        self.models = {}
        for key, (repo, rev) in config.INDICTRANS.items():
            tok = AutoTokenizer.from_pretrained(repo, trust_remote_code=True, revision=rev)
            model = AutoModelForSeq2SeqLM.from_pretrained(
                repo, trust_remote_code=True, revision=rev).to(device).eval()
            self.models[key] = (tok, model)

    def _one(self, key, text, src, tgt):
        tok, model = self.models[key]
        batch = self.ip.preprocess_batch([text], src_lang=src, tgt_lang=tgt)
        enc = tok(batch, truncation=True, padding="longest", max_length=256,
                  return_tensors="pt", return_attention_mask=True).to(self.device)
        with torch.inference_mode():
            out = model.generate(**enc, use_cache=True, min_length=0, max_length=256,
                                 num_beams=3, num_return_sequences=1)
        dec = tok.batch_decode(out, skip_special_tokens=True, clean_up_tokenization_spaces=True)
        return self.ip.postprocess_batch(dec, lang=tgt)[0]

    def _many(self, key, text, src, tgt):
        parts = [p for p in _SENT.split(text.strip()) if p.strip()]
        return " ".join(self._one(key, p, src, tgt) for p in parts)

    def to_en(self, text, lang):
        if lang == "en":
            return text
        return self._many("indic_en", text, config.IT2_TAG[lang], config.IT2_TAG["en"])

    def from_en(self, text, lang):
        """Return (translation, numbers_preserved). Callers must show English if not preserved."""
        if lang == "en":
            return text, True
        out = self._many("en_indic", _tighten(text), config.IT2_TAG["en"], config.IT2_TAG[lang])
        ok = digits(text) == digits(out) and "<ID" not in out and "ID1" not in out.replace(" ", "")
        return out, ok
