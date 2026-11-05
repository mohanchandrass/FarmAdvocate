"""Generate eval/test_cases.jsonl (50) and eval/dev_cases.jsonl (6).

Questions and gold facts were written by Claude from the TNAU Crop Production Guide 2020
(gold_page = printed page). Hindi and Kannada questions are drafted directly, not machine-translated,
and have NOT been checked by a native speaker. Run: python eval/build_cases.py
"""
import json
from pathlib import Path

OUT = Path(__file__).parent

# id, crop, type, English question, required_facts (regexes, all must match), gold printed page
EN = [
    ("R1", "Rice", "seed_rate", "What is the seed rate for hybrid rice in the nursery?", [r"20\s*kg"], 17),
    ("R2", "Rice", "irrigation", "What depth of water should be maintained in the rice nursery after the seedlings have grown?", [r"2\.5\s*cm"], 18),
    ("R3", "Rice", "fertilizer", "How much nitrogen and urea should I apply when incorporating stubble in rice?", [r"10\s*kg\s*N", r"22\s*kg"], 21),
    ("R4", "Rice", "fertilizer", "What is the recommended nitrogen, phosphorus and potash for hybrid rice?", [r"175", r"\b60\b"], 21),
    ("R5", "Rice", "spacing", "What spacing should I use for medium duration rice in medium or low fertility soil?", [r"20\s*(?:cm)?\s*[x×]\s*10"], 20),
    ("R6", "Rice", "seed_rate", "What is the seed rate for the System of Rice Intensification with a single seedling per hill?", [r"5\s*(?:-|–|to)\s*7"], 28),
    ("G1", "Ragi", "seed_rate", "What is the recommended seed rate for ragi?", [r"10\s*kg"], 99),
    ("G2", "Ragi", "fertilizer", "What are the recommended doses of nitrogen, phosphorus and potash for ragi?", [r"40\D{1,6}20\D{1,6}20"], 100),
    ("G3", "Ragi", "season", "When should rainfed ragi be sown in Tamil Nadu?", [r"June", r"July"], 99),
    ("G4", "Ragi", "spacing", "What row spacing is used when sowing ragi with a seed drill?", [r"22\.5"], 99),
    ("M1", "Maize", "seed_rate", "What is the seed rate for maize variety CO 1?", [r"20\s*kg"], 107),
    ("M2", "Maize", "spacing", "What spacing should be adopted for maize?", [r"25\s*cm", r"60\s*cm"], 107),
    ("M3", "Maize", "fertilizer", "What is the blanket NPK recommendation for hybrid maize?", [r"250\D{1,6}75\D{1,6}75"], 105),
    ("M4", "Maize", "irrigation", "Which period is most critical for moisture in maize?", [r"45", r"65"], 109),
    ("M5", "Maize", "fertilizer", "How much farmyard manure should be spread for irrigated maize?", [r"12\.5\s*t"], 104),
    ("W1", "Wheat", "season", "What is the ideal sowing time for wheat?", [r"15(?:th)?\s*October"], 122),
    ("W2", "Wheat", "fertilizer", "What blanket NPK should I apply to wheat if there is no soil test?", [r"80\D{1,6}40\D{1,6}40"], 123),
    ("W3", "Wheat", "spacing", "How far apart should wheat rows be, and how deep should the seed be sown?", [r"20\s*cm", r"5\s*cm"], 124),
    ("W4", "Wheat", "irrigation", "How many irrigations does wheat need?", [r"\b5\b|five|\b4\b"], 124),
    ("D1", "Redgram", "fertilizer", "What fertilizer should be applied basally to rainfed redgram?", [r"12\.5\s*kg\s*N"], 127),
    ("D2", "Redgram", "irrigation", "At which stages should redgram be irrigated?", [r"bud initiation"], 128),
    ("D3", "Redgram", "season", "When should long duration redgram varieties be sown?", [r"July"], 128),
    ("N1", "Groundnut", "seed_rate", "What is the seed rate for groundnut?", [r"120\s*kg"], 185),
    ("N2", "Groundnut", "fertilizer", "How much gypsum should be applied to groundnut?", [r"400\s*kg"], 186),
]

