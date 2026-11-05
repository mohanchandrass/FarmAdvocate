# Evaluation report

FarmAdvocate, evaluated on 50 test cases against the **deployed** Hugging Face Space (`DaMCSS/FarmAdvocate`, ZeroGPU),
via its public API. Generation is deterministic (greedy), so each number comes from a single run.

> **Disclosure.** The test questions, gold facts and every label in this report were produced by Claude, an AI model.
> Hindi and Kannada questions were drafted directly, not machine-translated, but **no native speaker or other human
> reviewed them or the labels**. Labels may share the system's blind spots. The raw outputs and every label with its
> reason are in `eval/results/` so each judgment can be checked.

## Test set
| Group | Cases |
|---|---|
| English, answerable | 24 (all six crops; fertilizer, irrigation, seed rate, spacing, season) |
| Hindi, answerable | 8 (each paired with an English case) |
| Kannada, answerable | 8 (each paired with an English case) |
| Should be refused | 10 (3 pest, 3 off-topic, 4 crops outside the corpus; in en, hi, kn) |

Six further dev cases were used only to set the retrieval threshold (0.68). Every gold fact was machine-checked to
appear on its gold page of the guide (`eval/check_cases.py`).

## Results

**RAG vs AgriParam alone** (same 24 English questions; "reviewed" = Claude's label after reading the answer):

| Configuration | Regex match | Reviewed: fully correct | Reviewed: correct or partial |
|---|---|---|---|
| A. AgriParam alone, no context | 4/24 (17%) | 3/24 (12%) | 8/24 (33%) |
| B. RAG, raw answer | 14/24 (58%) | 14/24 (58%) | 17/24 (71%) |
| C. RAG + numeric verifier | 14/24 (58%) | 14/24 (58%) | 17/24 (71%) |

* **Retrieval roughly quintupled fully-correct answers** (12% to 58%). The closed-book model invents plausible
  numbers ("80-100 kg/ha" ragi seed rate; guide: 10 kg/ha).
* **The verifier changed nothing**: all 39 generated answers passed it (0% fallback, 0 false alarms). It did not catch
  any of the 12 wrong generated answers, because each wrong number was present in the retrieved passages (see below).
  On this test set it neither helped nor hurt.
* The regex and the reviewer agree on 34/40 answerable cases (85%). Regex wrongly failed correct answers such as
  "40 kg N, 20 kg P2O5, 20 kg K2O" and wrongly passed a closed-book redgram date range (June 20 to July 10, whose
  text contained "July").

**Languages** (paired subset: the 16 English questions that have a Hindi or Kannada twin):

| Language | Fully correct | Correct or partial |
|---|---|---|
| English | 9/16 (56%) | 12/16 (75%) |
| Hindi | 4/8 (50%) | 4/8 (50%) |
| Kannada | 5/8 (62%) | 6/8 (75%) |

With 8 cases per language the differences are within noise; the data does not show Hindi or Kannada as clearly worse
than English. Numbers survived translation in 15 of 16 answers; the one exception was withheld by the guard.

**Other metrics**

| Metric | Result |
|---|---|
| Groundedness of 39 generated answers (Claude's labels) | 31 supported (79%), 3 partial, 4 unsupported, 1 no answer |
| Supported but incorrect (faithful to the wrong passage) | 6 of the 31 |
| Refusal accuracy (should-refuse cases) | 10/10 |
| False refusals (answerable but refused) | 1/40 |
| Retrieval Hit@3 (gold page in top 3, English meaning) | 34/40 (85%) |
| Median server-side time per query | 0.8 s (excludes queueing and Space wake-up) |

## Failure analysis
Of 40 answerable cases: 23 fully correct, 4 partial, 13 incorrect (including 1 false refusal).

| Failure type | Cases | Example and cause | Proposed fix |
|---|---|---|---|
| **Faithful to the wrong passage** (retrieval) | en-R4, hi-R4, en-M3, hi-M3, en-R1, hi-R1 (6) | "Hybrid rice" and "hybrid maize" questions retrieve the hybrid *seed production* passages (150:60:60, 150:75:75) instead of the commercial recommendation (175:60:60, 250:75:75). The answer is grounded, but answers a different question. | Down-rank chunks whose system is "Seed Production" unless the question mentions seeds or production; or add a cross-encoder re-ranker |
| **Misread within the right passage** | en-R6, en-G4, en-R2, kn-R2 (4) | SRI single-seedling rate (5-7 kg/ha) answered with the adjacent two-seedling rate (12-15); plant spacing given as row spacing; the nursery day-5 depth (1.5 cm) given instead of the final 2.5 cm. | Smaller chunks that keep each value with its label; a larger model |
| **Query mistranslation** | kn-D2 (1) | Kannada "tur" (redgram) was translated to "skin", so no crop was detected and wheat irrigation stages came back. | Show the translated question to the user; add a crop-name glossary to the translator input |
| **No answer given** | en-G3 (1) | The model echoed the question. The closed-book model answered this one correctly. | Detect answers that repeat the question and fall back to the source passage |
| **False refusal** | hi-D1 (1) | Top similarity 0.667 fell just under the 0.68 cutoff. | Lower the cutoff slightly or calibrate on more dev cases |
| **Partial answers** | en-R3, en-D2, en-N2, kn-R5 (4) | Omitted the 10 kg N value; omitted the 50% flowering stage; said "the passage does not provide quantities" before giving 400 kg/ha; garbled "20x10^6". | Prompt tuning |

**Why the verifier caught nothing.** It checks that quantities exist in the retrieved text. Every error above uses a
number that *is* in the retrieved text, attached to the wrong crop stage, wrong denominator ("2 kg per acre" became
"per hectare"), wrong passage, or wrong adjacent line. A stronger check would need to tie each number to its label,
which was out of scope here. It remains a safeguard against invented numbers, which the closed-book model produces
often, but this test set did not exercise that case.

**Other observations**
* Hindi translation of "finger millet" produced बाजरा (pearl millet) in one answer; the English text is always shown beside
  translations for this reason.
* "peanuts" (plural) was not recognised as groundnut by the crop alias list; retrieval still worked.
* The guide itself gives two groundnut seed rates (120 kg/ha at p185, 125 kg/ha at p190), so the test accepts either.
* The Kannada translation of "NPK @ 100 : 50 : 50" dropped the numbers during development (found at Gate 1);
  ratios are now spelled out ("100, 50 and 50") before translation, and translations whose numbers changed are withheld.

## Limitations of this evaluation
* Small sample (50 cases, 8 per non-English language), a single deterministic run, no confidence intervals.
* Questions were written from the same document as the corpus, so retrieval results are probably optimistic.
* Labels are by an AI reviewer and not independently checked by a human; the regex check is a separate, partial
  safeguard (85% agreement).
* Results apply to Tamil Nadu guidance for six crops only.
* The 0.68 retrieval cutoff was set from six dev cases.
* Latency excludes queueing, Space wake-up, and the free-tier GPU quota (about 2 minutes per day for logged-out users).
