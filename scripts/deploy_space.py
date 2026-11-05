"""Create/update the Hugging Face ZeroGPU Space from this repository.

Usage: python scripts/deploy_space.py [owner/name]      (needs `hf auth login` first)

The GitHub README has no YAML block; the Space needs one, so it is prepended here.
The token stored as the Space secret is read from your local Hugging Face login and never printed.
"""
import sys
import tempfile
from pathlib import Path

from huggingface_hub import HfApi, get_token

REPO = sys.argv[1] if len(sys.argv) > 1 else "DaMCSS/FarmAdvocate"
ROOT = Path(__file__).resolve().parents[1]
HEADER = """---
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

"""

api = HfApi()
api.create_repo(REPO, repo_type="space", space_sdk="gradio", space_hardware="zero-a10g", exist_ok=True)
api.add_space_secret(REPO, "HF_TOKEN", get_token())  # IndicTrans2 is gated
with tempfile.TemporaryDirectory() as tmp:
    (Path(tmp) / "README.md").write_text(HEADER + (ROOT / "README.md").read_text(encoding="utf-8"), encoding="utf-8")
    api.upload_file(path_or_fileobj=str(Path(tmp) / "README.md"), path_in_repo="README.md", repo_id=REPO, repo_type="space")
api.upload_folder(folder_path=str(ROOT), repo_id=REPO, repo_type="space",
                  allow_patterns=["app.py", "requirements.txt", "farmadvocate/*.py", "data/chunks.jsonl", "data/sources.md"],
                  commit_message="Deploy FarmAdvocate")
print("deployed:", f"https://huggingface.co/spaces/{REPO}")