HI = {  # 8 paired Hindi questions
    "R1": "हाइब्रिड धान के लिए नर्सरी में बीज दर कितनी होनी चाहिए?",
    "R3": "धान में पिछली फसल के ठूंठ मिलाते समय कितना नाइट्रोजन और यूरिया डालना चाहिए?",
    "R4": "हाइब्रिड धान के लिए नाइट्रोजन, फास्फोरस और पोटाश की अनुशंसित मात्रा कितनी है?",
    "G2": "रागी के लिए नाइट्रोजन, फास्फोरस और पोटाश की अनुशंसित मात्रा क्या है?",
    "M3": "हाइब्रिड मक्का के लिए एनपीके की सामान्य अनुशंसित मात्रा क्या है?",
    "W1": "गेहूं की बुवाई का सही समय क्या है?",
    "D1": "बारानी अरहर में बुवाई के समय कौन सा उर्वरक डालना चाहिए?",
    "N2": "मूंगफली में जिप्सम कितना डालना चाहिए?",
}
KN = {  # 8 paired Kannada questions
    "R2": "ಭತ್ತದ ನರ್ಸರಿಯಲ್ಲಿ ಸಸಿಗಳು ಬೆಳೆದ ನಂತರ ಎಷ್ಟು ಆಳದ ನೀರನ್ನು ಕಾಪಾಡಬೇಕು?",
    "R5": "ಮಧ್ಯಮ ಅವಧಿಯ ಭತ್ತಕ್ಕೆ, ಮಧ್ಯಮ ಅಥವಾ ಕಡಿಮೆ ಫಲವತ್ತತೆಯ ಮಣ್ಣಿನಲ್ಲಿ ನಾಟಿ ಅಂತರ ಎಷ್ಟು ಇರಬೇಕು?",
    "G1": "ರಾಗಿಗೆ ಶಿಫಾರಸು ಮಾಡಿದ ಬೀಜದ ಪ್ರಮಾಣ ಎಷ್ಟು?",
    "M1": "ಮೆಕ್ಕೆಜೋಳದ CO 1 ತಳಿಗೆ ಬೀಜದ ಪ್ರಮಾಣ ಎಷ್ಟು?",
    "W2": "ಮಣ್ಣಿನ ಪರೀಕ್ಷೆ ಇಲ್ಲದಿದ್ದರೆ ಗೋಧಿಗೆ ಎನ್‌ಪಿಕೆ ಎಷ್ಟು ಹಾಕಬೇಕು?",
    "W4": "ಗೋಧಿ ಬೆಳೆಗೆ ಎಷ್ಟು ಬಾರಿ ನೀರು ಹಾಯಿಸಬೇಕು?",
    "D2": "ತೊಗರಿಗೆ ಯಾವ ಹಂತಗಳಲ್ಲಿ ನೀರು ಹಾಯಿಸಬೇಕು?",
    "N1": "ನೆಲಗಡಲೆಗೆ ಬೀಜದ ಪ್ರಮಾಣ ಎಷ್ಟು?",
}
# 10 should-refuse cases: (id, lang, question, English meaning, kind)
REFUSE = [
    ("X1", "en", "How do I control stem borer in rice?", "How do I control stem borer in rice?", "pest"),
    ("X2", "en", "What is today's mandi price of wheat?", "What is today's mandi price of wheat?", "off_topic"),
    ("X3", "en", "How much fertilizer does cotton need?", "How much fertilizer does cotton need?", "unsupported_crop"),
    ("X4", "en", "What is the irrigation schedule for sugarcane?", "What is the irrigation schedule for sugarcane?", "unsupported_crop"),
    ("X5", "en", "Who won the cricket match yesterday?", "Who won the cricket match yesterday?", "off_topic"),
    ("X6", "hi", "धान में तना छेदक कीट को कैसे नियंत्रित करें?", "How do I control stem borer in rice?", "pest"),
    ("X7", "hi", "टमाटर की फसल में कितना खाद डालना चाहिए?", "How much fertilizer should be applied to the tomato crop?", "unsupported_crop"),
    ("X8", "hi", "आज मौसम का पूर्वानुमान क्या है?", "What is the weather forecast today?", "off_topic"),
    ("X9", "kn", "ರಾಗಿಯಲ್ಲಿ ಎಲೆ ರೋಗವನ್ನು ಹೇಗೆ ನಿಯಂತ್ರಿಸುವುದು?", "How do I control leaf disease in ragi?", "pest"),
    ("X10", "kn", "ಕಬ್ಬಿಗೆ ಎಷ್ಟು ನೀರು ಬೇಕು?", "How much water does sugarcane need?", "unsupported_crop"),
]
# Dev cases: used only to set the retrieval refusal threshold. Never used for reporting.
DEV = [
    {"id": "dev1", "lang": "en", "question": "How much farmyard manure is applied to the rice nursery?", "question_en": "How much farmyard manure is applied to the rice nursery?", "crop": "Rice", "type": "fertilizer", "required_facts": [r"1\s*tonne"], "gold_page": 18, "should_refuse": False},
    {"id": "dev2", "lang": "en", "question": "What rate of Azospirillum is used to treat ragi seed?", "question_en": "What rate of Azospirillum is used to treat ragi seed?", "crop": "Ragi", "type": "fertilizer", "required_facts": [r"25\s*g"], "gold_page": 100, "should_refuse": False},
    {"id": "dev3", "lang": "en", "question": "How much zinc sulphate should be applied to wheat in zinc deficient soils?", "question_en": "How much zinc sulphate should be applied to wheat in zinc deficient soils?", "crop": "Wheat", "type": "fertilizer", "required_facts": [r"37\.5"], "gold_page": 123, "should_refuse": False},
    {"id": "dev4", "lang": "en", "question": "When should the first irrigation be given to groundnut after sowing?", "question_en": "When should the first irrigation be given to groundnut after sowing?", "crop": "Groundnut", "type": "irrigation", "required_facts": [r"4\s*[-–to]+\s*5"], "gold_page": 191, "should_refuse": False},
    {"id": "dev5", "lang": "en", "question": "How do I grow orchids in my garden?", "question_en": "How do I grow orchids in my garden?", "crop": None, "type": "off_topic", "required_facts": [], "gold_page": None, "should_refuse": True},
    {"id": "dev6", "lang": "en", "question": "Which pesticide kills groundnut leaf miner?", "question_en": "Which pesticide kills groundnut leaf miner?", "crop": "Groundnut", "type": "pest", "required_facts": [], "gold_page": None, "should_refuse": True},
]


