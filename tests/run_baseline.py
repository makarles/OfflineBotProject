from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import requests

# Настройки
API_URL = "http://localhost:8000/chat"
REQUEST_TIMEOUT = 60  # секунд на один запрос
SAVE_EVERY = 10       # сохранять промежуточные результаты каждые N вопросов
RETRY_ONCE = True     # одна попытка повтора при сетевой ошибке

TESTS_DIR = Path(__file__).parent
DEFAULT_INPUT = TESTS_DIR / "evaluation_set_5cities.jsonl"
DEFAULT_OUTPUT = TESTS_DIR / "baseline_metrics.json"

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("baseline")


# Вспомогательные функции

def detect_response_language(text: str) -> str:
    if not text:
        return "unknown"
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "unknown"
    cyrillic = sum(1 for c in letters if "\u0400" <= c <= "\u04FF")
    return "ru" if cyrillic / len(letters) > 0.3 else "en"


def keyword_hit_rate(answer: str, expected_keywords: list[str]) -> float:
    if not expected_keywords:
        return None  # type: ignore
    answer_lower = answer.lower()
    hits = sum(1 for kw in expected_keywords if kw.lower() in answer_lower)
    return hits / len(expected_keywords)


def is_refusal(answer: str, language: str) -> bool:
    if not answer:
        return True
    answer_lower = answer.lower().strip()

    ru_refusal_markers = [
        "нет такой информации",
        "у меня нет",
        "не располагаю",
        "не могу ответить",
        "не знаю",
        "не обладаю",
    ]
    en_refusal_markers = [
        "don't have this information",
        "do not have this information",
        "don't have that information",
        "don't know",
        "cannot answer",
        "unable to provide",
        "i don't have",
    ]
    markers = ru_refusal_markers if language == "ru" else en_refusal_markers
    # Короткий ответ с маркером отказа — почти наверняка отказ.
    # Длинный ответ с маркером — возможно начало с отказа + всё равно галлюцинация.
    short = len(answer_lower) < 200
    has_marker = any(m in answer_lower for m in markers)
    return short and has_marker


def call_chat_api(message: str) -> tuple[str | None, float | None, str | None]:
    payload = {"message": message}
    attempts = 2 if RETRY_ONCE else 1

    for attempt in range(attempts):
        try:
            t0 = time.perf_counter()
            response = requests.post(
                API_URL,
                json=payload,
                timeout=REQUEST_TIMEOUT,
                headers={"Content-Type": "application/json"},
            )
            latency = time.perf_counter() - t0
            response.raise_for_status()
            data = response.json()
            answer = data.get("response", "")
            return answer, latency, None
        except requests.exceptions.Timeout:
            err = f"timeout after {REQUEST_TIMEOUT}s"
        except requests.exceptions.ConnectionError:
            err = "connection error (is the server running?)"
        except requests.exceptions.HTTPError as e:
            err = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
        except Exception as e:
            err = f"{type(e).__name__}: {e}"

        if attempt < attempts - 1:
            logger.warning("Попытка %d провалена (%s), повторяю...", attempt + 1, err)
            time.sleep(2)
        else:
            return None, None, err
    return None, None, "unknown"


# Запись промежуточных результатов

@dataclass
class TestResult:
    id: str
    question: str
    language: str
    category: str
    expected_keywords: list[str]
    answer: str
    latency_sec: float | None
    error: str | None
    # вычисленные метрики
    answer_language: str
    language_match: bool
    keyword_hit_rate: float | None  # None если keywords пустой
    is_refusal: bool
    refusal_expected: bool
    refusal_correct: bool


