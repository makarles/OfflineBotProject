from __future__ import annotations

import logging
from typing import Any

from backend.rag import retriever as dense_retriever
from backend.rag import bm25_retriever

logger = logging.getLogger("skyassist")

RRF_K = 60  # Сглаживающая константа RRF

CANDIDATES_PER_RETRIEVER = 20


def _chunk_id(chunk: dict[str, Any]) -> str:
    return chunk.get("text", "")[:200]


def retrieve(query: str, top_k: int = 8) -> list[dict[str, Any]]:
    dense_results = dense_retriever.retrieve(query, top_k=CANDIDATES_PER_RETRIEVER)
    bm25_results = bm25_retriever.retrieve(query, top_k=CANDIDATES_PER_RETRIEVER)

    logger.info(
        "Hybrid query: %r (dense=%d, bm25=%d)",
        query, len(dense_results), len(bm25_results)
    )

    rrf_scores: dict[str, float] = {}
    chunks_by_id: dict[str, dict[str, Any]] = {}

    for rank, chunk in enumerate(dense_results, start=1):
        cid = _chunk_id(chunk)
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (RRF_K + rank)
        if cid not in chunks_by_id:
            chunks_by_id[cid] = dict(chunk)

    for rank, chunk in enumerate(bm25_results, start=1):
        cid = _chunk_id(chunk)
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (RRF_K + rank)
        if cid not in chunks_by_id:
            chunks_by_id[cid] = dict(chunk)
        else:
            chunks_by_id[cid]["bm25_score"] = chunk.get("bm25_score")

    # Сортировка по RRF-скору, берём top-k
    sorted_ids = sorted(rrf_scores.keys(), key=lambda c: rrf_scores[c], reverse=True)

    results = []
    for cid in sorted_ids[:top_k]:
        chunk = chunks_by_id[cid]
        chunk["rrf_score"] = rrf_scores[cid]
        if "score" not in chunk:
            chunk["score"] = 0.0
        results.append(chunk)

    logger.info("Hybrid returned %d chunks (out of %d unique candidates)",
                len(results), len(rrf_scores))
    return results


# CLI для отладки: python -m backend.rag.hybrid_retriever "запрос"
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if len(sys.argv) < 2:
        print("Usage: python -m backend.rag.hybrid_retriever <query>")
        print("Example: python -m backend.rag.hybrid_retriever 'Летает ли AeroLine в Катманду?'")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    print(f"\nЗапрос: {query!r}\n")

    results = retrieve(query, top_k=8)
    print(f"Топ-{len(results)} после RRF:\n")
    for i, r in enumerate(results):
        text_preview = r.get("text", "")[:120].replace("\n", " ")
        dense_s = r.get("score", 0.0)
        bm25_s = r.get("bm25_score")
        bm25_str = f"bm25={bm25_s:.2f}" if bm25_s is not None else "bm25=—"
        print(f"[{i}] rrf={r['rrf_score']:.4f} dense={dense_s:.3f} {bm25_str} "
              f"city={r.get('city', '?') or '(none)'} "
              f"section={r.get('section', '?')}")
        print(f"    {text_preview}")
        print()