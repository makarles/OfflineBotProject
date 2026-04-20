from __future__ import annotations

import logging
import pickle
import re
import pymorphy3 as pymorphy2
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

logger = logging.getLogger("skyassist")

CHUNKS_PATH = Path("data/chunks.pkl")

TOKEN_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9]+", re.UNICODE)


STOPWORDS = {
    # RU
    "в", "на", "с", "к", "по", "за", "из", "от", "до", "у", "о", "об",
    "и", "а", "но", "или", "же", "ли", "бы", "не", "ни",
    "что", "как", "где", "когда", "кто", "это", "есть", "быть",
    # EN
    "the", "a", "an", "is", "are", "was", "were", "be",
    "of", "in", "on", "at", "to", "for", "with", "by",
    "and", "or", "but", "not", "what", "how", "where", "when",
    "this", "that", "i", "you", "we", "they", "do", "does",
}

# Инициализация pymorphy
_morph: pymorphy2.MorphAnalyzer | None = None


def _get_morph() -> pymorphy2.MorphAnalyzer:
    global _morph
    if _morph is None:
        logger.info("Инициализация pymorphy2...")
        _morph = pymorphy2.MorphAnalyzer()
    return _morph


def _is_cyrillic(token: str) -> bool:
    return any("\u0400" <= c <= "\u04FF" for c in token)


def tokenize(text: str) -> list[str]:
    if not text:
        return []
    morph = _get_morph()
    tokens = TOKEN_RE.findall(text.lower())

    result = []
    for tok in tokens:
        if tok in STOPWORDS:
            continue
        if _is_cyrillic(tok):
            # parse() возвращает список разборов, первый обычно самый вероятный
            normal = morph.parse(tok)[0].normal_form
            result.append(normal)
        else:
            result.append(tok)
    return result


class BM25Retriever:
    def __init__(self, chunks: list[dict[str, Any]]):
        if not chunks:
            raise ValueError("BM25Retriever: передан пустой список чанков")

        self._chunks = chunks
        logger.info("BM25: токенизация %d чанков...", len(chunks))
        tokenized_corpus = [tokenize(c.get("text", "")) for c in chunks]
        self._bm25 = BM25Okapi(tokenized_corpus)
        logger.info("BM25: индекс построен")

    def retrieve(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        tokens = tokenize(query)
        if not tokens:
            return []

        scores = self._bm25.get_scores(tokens)
        # argsort по убыванию, берем top-k
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] <= 0:
                # BM25 score 0 означает что ни одно из слов запроса не встречается
                # в документе — такие результаты не имеют смысла
                continue
            chunk = dict(self._chunks[idx])  # копия, чтобы не портить исходный
            chunk["bm25_score"] = float(scores[idx])
            results.append(chunk)
        return results


# Ленивая инициализация (singleton) — чтобы индекс строился только при первом вызове
_retriever: BM25Retriever | None = None


def _load_retriever() -> BM25Retriever:
    global _retriever
    if _retriever is None:
        if not CHUNKS_PATH.exists():
            raise FileNotFoundError(
                f"Не найден {CHUNKS_PATH}. "
                f"Сначала запусти indexer: python -m backend.rag.indexer"
            )
        with CHUNKS_PATH.open("rb") as f:
            chunks = pickle.load(f)
        _retriever = BM25Retriever(chunks)
    return _retriever


def retrieve(query: str, top_k: int = 10) -> list[dict[str, Any]]:
    return _load_retriever().retrieve(query, top_k=top_k)


# CLI для отладки: python -m backend.rag.bm25_retriever "твой запрос"
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if len(sys.argv) < 2:
        print("Usage: python -m backend.rag.bm25_retriever <query>")
        print("Example: python -m backend.rag.bm25_retriever 'Катманду'")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    print(f"\nЗапрос: {query!r}")
    print(f"Токены: {tokenize(query)}\n")

    results = retrieve(query, top_k=5)
    print(f"Найдено {len(results)} чанков:\n")
    for i, r in enumerate(results):
        text_preview = r.get("text", "")[:120].replace("\n", " ")
        print(f"[{i}] bm25={r['bm25_score']:.3f} "
              f"city={r.get('city', '?')} "
              f"section={r.get('section', '?')}")
        print(f"    {text_preview}")
        print()