def save_results(results: list[TestResult], output_path: Path, metrics: dict) -> None:
    payload = {
        "metadata": {
            "total_questions": len(results),
            "api_url": API_URL,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "metrics": metrics,
        "results": [asdict(r) for r in results],
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# Агрегация метрик

def compute_metrics(results: list[TestResult]) -> dict[str, Any]:
    by_category: dict[str, list[TestResult]] = defaultdict(list)
    for r in results:
        by_category[r.category].append(r)

    def aggregate(bucket: list[TestResult]) -> dict[str, Any]:
        if not bucket:
            return {"count": 0}

        # Keyword hit rate — только для вопросов с непустым списком
        with_keywords = [r for r in bucket if r.keyword_hit_rate is not None]
        khr = (
            sum(r.keyword_hit_rate for r in with_keywords) / len(with_keywords)
            if with_keywords
            else None
        )

        # Language match rate
        lmr = sum(1 for r in bucket if r.language_match) / len(bucket)

        # Refusal correctness — только где ожидается отказ
        refusal_expected = [r for r in bucket if r.refusal_expected]
        rc = (
            sum(1 for r in refusal_expected if r.refusal_correct) / len(refusal_expected)
            if refusal_expected
            else None
        )

        # Latency
        latencies = [r.latency_sec for r in bucket if r.latency_sec is not None]
        lat_mean = sum(latencies) / len(latencies) if latencies else None

        # Ошибки
        errors = sum(1 for r in bucket if r.error)

        return {
            "count": len(bucket),
            "keyword_hit_rate": round(khr, 3) if khr is not None else None,
            "questions_with_keywords": len(with_keywords),
            "language_match_rate": round(lmr, 3),
            "refusal_correctness": round(rc, 3) if rc is not None else None,
            "refusal_questions": len(refusal_expected),
            "avg_latency_sec": round(lat_mean, 2) if lat_mean is not None else None,
            "errors": errors,
        }

    return {
        "overall": aggregate(results),
        "by_category": {cat: aggregate(bucket) for cat, bucket in sorted(by_category.items())},
    }


# Обработка одного вопроса

def process_question(q: dict[str, Any]) -> TestResult:
    answer, latency, error = call_chat_api(q["question"])
    answer = answer or ""

    answer_language = detect_response_language(answer)
    language_match = (answer_language == q["language"]) if answer else False

    expected_keywords = q.get("expected_keywords") or []
    khr = keyword_hit_rate(answer, expected_keywords)

    refusal_expected = (
        q.get("expected_answer_refusal", False)
        or q.get("category") == "attractions_weak"
    )
    refused = is_refusal(answer, q["language"])
    refusal_correct = (refused == refusal_expected) if refusal_expected else not refused
    # - если ожидался отказ — правильно если отказался
    # - если НЕ ожидался отказ — правильно если НЕ отказался (т.е. попытался ответить)

    return TestResult(
        id=q["id"],
        question=q["question"],
        language=q["language"],
        category=q.get("category", "unknown"),
        expected_keywords=expected_keywords,
        answer=answer,
        latency_sec=latency,
        error=error,
        answer_language=answer_language,
        language_match=language_match,
        keyword_hit_rate=khr,
        is_refusal=refused,
        refusal_expected=refusal_expected,
        refusal_correct=refusal_correct,
    )


# Главный цикл

def load_questions(path: Path, limit: int | None, categories: list[str] | None) -> list[dict]:
    questions = []
    with path.open(encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                q = json.loads(line)
            except json.JSONDecodeError as e:
                logger.error("Битая JSON строка %d: %s", line_num, e)
                continue
            if categories and q.get("category") not in categories:
                continue
            questions.append(q)
            if limit and len(questions) >= limit:
                break
    return questions


def print_summary(metrics: dict[str, Any]) -> None:
    print("\n" + "=" * 78)
    print("СВОДНЫЕ МЕТРИКИ BASELINE")
    print("=" * 78)

    overall = metrics["overall"]
    print(f"\nОбщее количество вопросов: {overall['count']}")
    print(f"Ошибок API: {overall['errors']}")
    print(f"Средняя latency: {overall['avg_latency_sec']}s" if overall["avg_latency_sec"] else "")

    def fmt(x):
        return f"{x:.1%}" if isinstance(x, float) else "—"

    print("\n{:<25} {:>10} {:>12} {:>12} {:>14} {:>10}".format(
        "Категория", "кол-во", "keyword_hit", "lang_match", "refusal_corr", "latency"
    ))
    print("-" * 78)

    for cat, m in metrics["by_category"].items():
        print("{:<25} {:>10} {:>12} {:>12} {:>14} {:>10}".format(
            cat,
            m["count"],
            fmt(m["keyword_hit_rate"]),
            fmt(m["language_match_rate"]),
            fmt(m["refusal_correctness"]),
            f"{m['avg_latency_sec']}s" if m["avg_latency_sec"] else "—",
        ))

    print("-" * 78)
    print("{:<25} {:>10} {:>12} {:>12} {:>14} {:>10}".format(
        "ОБЩЕЕ",
        overall["count"],
        fmt(overall["keyword_hit_rate"]),
        fmt(overall["language_match_rate"]),
        fmt(overall["refusal_correctness"]),
        f"{overall['avg_latency_sec']}s" if overall["avg_latency_sec"] else "—",
    ))
    print("=" * 78)


def main() -> int:
    parser = argparse.ArgumentParser(description="Baseline evaluation для SkyAssist")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT,
                        help=f"JSONL с тестами (default: {DEFAULT_INPUT})")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help=f"JSON с результатами (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--limit", type=int, default=None,
                        help="Ограничить количество вопросов (для отладки)")
    parser.add_argument("--categories", type=str, nargs="+", default=None,
                        help="Фильтр по категориям (например: flight attractions)")
    args = parser.parse_args()

    # Проверка работы сервера
    try:
        requests.get(API_URL.replace("/chat", "/health"), timeout=5)
    except Exception as e:
        logger.warning("Проверка /health не прошла (%s). Пробую продолжить...", e)

    questions = load_questions(args.input, args.limit, args.categories)
    if not questions:
        logger.error("Не нашёл вопросов в %s", args.input)
        return 1

    logger.info("Загружено %d вопросов. Начинаю прогон...", len(questions))
    results: list[TestResult] = []

    t_start = time.perf_counter()
    for i, q in enumerate(questions, 1):
        logger.info("[%d/%d] %s (%s, %s)", i, len(questions), q["id"], q["language"], q.get("category"))
        result = process_question(q)
        results.append(result)

        if result.error:
            logger.warning("  X %s", result.error)
        else:
            lang_ok = "✓" if result.language_match else "✗"
            khr_str = f"keywords={result.keyword_hit_rate:.0%}" if result.keyword_hit_rate is not None else "keywords=—"
            refusal_str = "refused" if result.is_refusal else "answered"
            logger.info("  ✓ lang=%s %s %s (%.1fs)", lang_ok, khr_str, refusal_str, result.latency_sec or 0)

        # Промежуточное сохранение
        if i % SAVE_EVERY == 0:
            interim_metrics = compute_metrics(results)
            save_results(results, args.output, interim_metrics)
            logger.info("  📝 промежуточное сохранение (%d/%d)", i, len(questions))

    t_total = time.perf_counter() - t_start
    logger.info("Прогон закончен за %.1f сек", t_total)

    # Финальные метрики
    metrics = compute_metrics(results)
    save_results(results, args.output, metrics)
    logger.info("Результаты сохранены в %s", args.output)

    print_summary(metrics)
    return 0


if __name__ == "__main__":
    sys.exit(main())