# Data sources

`data/chunks.jsonl` contains passages extracted, for educational use, from:

**Crop Production Guide: Agriculture 2020**, Directorate of Agriculture, Chepauk, Chennai, and Tamil Nadu
Agricultural University, Coimbatore. https://agritech.tnau.ac.in/pdf/AGRICULTURE.pdf
Copyright remains with the publishers (the TNAU site states "All Rights Reserved"). The original PDF is not included
in this repository. Crop-protection (pest, disease, weed and herbicide) sections and variety tables were removed.
Printed page numbers in citations refer to the guide's own numbering.

Included crops: rice (printed pages 17-64), ragi (92-102), maize (103-116), wheat (122-124), redgram (125-133),
groundnut (181-197). Rebuild with `python scripts/build_corpus.py`.
