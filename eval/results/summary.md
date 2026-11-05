Cases run: 50/50 (RAG), 24/24 (closed book)

| Configuration (24 English questions) | Factual correctness (regex) |
|---|---|
| A. AgriParam alone | 4/24 (17%) |
| B. RAG, raw answer | 14/24 (58%) |
| C. RAG + verifier (final answer) | 14/24 (58%) |

| Language | Factual correctness, final English answer, paired subset |
|---|---|
| en | 9/16 (56%) |
| hi | 4/8 (50%) |
| kn | 5/8 (62%) |

Fallback rate (verifier replaced answer): 0/39 (0%)
| Configuration (24 English questions) | Reviewed: fully correct | Reviewed: correct or partial |
|---|---|---|
| A. AgriParam alone | 3/24 (12%) | 8/24 (33%) |
| B/C. RAG (verifier changed no answer) | 14/24 (58%) | 17/24 (71%) |

| Language (paired subset, reviewed) | Fully correct | Correct or partial |
|---|---|---|
| en | 9/16 (56%) | 12/16 (75%) |
| hi | 4/8 (50%) | 4/8 (50%) |
| kn | 5/8 (62%) | 6/8 (75%) |

Groundedness on 39 generated answers (Claude's labels): supported 31/39 (79%), partial 3, unsupported 4, no answer 1
  of which supported but incorrect (faithful to the wrong passage): 6
Agreement between regex and reviewer on 'fully correct' (40 answerable cases): 34/40 (85%)
Verifier pass rate on generated answers: 39/39 (100%)
Refusal accuracy (should refuse): 10/10 (100%)
False refusals (answerable refused): 1/40 (2%)
Retrieval Hit@3 (English meaning): 34/40 (85%)
Numbers preserved through translation (hi/kn answers): 15/16 (94%)
Median seconds per query: 0.8