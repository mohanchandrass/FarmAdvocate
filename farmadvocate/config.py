"""Central configuration: models, revisions, thresholds, languages, crop vocabulary."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHUNKS_PATH = ROOT / "data" / "chunks.jsonl"

# Models named in the assignment brief. IndicTrans2 is pinned to the commits behind the
# maintainers' transformers>=4.48 compatibility PRs (en-indic refs/pr/15, indic-en refs/pr/4);
# both loaded and translated correctly on transformers 4.53.1 at Gate 1.
AGRIPARAM = "bharatgenai/AgriParam"
AGRIPARAM_REV = os.environ.get("AGRIPARAM_REV", "main")  # pinned to a commit after Gate 1b
INDICTRANS = {
    "en_indic": ("ai4bharat/indictrans2-en-indic-dist-200M",
                 os.environ.get("IT2_EN_INDIC_REV", "bf4b89ee717b362d6fa1b9373778f94a99109568")),
    "indic_en": ("ai4bharat/indictrans2-indic-en-dist-200M",
                 os.environ.get("IT2_INDIC_EN_REV", "af1fe3d7d04e6327f9ae186b48a75cd6c0450aa8")),
}
EMBEDDER = "BAAI/bge-small-en-v1.5"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

# UI label -> (code, IndicTrans2 tag)
LANGS = {"English": "en", "हिन्दी (Hindi)": "hi", "ಕನ್ನಡ (Kannada)": "kn"}
IT2_TAG = {"en": "eng_Latn", "hi": "hin_Deva", "kn": "kan_Knda"}

TOP_K = 3
MAX_PROMPT_TOKENS = 1700   # AgriParam context is 2048; leave room for the answer
MAX_NEW_TOKENS = 200
# Set from the 6 dev cases only: answerable queries scored >= 0.731, an off-topic query scored 0.64.
SCORE_THRESHOLD = float(os.environ.get("SCORE_THRESHOLD", "0.68"))

CROP_ALIASES = {
    "Rice": ["rice", "paddy"],
    # IndicTrans2 often renders ragi as plain 'millet'; the guide section we index covers only finger millet.
    "Ragi": ["ragi", "finger millet", "nachni", "millet", "millets"],
    "Maize": ["maize", "corn", "makka"],
    "Wheat": ["wheat", "gehun"],
    "Redgram": ["redgram", "red gram", "pigeon pea", "pigeonpea", "arhar", "tur", "toor"],
    "Groundnut": ["groundnut", "ground nut", "peanut", "moongphali"],
}
# Checked before CROP_ALIASES so that e.g. 'pearl millet' is not mistaken for ragi via 'millet'.
UNSUPPORTED_OVERRIDE = ["pearl millet", "foxtail millet", "little millet", "kodo millet", "barnyard millet",
                        "proso millet", "bajra", "cumbu", "sorghum", "jowar"]
# Crops the guide covers but this build does not index, plus common crops it does not cover.
OUT_OF_CORPUS_CROPS = [
    "cotton", "sugarcane", "tomato", "onion", "potato", "banana", "mango", "coconut", "tea",
    "coffee", "rubber", "sorghum", "jowar", "bajra", "cumbu", "pearl millet", "blackgram",
    "black gram", "greengram", "green gram", "cowpea", "sesame", "castor", "sunflower",
    "soybean", "soya", "chilli", "turmeric", "jute", "barley", "mustard", "gram", "chickpea",
]
PEST_TERMS = ["pest", "pests", "insect", "insects", "insecticide", "pesticide", "fungicide",
              "fungus", "disease", "diseases", "weevil", "borer", "aphid", "aphids", "blight",
              "herbicide", "weedicide", "worm", "caterpillar", "mite", "mites"]
OFF_TOPIC_TERMS = ["price", "prices", "market", "mandi", "weather", "forecast", "subsidy", "loan",
                   "insurance", "cricket", "movie", "election", "recipe", "stock", "salary", "capital of"]

REFERRAL = ("please contact your local Krishi Vigyan Kendra (KVK) or call the Kisan Call Centre "
            "at 1800-180-1551.")
MESSAGES = {
    "out_of_scope": ("This assistant answers crop, irrigation and fertilizer questions from the TNAU guide. "
                     "For pests, diseases or other topics, " + REFERRAL),
    "unsupported_crop": ("The sources cover only rice, ragi, maize, wheat, redgram (pigeon pea) and groundnut. "
                         "For other crops, " + REFERRAL),
    "not_found": "I could not find this in my sources. For this question, " + REFERRAL,
    "unverified": "The exact answer could not be verified. Here is the source passage:",
}
NOTICE = ("Based on the TNAU Crop Production Guide 2020 (Tamil Nadu). "
          "Recommendations may differ in your region; confirm with your local KVK.")
