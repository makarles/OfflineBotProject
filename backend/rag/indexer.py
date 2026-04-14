import json
import os
import pickle
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

KNOWLEDGE_BASE_DIR = Path("data/knowledge_base")
INDEX_PATH = Path("data/faiss_index.bin")
CHUNKS_PATH = Path("data/chunks.pkl")

EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CHUNK_SIZE = 300
CHUNK_OVERLAP = 50


def load_documents() -> list[dict]:
    documents = []
    # из корневой папки и из подпапки cities
    for pattern in ["*.json", "cities/*.json"]:
        for file in KNOWLEDGE_BASE_DIR.glob(pattern):
            with open(file, "r", encoding="utf-8") as f:
                doc = json.load(f)
                documents.append(doc)
    print(f"Загружено документов: {len(documents)}")
    return documents


def split_into_chunks(text: str, chunk_size: int = CHUNK_SIZE,
                      overlap: int = CHUNK_OVERLAP) -> list[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def build_index():
    print("Загрузка модели эмбеддингов...")
    model = SentenceTransformer(EMBEDDING_MODEL)

    documents = load_documents()

    all_chunks = []
    for doc in documents:
        chunks = split_into_chunks(doc["content"])
        for chunk in chunks:
            all_chunks.append({
                "text": chunk,
                "title": doc["title"],
                "category": doc["category"],
                "language": doc.get("language", "ru")
            })

    print(f"Всего чанков: {len(all_chunks)}")

    texts = [chunk["text"] for chunk in all_chunks]
    print("Вычисление эмбеддингов...")
    embeddings = model.encode(texts, show_progress_bar=True)
    embeddings = np.array(embeddings).astype("float32")

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)

    faiss.normalize_L2(embeddings)
    index.add(embeddings)

    faiss.write_index(index, str(INDEX_PATH))
    with open(CHUNKS_PATH, "wb") as f:
        pickle.dump(all_chunks, f)

    print(f"Индекс сохранён: {INDEX_PATH}")
    print(f"Чанки сохранены: {CHUNKS_PATH}")
    print("Индексирование завершено!")


if __name__ == "__main__":
    build_index()