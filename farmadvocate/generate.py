"""AgriParam answer generation with a token budget (the model has a 2048-token context)."""
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from . import config

INSTRUCTION = ("Answer using only the context above. Include exact quantities and units. "
               "If the context does not contain the answer, say you do not know.")


class Generator:
    def __init__(self, device):
        self.device = device
        self.tok = AutoTokenizer.from_pretrained(config.AGRIPARAM, trust_remote_code=True,
                                                 revision=config.AGRIPARAM_REV)
        self.model = AutoModelForCausalLM.from_pretrained(
            config.AGRIPARAM, trust_remote_code=True, torch_dtype=torch.bfloat16,
            revision=config.AGRIPARAM_REV).to(device).eval()

    def _prompt(self, question, passages):
        ctx = "\n\n".join(passages)
        return f"<context> {ctx} <user> {INSTRUCTION}\nQuestion: {question} <assistant>"

    def build_prompt(self, question, passages):
        """Drop the lowest-ranked passage until the prompt fits the token budget."""
        passages = list(passages)
        while True:
            prompt = self._prompt(question, passages)
            n = len(self.tok(prompt)["input_ids"])
            if n <= config.MAX_PROMPT_TOKENS or len(passages) <= 1:
                return prompt, passages
            passages.pop()

    def _generate(self, prompt):
        enc = self.tok(prompt, return_tensors="pt", truncation=True,
                       max_length=config.MAX_PROMPT_TOKENS + 100)
        enc.pop("token_type_ids", None)
        enc = enc.to(self.device)
        n_in = enc["input_ids"].shape[1]
        with torch.inference_mode():
            out = self.model.generate(
                **enc, max_new_tokens=config.MAX_NEW_TOKENS, do_sample=False, repetition_penalty=1.1,
                use_cache=True, eos_token_id=self.tok.eos_token_id, pad_token_id=self.tok.eos_token_id)
        text = self.tok.decode(out[0][n_in:], skip_special_tokens=True)
        for marker in ("<user>", "<assistant>", "<context>"):
            text = text.split(marker)[0]
        return text.strip()

    def answer_with_context(self, question, passages):
        prompt, used = self.build_prompt(question, passages)
        return self._generate(prompt), used

    def answer_closed_book(self, question):
        """Baseline A: AgriParam alone, no retrieved context."""
        return self._generate(f"<user> {question} <assistant>")