def case(cid, lang, q, q_en, crop, typ, facts, page, refuse, pair=None, kind=None):
    return {"id": cid, "lang": lang, "question": q, "question_en": q_en, "crop": crop, "type": typ,
            "required_facts": facts, "gold_page": page, "should_refuse": refuse,
            "pair_id": pair, "refusal_kind": kind}


cases = []
for cid, crop, typ, q, facts, page in EN:
    cases.append(case(f"en-{cid}", "en", q, q, crop, typ, facts, page, False))
by_id = {c[0]: c for c in EN}
for lang, qs in (("hi", HI), ("kn", KN)):
    for cid, q in qs.items():
        _, crop, typ, q_en, facts, page = by_id[cid]
        cases.append(case(f"{lang}-{cid}", lang, q, q_en, crop, typ, facts, page, False, pair=f"en-{cid}"))
for cid, lang, q, q_en, kind in REFUSE:
    cases.append(case(f"{lang}-{cid}", lang, q, q_en, None, kind, [], None, True, kind=kind))

assert len(cases) == 50, len(cases)
assert sum(c["should_refuse"] for c in cases) == 10
with open(OUT / "test_cases.jsonl", "w", encoding="utf-8") as f:
    for c in cases:
        f.write(json.dumps(c, ensure_ascii=False) + "\n")
with open(OUT / "dev_cases.jsonl", "w", encoding="utf-8") as f:
    for c in DEV:
        f.write(json.dumps(dict(c, pair_id=None, refusal_kind=None), ensure_ascii=False) + "\n")
print(f"wrote {len(cases)} test cases and {len(DEV)} dev cases")
