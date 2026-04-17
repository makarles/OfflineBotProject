import json
import logging
import os
import pickle
from pathlib import Path

import faiss
import numpy as np
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer


os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

logger = logging.getLogger("skyassist.indexer")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

# Пути
KNOWLEDGE_BASE_DIR = Path("data/knowledge_base")
INDEX_PATH = Path("data/faiss_index.bin")
CHUNKS_PATH = Path("data/chunks.pkl")

# Модель эмбеддингов
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Параметры чакинга
CHUNK_SIZE = 700
CHUNK_OVERLAP = 100

# Человекочитаемые названия секций для заголовков чанков
SECTION_TITLES = {
    "visa": "Визовый режим",
    "currency": "Валюта",
    "climate": "Климат",
    "airport_transport": "Транспорт из аэропорта",
    "tips": "Советы туристу",
}


def load_documents() -> list[dict]:
    documents = []
    paths = sorted(KNOWLEDGE_BASE_DIR.glob("*.json")) + sorted(
        KNOWLEDGE_BASE_DIR.glob("cities/*.json")
    )
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                doc = json.load(f)
                doc["_source_path"] = str(path)
                documents.append(doc)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Пропущен файл %s: %s", path, e)
    logger.info("Загружено документов: %d", len(documents))
    return documents


def make_chunk_metadata(doc: dict) -> dict:
    return {
        "title": doc.get("title", ""),
        "category": doc.get("category", ""),
        "language": doc.get("language", "ru"),
        "city": doc.get("city", ""),
        "iata": doc.get("iata", ""),
        "country": doc.get("country", ""),
    }


def _flatten_section_value(value) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        parts = []
        for k, v in value.items():
            if isinstance(v, str) and v.strip():
                parts.append(f"{k}: {v.strip()}")
        return ". ".join(parts)
    if isinstance(value, list):
        parts = [str(item).strip() for item in value if str(item).strip()]
        return ". ".join(parts)
    return ""


def build_practical_chunks(doc: dict, base_meta: dict) -> list[dict]:
    practical = doc.get("practical_info")
    if not practical or not isinstance(practical, dict):
        return []

    chunks = []
    for section_key, section_value in practical.items():
        flat = _flatten_section_value(section_value)
        if not flat:
            continue

        section_label = SECTION_TITLES.get(section_key, section_key)
        city = base_meta.get("city", "")
        chunk_text = f"{section_label} ({city}): {flat}"

        chunks.append({
            **base_meta,
            "text": chunk_text,
            "section": section_key,
            "chunk_index": 0,
        })
    return chunks


def build_content_chunks(
        doc: dict,
        base_meta: dict,
        splitter: RecursiveCharacterTextSplitter,
) -> list[dict]:
    content = doc.get("content", "")
    if not content or not isinstance(content, str):
        return []

    pieces = splitter.split_text(content)
    chunks = []
    for i, piece in enumerate(pieces):
        chunks.append({
            **base_meta,
            "text": piece,
            "section": "content",
            "chunk_index": i,
        })
    return chunks


def build_all_chunks(documents: list[dict]) -> list[dict]:
    """Главная функция сборки чанков из всех документов."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""],
        length_function=len,
    )

    all_chunks = []
    for doc in documents:
        base_meta = make_chunk_metadata(doc)

        practical_chunks = build_practical_chunks(doc, base_meta)
        content_chunks = build_content_chunks(doc, base_meta, splitter)

        doc_chunks = practical_chunks + content_chunks
        if not doc_chunks:
            logger.warning(
                "Документ без чанков: %s (пустые content и practical_info)",
                doc.get("_source_path", doc.get("title", "<unknown>")),
            )
            continue

        all_chunks.extend(doc_chunks)

    logger.info("Всего чанков: %d", len(all_chunks))

    # Статистика для лога
    by_section: dict[str, int] = {}
    for chunk in all_chunks:
        by_section[chunk["section"]] = by_section.get(chunk["section"], 0) + 1
    logger.info("Распределение по секциям: %s", by_section)

    return all_chunks


def atomic_save_index(index: faiss.Index, chunks: list[dict]) -> None:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_index = INDEX_PATH.with_suffix(".bin.tmp")
    tmp_chunks = CHUNKS_PATH.with_suffix(".pkl.tmp")

    faiss.write_index(index, str(tmp_index))
    with open(tmp_chunks, "wb") as f:
        pickle.dump(chunks, f)

    os.replace(tmp_index, INDEX_PATH)
    os.replace(tmp_chunks, CHUNKS_PATH)
    logger.info("Индекс сохранён: %s", INDEX_PATH)
    logger.info("Чанки сохранены: %s", CHUNKS_PATH)


def build_index() -> None:
    logger.info("Загрузка модели эмбеддингов: %s", EMBEDDING_MODEL)
    model = SentenceTransformer(EMBEDDING_MODEL)

    documents = load_documents()
    if not documents:
        logger.error("База знаний пуста — нечего индексировать")
        return

    all_chunks = build_all_chunks(documents)
    if not all_chunks:
        logger.error("Не получилось собрать ни одного чанка")
        return

    texts = [chunk["text"] for chunk in all_chunks]
    logger.info("Вычисление эмбеддингов для %d чанков...", len(texts))
    embeddings = model.encode(texts, show_progress_bar=True)
    embeddings = np.asarray(embeddings, dtype="float32")

    faiss.normalize_L2(embeddings)

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    atomic_save_index(index, all_chunks)
    logger.info("Индексирование завершено")


if __name__ == "__main__":
    build_index()

