"""Reviewer labels for the 50-case run, written by Claude after reading every answer and its retrieved passages.

correct:  yes | partial | no     (does the final English answer state the guide's fact correctly and completely?)
grounded: supported | partial | unsupported | no_answer  (is every claim supported by the retrieved passages?)
Groundedness is independent of correctness: an answer can be faithful to a passage that is the wrong passage.
NOT checked by a human. Run: python eval/make_labels.py
"""
import json
from pathlib import Path

Y, P, N = "yes", "partial", "no"
S, SP, U, NA = "supported", "partial", "unsupported", "no_answer"
RAG = {
    "en-R1": (N, U, "Source says 2 kg per ACRE (SRI hybrid seed); answer changed it to per hectare. Gold passage (p17) not retrieved."),
    "en-R2": (N, SP, "1.5 cm is in the passage but is the day-5 depth; gold is 2.5 cm. '4 leaves old' is invented."),
    "en-R3": (P, S, "22 kg urea is right; omits the 10 kg N/ha."),
    "en-R4": (N, S, "Faithful to the hybrid rice SEED PRODUCTION passage (150:60:60); gold is commercial hybrid rice (175:60:60). Wrong passage retrieved."),
    "en-R5": (Y, S, "20x10, 50 hills/m2."),
    "en-R6": (N, U, "12-15 kg/ha is the TWO-seedling rate on the adjacent line; single-seedling rate is 5-7."),
    "en-G1": (Y, S, ""),
    "en-G2": (Y, S, "40:20:20 stated as N, P2O5, K2O (regex pattern too strict)."),
    "en-G3": (N, NA, "Echoed the question; no answer. Contains no number, so the verifier cannot flag it."),
    "en-G4": (N, U, "Gave plant spacing (7.5-10 cm) as row spacing; gold is 22.5-30 cm."),
    "en-M1": (Y, S, ""),
    "en-M2": (Y, S, ""),
    "en-M3": (N, S, "Faithful to the hybrid maize SEED PRODUCTION passage (150:75:75); gold is 250:75:75. Wrong passage retrieved."),
    "en-M4": (Y, S, ""),
    "en-M5": (Y, S, ""),
    "en-W1": (Y, S, ""),
    "en-W2": (Y, S, "80:40:40 stated as N, P2O5, K2O (regex pattern too strict)."),
    "en-W3": (Y, S, ""),
    "en-W4": (Y, S, ""),
    "en-D1": (Y, S, ""),
    "en-D2": (P, S, "Omits the 50% flowering stage."),
    "en-D3": (Y, S, ""),
    "en-N1": (Y, S, "125 kg/ha is in the guide at p190 (p185 says 120)."),
    "en-N2": (P, SP, "States 400 kg/ha but opens with 'the passage does not provide specific quantities', which is false."),
    "hi-R1": (N, S, "Faithful to the SRI passage (2 kg per acre); wrong passage for the question."),
    "hi-R3": (Y, S, ""),
    "hi-R4": (N, S, "Same hybrid seed production passage as en-R4."),
    "hi-G2": (Y, S, ""),
    "hi-M3": (N, S, "Same hybrid seed production passage as en-M3; also drops the P and K values."),
    "hi-W1": (Y, S, ""),
    "hi-D1": (N, NA, "False refusal: top similarity 0.667 is just under the 0.68 threshold."),
    "hi-N2": (Y, S, "Crop not detected ('peanuts' plural), retrieval still found the right passage."),
    "kn-R2": (N, U, "Combined the 1.5 cm depth with an unrelated '18 to 24 hours'; gold is 2.5 cm."),
    "kn-R5": (P, SP, "Contains 20x10 but garbled as '20x10^6'."),
    "kn-G1": (Y, S, ""),
    "kn-M1": (Y, S, ""),
    "kn-W2": (Y, S, "80:40:40 (regex pattern too strict)."),
    "kn-W4": (Y, S, ""),
    "kn-D2": (N, S, "Query mistranslated: tur (redgram) became 'skin', so no crop was detected and wheat stages were returned."),
    "kn-N1": (Y, S, "Mixes the p185 and p190 seed rates, both in the guide."),
}
# Closed-book baseline (AgriParam alone), reviewed against the guide's value.
CB = {
    "en-R1": (N, "15 kg per acre"), "en-R2": (P, "2-3 cm range includes 2.5, but invented context"),
    "en-R3": (N, ""), "en-R4": (N, ""), "en-R5": (N, ""), "en-R6": (N, ""), "en-G1": (N, "80-100 kg/ha"),
    "en-G2": (N, ""), "en-G3": (Y, "late June to early July"), "en-G4": (N, ""), "en-M1": (Y, "20 kg/ha"),
    "en-M2": (P, "range 20-30 cm includes 25"), "en-M3": (N, ""), "en-M4": (N, ""), "en-M5": (N, ""),
    "en-W1": (P, "mid-October to mid-November"), "en-W2": (N, ""), "en-W3": (P, "20-25 cm, 3-5 cm"),
    "en-W4": (Y, "4 to 6"), "en-D1": (N, ""), "en-D2": (P, "flowering and pod formation only"),
    "en-D3": (N, "June 20 to July 10; guide says July-August (the regex wrongly matched 'July')"),
    "en-N1": (N, "100 kg/ha"), "en-N2": (N, "200-300 kg/ha"),
}
out = {"rag": {k: {"correct": c, "grounded": g, "note": n} for k, (c, g, n) in RAG.items()},
       "closed_book": {k: {"correct": c, "note": n} for k, (c, n) in CB.items()}}
assert len(RAG) == 40 and len(CB) == 24
(Path(__file__).parent / "results" / "labels.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("labels written:", len(RAG), "rag,", len(CB), "closed-book")
