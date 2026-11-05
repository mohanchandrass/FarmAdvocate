"""FarmAdvocate: Gradio app (UI and /ask API) for a Hugging Face ZeroGPU Space."""
try:  # must be imported before torch on ZeroGPU
    import spaces
    gpu = spaces.GPU(duration=90)
except Exception:  # running locally or on Colab
    def gpu(fn):
        return fn

import gradio as gr

from farmadvocate import config, pipeline

pipeline.load()  # models are placed on the GPU at module level, as ZeroGPU requires

BADGES = {
    "verified": "✅ Verified against the sources",
    "unverified": "⚠️ Unverified: showing the source passage instead",
    "out_of_scope": "🚫 Out of scope",
    "unsupported_crop": "🚫 Crop not covered",
    "not_found": "❓ Not found in the sources",
}


@gpu
def _run(question, lang):
    return pipeline.answer(question, lang)


def ask(question, lang_label):
    if not question or not question.strip():
        return "", "", "Please type a question.", "", {}
    out = _run(question.strip(), config.LANGS[lang_label])
    src = "\n\n".join(
        f"**{s['crop']} · {s['section']} · page {s['page']}** (similarity {s['score']})\n\n> {s['text']}"
        for s in out["sources"]) or "_No sources used._"
    return out["answer"], out["answer_en"], BADGES.get(out["status"], out["status"]), src, out


EXAMPLES = [
    ["What is the seed rate for groundnut?", "English"],
    ["How much gypsum should be applied to groundnut?", "English"],
    ["गेहूं की बुवाई का सही समय क्या है?", "हिन्दी (Hindi)"],
    ["रागी के लिए नाइट्रोजन, फास्फोरस और पोटाश की अनुशंसित मात्रा क्या है?", "हिन्दी (Hindi)"],
    ["ಗೋಧಿ ಬೆಳೆಗೆ ಎಷ್ಟು ಬಾರಿ ನೀರು ಹಾಯಿಸಬೇಕು?", "ಕನ್ನಡ (Kannada)"],
    ["How do I control stem borer in rice?", "English"],
]

with gr.Blocks(title="FarmAdvocate") as demo:
    gr.Markdown("# 🌾 FarmAdvocate\nAsk about crop, irrigation and fertilizer in English, Hindi or Kannada. "
                "Answers come from the TNAU Crop Production Guide 2020 (rice, ragi, maize, wheat, redgram, groundnut) "
                "using BharatGen AgriParam and AI4Bharat IndicTrans2.")
    with gr.Row():
        with gr.Column(scale=3):
            question = gr.Textbox(label="Your question", lines=3)
            lang = gr.Dropdown(list(config.LANGS), value="English", label="Language")
            btn = gr.Button("Ask", variant="primary")
            gr.Examples(EXAMPLES, inputs=[question, lang], cache_examples=False)
        with gr.Column(scale=4):
            badge = gr.Markdown()
            answer = gr.Textbox(label="Answer", lines=6, interactive=False)
            answer_en = gr.Textbox(label="Answer in English", lines=4, interactive=False)
            with gr.Accordion("Sources", open=False):
                sources = gr.Markdown()
            raw = gr.JSON(label="API response", visible=False)
    gr.Markdown(f"_{config.NOTICE}_")
    btn.click(ask, [question, lang], [answer, answer_en, badge, sources, raw], api_name="ask")

if __name__ == "__main__":
    demo.queue().launch()
