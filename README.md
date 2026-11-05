---
title: FarmAdvocate
emoji: 🌾
colorFrom: green
colorTo: yellow
sdk: gradio
sdk_version: 5.49.1
python_version: "3.12.12"
app_file: app.py
license: mit
short_description: Farmer advisory assistant in English, Hindi and Kannada
---

# 🌾 FarmAdvocate

**CS3235 mini-project, Option 2: AI Farmer Advisory Assistant.** Individual submission by Mohan Chandra S S.

## Problem
Small farmers in India need clear guidance on crops, irrigation and fertilizer doses, but the authoritative
guides are long English-language PDFs. A wrong dose can waste money or damage a crop. FarmAdvocate lets a farmer ask
in English, Hindi or Kannada and answers only from a curated agricultural source, with page citations, and refuses
questions it cannot support. Its source is the Tamil Nadu (TNAU) guide, so recommendations are regional and must be
confirmed with a local Krishi Vigyan Kendra (KVK).

## How it works
```
Question (en/hi/kn) -> IndicTrans2 to English -> scope router (pests, off-topic) -> crop detection
  -> retrieve top 3 passages (bge-small + NumPy cosine search) -> BharatGen AgriParam answers from context
  -> numeric verifier (every quantity must appear in the passages) -> IndicTrans2 back to the user's language
```
| Part | Choice |
|---|---|
| Domain LLM | [BharatGen AgriParam](https://huggingface.co/bharatgenai/AgriParam) (bf16) |
| Translation | [AI4Bharat IndicTrans2](https://github.com/AI4Bharat/IndicTrans2) distilled 200M, en-indic and indic-en |
| Retrieval | `BAAI/bge-small-en-v1.5`, in-memory NumPy index over 282 chunks (no vector database: the corpus is small and fixed) |
| Corpus | [TNAU Crop Production Guide: Agriculture 2020](https://agritech.tnau.ac.in/pdf/AGRICULTURE.pdf): rice, ragi, maize, wheat, redgram, groundnut. Extracted passages only, with attribution (see `data/sources.md`) |
| Frontend and hosting | Gradio on a Hugging Face ZeroGPU Space |

Safety design: pest and pesticide questions are refused, crops outside the corpus are refused, low-similarity
questions return "not found", and an answer with a quantity that is not in the retrieved passages is replaced by the
source passage itself. Translated answers whose numbers changed are withheld in favour of the English text.

## Run it
* **Hosted:** open the Space (link below). The first load after a sleep can take several minutes, and the free GPU
  quota is small for logged-out visitors (about 2 minutes a day); sign in to Hugging Face for more.
* **Locally or on Colab:** a GPU is needed for AgriParam. `notebooks/colab_runner.ipynb` runs the checks and the
  evaluation on a Colab T4. The reported results were produced against the Space instead:
  `python eval/run_eval.py space` then `python eval/make_labels.py` and `python eval/run_eval.py metrics`.
  ```
  pip install -r requirements.txt   # plus: pip install gradio==5.49.1 spaces
  export HF_TOKEN=...                # IndicTrans2 is gated: accept its terms on Hugging Face first
  python app.py
  ```
* **Rebuild the corpus:** `python scripts/build_corpus.py path/to/AGRICULTURE.pdf` (needs only PyMuPDF).

## Evaluation
50 test cases (24 English, 8 Hindi, 8 Kannada answerable, 10 that should be refused) plus 6 dev cases used only to set
the retrieval threshold, run against the deployed Space. Full metrics and the failure analysis are in
[`eval/REPORT.md`](eval/REPORT.md).

| Result (24 English questions) | AgriParam alone | With retrieval (RAG) |
|---|---|---|
| Fully correct (reviewed) | 3 (12%) | 14 (58%) |
| Correct or partial | 8 (33%) | 17 (71%) |

Other results: retrieval Hit@3 85%; 10/10 refusal cases handled; 1 false refusal in 40; 79% of generated answers fully
supported by their retrieved passages; Hindi 4/8 and Kannada 5/8 fully correct. The numeric verifier flagged nothing,
because every wrong number was present in the retrieved text (it was misapplied, not invented): see the report.

> **Disclosure:** the test questions, gold answers and result labels were produced by Claude, an AI model. Hindi and
> Kannada questions were drafted directly rather than machine-translated, but no native speaker or independent human
> reviewed them. The test questions come from the same document as the corpus, so retrieval results may be optimistic.

## Limitations
Tamil Nadu recommendations only; six crops; no pest or disease advice; AgriParam has a 2048-token context and supports
only English and Hindi natively, so Kannada goes through translation; free-tier GPU quota limits demo traffic.

## Links
* Space: https://huggingface.co/spaces/DaMCSS/FarmAdvocate
* Demo recording: _added after recording_
* Technical requirements document: [`docs/TRD.md`](docs/TRD.md)
