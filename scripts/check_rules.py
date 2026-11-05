"""Quick self-check of the pure-Python rules (run: python scripts/check_rules.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from farmadvocate import rules  # noqa: E402

CTX = ("Apply 10 kg N/ha (22 kg urea) at puddling. Basal NPK @ 100 : 50 : 50 kg / ha. "
       "Maintain 2.5 cm depth of water. Seed rate 20 kg for hybrids. Dose 1,000 g per ha. "
       "Hybrid rice 175 60 60")
checks = [
    ("route pest", rules.route("How do I control stem borer in rice?"), "out_of_scope"),
    ("route price", rules.route("What is the price of rice today?"), "out_of_scope"),
    ("route fert not refused", rules.route("How much nitrogen should I apply for poor growth of rice?"), None),
    ("route foliar spray ok", rules.route("When should I do a foliar spray of urea on groundnut?"), None),
    ("crop rice", rules.detect_crop("Seed rate for paddy?"), ("Rice", False)),
    ("crop tur not turn", rules.detect_crop("When do I turn the soil?"), (None, False)),
    ("crop tur", rules.detect_crop("Fertilizer for tur dal"), ("Redgram", False)),
    ("crop unsupported", rules.detect_crop("How much water does cotton need?"), (None, True)),
    ("crop corn vs acorn", rules.detect_crop("acorn planting"), (None, False)),
    ("verify ok unit variants", rules.verify_numbers("Apply 22 kg per hectare urea and keep 2.5 cm water", CTX)[0], True),
    ("verify ratio ok", rules.verify_numbers("Use NPK 100:50:50 kg/ha", CTX)[0], True),
    ("verify wrong number", rules.verify_numbers("Apply 45 kg/ha urea", CTX)[0], False),
    ("verify known limitation: right number, wrong nutrient passes", rules.verify_numbers("Apply 50 kg/ha urea", CTX)[0], True),
    ("verify wrong ratio", rules.verify_numbers("Use NPK 120:60:60", CTX)[0], False),
    ("verify thousands", rules.verify_numbers("Use 1000 g per ha", CTX)[0], True),
    ("verify range", rules.verify_numbers("Seed rate 20-30 kg", CTX)[0], False),
    ("verify same number wrong unit (125 kg vs 125 ml)", rules.verify_numbers("Seed rate is 125 kg/ha", "Treat seeds with 125 ml of Rhizobium. Use 120 kg/ha of kernels.")[0], False),
    ("verify % vs days", rules.verify_numbers("an increase of 15%", "Sow after 15 days. Use 120 kg/ha.")[0], False),
    ("verify glued unit in context", rules.verify_numbers("Seed rate is 20 kg per hectare", "Seedrate | 20kgperhectare")[0], True),
    ("verify table cell without unit", rules.verify_numbers("Apply 175 kg N per hectare", "Hybrid rice | 175 | 60 | 60")[0], True),
    ("verify cm vs kg", rules.verify_numbers("Keep 2.5 cm of water", "Apply 2.5 kg of urea")[0], False),
    ("ordinals", rules.normalize_ordinals("15th October to 1st week of November, 40th day"), "15th October to first week of November, 40th day"),
    ("verify bare numbers ignored", rules.verify_numbers("1. First step. Step 2 is next.", CTX)[0], True),
]
bad = [c for c in checks if c[1] != c[2]]
for name, got, want in checks:
    print(("PASS" if got == want else "FAIL"), name, "" if got == want else f"got={got!r} want={want!r}")
sys.exit(1 if bad else 0)
