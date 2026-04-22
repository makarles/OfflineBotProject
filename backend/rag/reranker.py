from __future__ import annotations

import logging
from typing import Any

import torch
from sentence_transformers import CrossEncoder

logger = logging.getLogger("skyassist")

MODEL_NAME = "BAAI/bge-reranker-v2-m3"

# Singleton — модель грузится один раз при старте сервера
_reranker: CrossEncoder | None = None


def _load_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        logger.info("Reranker: загрузка модели %s...", MODEL_NAME)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _reranker = CrossEncoder(MODEL_NAME, device=device, max_length=512)
        logger.info("Reranker: загружен на %s", device)
    return _reranker


def rerank(
    query: str,
    chunks: list[dict[str, Any]],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    if not chunks:
        return []

    model = _load_reranker()

    # Формируем пары (query, chunk_text) для модели
    pairs = [(query, chunk.get("text", "")) for chunk in chunks]

    scores = model.predict(pairs, show_progress_bar=False)

    # Привязываем scores к чанкам и сортируем
    scored_chunks = []
    for chunk, score in zip(chunks, scores):
        chunk = dict(chunk)  # копия чтобы не портить оригинал
        chunk["rerank_score"] = float(score)
        scored_chunks.append(chunk)

    scored_chunks.sort(key=lambda c: c["rerank_score"], reverse=True)

    logger.info(
        "Rerank: %d to %d, top score=%.3f, bottom score=%.3f",
        len(chunks), min(top_k, len(scored_chunks)),
        scored_chunks[0]["rerank_score"],
        scored_chunks[-1]["rerank_score"] if len(scored_chunks) > 1 else 0.0
    )

    return scored_chunks[:top_k]


if __name__ == "__main__":
    import sys
    from backend.rag import hybrid_retriever

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if len(sys.argv) < 2:
        print("Usage: python -m backend.rag.reranker <query>")
        print("Example: python -m backend.rag.reranker 'Какая валюта в Дубае?'")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    print(f"\nЗапрос: {query!r}\n")

    # 20 кандидатов от hybrid
    candidates = hybrid_retriever.retrieve(query, top_k=20)
    print(f"Hybrid вернул {len(candidates)} кандидатов\n")

    print("Топ-5 от hybrid (до reranker):")
    for i, c in enumerate(candidates[:5]):
        text_preview = c.get("text", "")[:100].replace("\n", " ")
        print(f"  [{i}] rrf={c.get('rrf_score', 0):.4f} "
              f"dense={c.get('score', 0):.3f} "
              f"city={c.get('city', '?') or '(none)'} "
              f"| {text_preview}")

    # Reranker пересортирует
    reranked = rerank(query, candidates, top_k=5)

    print("\nТоп-5 после reranker:")
    for i, c in enumerate(reranked):
        text_preview = c.get("text", "")[:100].replace("\n", " ")
        print(f"  [{i}] rerank={c['rerank_score']:+.3f} "
              f"dense={c.get('score', 0):.3f} "
              f"city={c.get('city', '?') or '(none)'} "
              f"| {text_preview}")
