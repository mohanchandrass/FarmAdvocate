"""In-memory vector retrieval: bge-small embeddings and a NumPy dot product."""
import json

import numpy as np
from sentence_transformers import SentenceTransformer

from . import config


class Retriever:
    def __init__(self):
        self.chunks = [json.loads(line) for line in open(config.CHUNKS_PATH, encoding="utf-8")]
        self.model = SentenceTransformer(config.EMBEDDER, device="cpu")
        self.matrix = self.model.encode([c["text"] for c in self.chunks], normalize_embeddings=True,
                                        batch_size=32, show_progress_bar=False)
        self.crops = np.array([c["crop"] for c in self.chunks])

    def search(self, query, crop=None, k=config.TOP_K):
        """Return [(score, chunk)] best first; filtered to `crop` when one was detected."""
        q = self.model.encode([config.QUERY_PREFIX + query], normalize_embeddings=True)[0]
        scores = self.matrix @ q
        if crop:
            scores = np.where(self.crops == crop, scores, -1.0)
        top = np.argsort(-scores)[:k]
        return [(float(scores[i]), self.chunks[i]) for i in top if scores[i] > -1.0]
