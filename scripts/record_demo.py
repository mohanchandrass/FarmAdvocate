"""Record docs/demo.gif by driving the live Space UI in a real browser (Playwright + Pillow).

Usage: python scripts/record_demo.py [space_url]
Runs as an anonymous visitor by default. Anonymous ZeroGPU quota is only about 2 minutes a day, so set
HF_TOKEN in the environment to record against your own (larger) quota.
The recorder aborts if the page shows an error banner, so a broken recording is never saved.
"""
import io
import os
import sys
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "https://damcss-farmadvocate.hf.space"
OUT = Path(__file__).resolve().parents[1] / "docs" / "demo.gif"
W, H = 1100, 760
SCENES = [  # (language label, question, hold seconds on the final answer)
    ("English", "What is the seed rate for groundnut?", 2.8),
    ("हिन्दी (Hindi)", "गेहूं की बुवाई का सही समय क्या है?", 2.6),
    ("ಕನ್ನಡ (Kannada)", "ಗೋಧಿ ಬೆಳೆಗೆ ಎಷ್ಟು ಬಾರಿ ನೀರು ಹಾಯಿಸಬೇಕು?", 2.6),
    ("English", "How do I control stem borer in rice?", 2.4),
]
frames = []  # (PIL image, duration ms)


def shot(page, ms):
    img = Image.open(io.BytesIO(page.screenshot(type="png"))).convert("RGB")
    img = img.resize((W * 3 // 4, H * 3 // 4), Image.LANCZOS)
    frames.append((img, ms))


TOKEN = os.environ.get("HF_TOKEN")  # optional: record with your own ZeroGPU quota instead of the anonymous one

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": W, "height": H})
    if TOKEN:  # attach the token only to requests to the Space itself, never to third-party hosts
        page.route("**/*", lambda route: route.continue_(
            headers={**route.request.headers, "authorization": f"Bearer {TOKEN}"})
            if route.request.url.split("/")[2].endswith(".hf.space") else route.continue_())
    page.goto(URL, wait_until="networkidle", timeout=240_000)
    page.wait_for_selector("text=Get advice", timeout=240_000)
    time.sleep(1.5)
    shot(page, 1800)
    for lang, q, hold in SCENES:
        box = page.get_by_label("Ask a farming question")
        box.fill("")
        page.get_by_label("Language").click()
        page.get_by_role("option", name=lang).click()
        box.click()
        for i in range(0, len(q), 6):  # typed look
            box.fill(q[: i + 6])
            if i % 12 == 0:
                shot(page, 160)
        box.fill(q)
        shot(page, 500)
        page.get_by_role("button", name="Get advice").click()
        shot(page, 700)
        page.wait_for_selector(".badge, .toast-wrap", timeout=120_000)
        time.sleep(0.8)
        if page.locator(".toast-wrap, text=quota exceeded").count():
            raise SystemExit(f"Page shows an error (likely GPU quota) on: {q!r}. Nothing saved.")
        page.get_by_text("Sources used").click() if "seed rate" in q else None
        time.sleep(0.6)
        shot(page, int(hold * 1000))
    browser.close()

OUT.parent.mkdir(exist_ok=True)
imgs = [f[0].quantize(colors=128, method=Image.MEDIANCUT, dither=Image.NONE) for f in frames]
imgs[0].save(OUT, save_all=True, append_images=imgs[1:], duration=[f[1] for f in frames], loop=0, optimize=True)
print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.2f} MB, {len(frames)} frames)")
