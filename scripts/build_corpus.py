"""Build data/chunks.jsonl from the TNAU Crop Production Guide 2020.

Usage (Windows or Linux, needs only PyMuPDF):
    python scripts/build_corpus.py [path/to/AGRICULTURE.pdf]
"""
import json
import re
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
PDF = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "raw" / "AGRICULTURE.pdf"
OUT = ROOT / "data" / "chunks.jsonl"
PDF_OFFSET = 11  # PDF page index = printed page + 11

# Printed page ranges, inclusive. Rice skips the variety tables on printed pages 1-16.
CROPS = {
    "Rice": (17, 64), "Ragi": (92, 102), "Maize": (103, 116),
    "Wheat": (122, 124), "Redgram": (125, 133), "Groundnut": (181, 197),
}
# Sections dropped from the corpus: pest/disease/weed chemicals are out of scope.
DROP = re.compile(r"(?i)crop protection|pest|disease|weed|herbicide|insecticid|fungicid|variet")
WORDS_MIN, WORDS_MAX, OVERLAP = 180, 250, 40
BULLET = re.compile(r"^[•●▪�\-\*•]\s*")


def fix_spaced(text):
    """Repair letter-spaced runs such as 'I t a l s o g r o w n'."""
    def join(m):
        return m.group(0).replace(" ", "")
    return re.sub(r"(?:\b\w ){6,}\w\b", join, text)


def page_items(page):
    """Return [(y, kind, text, is_heading)] in reading order, with tables rendered as rows."""
    items, boxes = [], []
    try:
        for t in page.find_tables().tables:
            rows = t.extract()
            if not rows or len(rows) < 2:
                continue
            lines = [" | ".join((c or "").replace("\n", " ").strip() for c in r) for r in rows]
            items.append((t.bbox[1], "table", "\n".join(lines), False))
            boxes.append(pymupdf.Rect(t.bbox))
    except Exception:
        pass
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            r = pymupdf.Rect(ln["bbox"])
            if any(r.intersects(bx) and (r & bx).get_area() > 0.5 * r.get_area() for bx in boxes):
                continue
            sp = ln["spans"]
            txt = "".join(s["text"] for s in sp).strip()
            if not txt or re.fullmatch(r"\d{1,3}", txt):
                continue
            bold = all(("Bold" in s["font"] or s["flags"] & 16) for s in sp if s["text"].strip())
            heading = bold and sp[0]["size"] >= 11.5 and len(txt) < 90 and not BULLET.match(txt)
            items.append((ln["bbox"][1], "line", txt, heading))
    return [i for i in sorted(items, key=lambda i: i[0])]


def sections_for(crop, first, last):
    """Yield (system, section, page_start, page_end, text) per section."""
    system, section, buf, pages = "", "General", [], []

    def flush():
        if buf and section_ok(section) and system_ok(system):
            yield (system, section, min(pages), max(pages), " ".join(buf))

    def section_ok(s):
        return not DROP.search(s)

    def system_ok(s):
        return not DROP.search(s)

    for printed in range(first, last + 1):
        page = doc[printed + PDF_OFFSET]
        for _, kind, txt, heading in page_items(page):
            if kind == "table":
                buf.append("TABLE: " + txt.replace("\n", " ; "))
                pages.append(printed)
                continue
            if heading:
                yield from flush()
                buf, pages = [], []
                clean = re.sub(r"^[\d.]+\s*", "", txt).strip(" :")
                if clean.isupper() and len(clean) > 6:
                    system, section = clean.title(), "General"
                else:
                    section = clean
                continue
            buf.append(BULLET.sub("", fix_spaced(txt)))
            pages.append(printed)
    yield from flush()


def chunks_of(text):
    words = text.split()
    if len(words) <= WORDS_MAX:
        return [" ".join(words)]
    out, i = [], 0
    while i < len(words):
        out.append(" ".join(words[i:i + WORDS_MAX]))
        if i + WORDS_MAX >= len(words):
            break
        i += WORDS_MAX - OVERLAP
    return out


doc = pymupdf.open(PDF)
rows = []
for crop, (a, b) in CROPS.items():
    for system, section, p0, p1, text in sections_for(crop, a, b):
        if len(text.split()) < 12:
            continue
        label = f"Crop: {crop} | " + (f"System: {system} | " if system else "") + f"Section: {section}"
        for part in chunks_of(text):
            rows.append({"id": f"c{len(rows):04d}", "crop": crop, "section": section,
                         "system": system, "page_start": p0, "page_end": p1,
                         "text": f"{label}. {part}"})

OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

by_crop = {}
for r in rows:
    by_crop[r["crop"]] = by_crop.get(r["crop"], 0) + 1
words = [len(r["text"].split()) for r in rows]
print(f"{len(rows)} chunks, words min/median/max = {min(words)}/{sorted(words)[len(words)//2]}/{max(words)}")
print(by_crop)
