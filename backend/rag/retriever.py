import pickle
import faiss
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

INDEX_PATH = Path("data/faiss_index.bin")
CHUNKS_PATH = Path("data/chunks.pkl")
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

_model = None
_index = None
_chunks = None


def _load():
    global _model, _index, _chunks
    if _model is None:
        print("Загрузка модели эмбеддингов...")
        _model = SentenceTransformer(EMBEDDING_MODEL)
    if _index is None:
        _index = faiss.read_index(str(INDEX_PATH))
    if _chunks is None:
        with open(CHUNKS_PATH, "rb") as f:
            _chunks = pickle.load(f)


def retrieve(query: str, top_k: int = 3) -> list[dict]:
    _load()

    embedding = _model.encode([query])
    embedding = np.array(embedding).astype("float32")
    faiss.normalize_L2(embedding)

    scores, indices = _index.search(embedding, top_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        chunk = _chunks[idx].copy()
        chunk["score"] = float(score)
        results.append(chunk)

    return results