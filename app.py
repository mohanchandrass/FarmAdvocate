"""FarmAdvocate: Gradio app (UI and /ask API) for a Hugging Face ZeroGPU Space."""
try:  # must be imported before torch on ZeroGPU
    import spaces
    gpu = spaces.GPU(duration=30)  # a query takes a few seconds; a short request leaves quota usable and queues faster
except Exception:  # running locally or on Colab
    def gpu(fn):
        return fn

import html

import gradio as gr

from farmadvocate import cache as saved_answers
from farmadvocate import config, pipeline

pipeline.load()  # models are placed on the GPU at module level, as ZeroGPU requires

BADGES = {
    "verified": ("Quantities found in the sources", "ok"),
    "unverified": ("Unverified: showing the source passage instead", "warn"),
    "out_of_scope": ("Out of scope: please ask your local KVK", "stop"),
    "unsupported_crop": ("Crop not covered by the sources", "stop"),
    "not_found": ("Not found in the sources", "warn"),
}

CSS = """
.gradio-container {max-width: 1080px !important; margin: auto;}
#hero {background: linear-gradient(135deg, #14532d 0%, #3f8f4f 60%, #a3b83a 100%); color: #fff;
       border-radius: 16px; padding: 26px 30px; margin-bottom: 6px;}
#hero h1 {margin: 0 0 4px 0; font-size: 2rem; color: #fff;}
#hero p {margin: 2px 0; color: #eef7e8; font-size: 1.02rem;}
.pill {display: inline-block; background: rgba(255,255,255,.18); border-radius: 999px; padding: 3px 12px;
       margin: 8px 6px 0 0; font-size: .85rem;}
.badge {border-radius: 10px; padding: 10px 14px; font-weight: 600; margin-bottom: 6px;}
.badge.ok {background: #e7f6ea; color: #14532d; border: 1px solid #b7e0c0;}
.badge.warn {background: #fff6e0; color: #7a4b00; border: 1px solid #f0d58c;}
.badge.stop {background: #fdeaea; color: #8a1c1c; border: 1px solid #efb7b7;}
.meta {font-size: .85rem; color: #5b6b5e; font-weight: 400; margin-top: 4px;}
#notice {font-size: .88rem; color: #5b6b5e;}
"""

HERO = """
<div id="hero">
  <h1>FarmAdvocate</h1>
  <p>Crop, irrigation and fertilizer advice in your language, answered only from a trusted agricultural guide.</p>
  <span class="pill">English</span><span class="pill">हिन्दी</span><span class="pill">ಕನ್ನಡ</span>
  <span class="pill">Cited sources</span><span class="pill">Refuses pest &amp; off-topic questions</span>
</div>
"""

FOOTER = f"""
<div id="notice">

{config.NOTICE}

**Under the hood:** BharatGen AgriParam (answers) · AI4Bharat IndicTrans2 (Hindi/Kannada translation) ·
bge-small retrieval over the TNAU Crop Production Guide 2020 (rice, ragi, maize, wheat, redgram, groundnut) ·
numeric verifier. Source and write-up: [github.com/mohanchandrass/FarmAdvocate](https://github.com/mohanchandrass/FarmAdvocate)

</div>
"""


@gpu
def _run(question, lang):
    return pipeline.answer(question, lang)


@gpu
def _run_closed_book(question, lang):
    return pipeline.answer(question, lang, mode="closed_book")


def closed_book(question, lang_label):
    """Evaluation baseline (AgriParam alone, no retrieval). Not shown in the UI."""
    return _run_closed_book(question.strip(), config.LANGS[lang_label])


SAVED = saved_answers.load()  # answers saved from the evaluation run for the example and test questions


def _answer(question, lang_label, use_saved):
    if not question or not question.strip():
        return "", "", '<div class="badge warn">Please type a question.</div>', "", {}
    code, q = config.LANGS[lang_label], question.strip()
    saved = SAVED.get(saved_answers.cache_key(q, code)) if use_saved else None
    if saved:  # no GPU needed
        out = dict(saved, cached=True)
    else:
        out = pipeline.quick_refusal(q, code) or _run(q, code)  # refusals need no GPU either
    text, kind = BADGES.get(out["status"], (out["status"], "warn"))
    meta = f"Understood as: “{html.escape(out['question_en'])}”"
    if out.get("crop"):
        meta += f" · Crop: {html.escape(out['crop'])}"
    if out.get("cached"):
        meta += " · Saved answer from the evaluation run (no GPU used)"
    src = "\n\n".join(
        f"**{s['crop']} · {s.get('system') or 'General'} · {s['section']} · page {s['page']}** (similarity {s['score']})\n\n> {s['text']}"
        for s in out["sources"]) or "_No sources used for this reply._"
    badge_html = f'<div class="badge {kind}">{text}<div class="meta">{meta}</div></div>'
    return out["answer"], out["answer_en"], badge_html, src, out


def ask(question, lang_label):
    return _answer(question, lang_label, use_saved=True)


def ask_live(question, lang_label):
    """Always runs the full pipeline (used by the evaluation, which must never read saved answers)."""
    return _answer(question, lang_label, use_saved=False)


EXAMPLES = [
    ["What is the seed rate for groundnut?", "English"],
    ["How much gypsum should be applied to groundnut?", "English"],
    ["गेहूं की बुवाई का सही समय क्या है?", "हिन्दी (Hindi)"],
    ["रागी के लिए नाइट्रोजन, फास्फोरस और पोटाश की अनुशंसित मात्रा क्या है?", "हिन्दी (Hindi)"],
    ["ಗೋಧಿ ಬೆಳೆಗೆ ಎಷ್ಟು ಬಾರಿ ನೀರು ಹಾಯಿಸಬೇಕು?", "ಕನ್ನಡ (Kannada)"],
    ["How do I control stem borer in rice?", "English"],
]

theme = gr.themes.Soft(primary_hue="green", secondary_hue="lime", neutral_hue="stone")

with gr.Blocks(title="FarmAdvocate", theme=theme, css=CSS) as demo:
    gr.HTML(HERO)
    with gr.Row(equal_height=False):
        with gr.Column(scale=4):
            question = gr.Textbox(label="Ask a farming question", lines=3,
                                  placeholder="e.g. What is the seed rate for groundnut?")
            lang = gr.Dropdown(list(config.LANGS), value="English", label="Language")
            btn = gr.Button("Get advice", variant="primary")
            gr.Examples(EXAMPLES, inputs=[question, lang], cache_examples=False, label="Try an example")
        with gr.Column(scale=6):
            badge = gr.HTML()
            answer = gr.Textbox(label="Answer", lines=5, interactive=False, show_copy_button=True)
            answer_en = gr.Textbox(label="Answer in English", lines=3, interactive=False)
            with gr.Accordion("Sources used", open=False):
                sources = gr.Markdown()
            raw = gr.JSON(label="API response", visible=False)
    gr.Markdown(FOOTER)
    btn.click(ask, [question, lang], [answer, answer_en, badge, sources, raw], api_name="ask")
    question.submit(ask, [question, lang], [answer, answer_en, badge, sources, raw], api_name=False)
    hidden = gr.Button(visible=False)  # endpoints used only by the evaluation
    hidden.click(closed_book, [question, lang], [raw], api_name="closed_book")
    hidden.click(ask_live, [question, lang], [answer, answer_en, badge, sources, raw], api_name="ask_live")

if __name__ == "__main__":
    demo.queue().launch()
