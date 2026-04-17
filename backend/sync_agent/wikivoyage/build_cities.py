import argparse
import json
import logging
import shutil
import sys
import time
from pathlib import Path

from backend.sync_agent.wikivoyage.cities_config import CITIES
from backend.sync_agent.wikivoyage.fetcher import (
    WIKIPEDIA_API,
    WIKIVOYAGE_API,
    fetch_wikipedia,
    fetch_wikivoyage,
)
from backend.sync_agent.wikivoyage.wikivoyage_parser import (
    parse_wikipedia_fallback,
    parse_wikivoyage_article,
)

logger = logging.getLogger("skyassist.wikivoyage.build")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

KNOWLEDGE_BASE_DIR = Path("data/knowledge_base/cities")
BACKUP_DIR = Path("data/knowledge_base/cities_old")
REPORT_PATH = KNOWLEDGE_BASE_DIR / "_build_report.json"

MIN_CONTENT_CHARS = 500


def _wikivoyage_url(page_title: str) -> str:
    return f"https://en.wikivoyage.org/wiki/{page_title.replace(' ', '_')}"


def _wikipedia_url(page_title: str) -> str:
    return f"https://en.wikipedia.org/wiki/{page_title.replace(' ', '_')}"


def _build_one_city(city_config: dict) -> tuple[dict | None, str]:
    city_ru = city_config["city_ru"]
    iata = city_config["iata"]
    country_ru = city_config["country_ru"]
    wv_title = city_config["wikivoyage_en"]
    wp_title = city_config["wikipedia_fallback_en"]

    # Попытка Wikivoyage
    wv_text = fetch_wikivoyage(wv_title)
    if wv_text:
        doc = parse_wikivoyage_article(
            wikitext=wv_text,
            city_ru=city_ru,
            iata=iata,
            country_ru=country_ru,
            source_url=_wikivoyage_url(wv_title),
        )
        if doc and "_redirect_to" in doc:
            new_title = doc["_redirect_to"]
            logger.info("Вторая попытка: %s → %s", wv_title, new_title)
            wv_text = fetch_wikivoyage(new_title)
            if wv_text:
                doc = parse_wikivoyage_article(
                    wikitext=wv_text,
                    city_ru=city_ru,
                    iata=iata,
                    country_ru=country_ru,
                    source_url=_wikivoyage_url(new_title),
                )

        if doc and "_redirect_to" not in doc:
            content_len = len(doc.get("content", ""))
            if content_len >= MIN_CONTENT_CHARS:
                return doc, "wikivoyage"
            logger.info(
                "Wikivoyage для %s слишком короткий (%d симв), fallback на Wikipedia",
                city_ru, content_len,
            )
        else:
            logger.info("Wikivoyage: нет пригодного контента для %s", city_ru)
    else:
        logger.info("Wikivoyage: страница %s не получена", wv_title)

    # Fallback Wikipedia
    wp_text = fetch_wikipedia(wp_title)
    if wp_text:
        doc = parse_wikipedia_fallback(
            wikitext=wp_text,
            city_ru=city_ru,
            iata=iata,
            country_ru=country_ru,
            source_url=_wikipedia_url(wp_title),
        )
        if doc and len(doc.get("content", "")) >= MIN_CONTENT_CHARS:
            return doc, "wikipedia"

    return None, "error"


def _backup_existing(iata: str) -> None:
    src = KNOWLEDGE_BASE_DIR / f"{iata.lower()}.json"
    if not src.exists():
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dst = BACKUP_DIR / f"{iata.lower()}.json"
    shutil.copy2(src, dst)
    logger.debug("Backup: %s → %s", src, dst)


def build_all(only_iata: str | None = None, dry_run: bool = False) -> None:
    KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)

    cities = CITIES
    if only_iata:
        cities = [c for c in CITIES if c["iata"].upper() == only_iata.upper()]
        if not cities:
            logger.error("Город с IATA=%s не найден в cities_config", only_iata)
            sys.exit(1)

    logger.info("Начинаем парсинг %d городов (dry_run=%s)", len(cities), dry_run)
    report = {
        "total": len(cities),
        "wikivoyage": 0,
        "wikipedia": 0,
        "errors": 0,
        "per_city": [],
    }

    start = time.time()
    for i, city in enumerate(cities, 1):
        logger.info("[%d/%d] %s (%s)", i, len(cities), city["city_ru"], city["iata"])
        doc, source = _build_one_city(city)

        entry = {
            "city": city["city_ru"],
            "iata": city["iata"],
            "source": source,
            "content_len": len(doc.get("content", "")) if doc else 0,
            "has_practical_info": bool(doc and doc.get("practical_info")),
        }
        report["per_city"].append(entry)

        if not doc:
            report["errors"] += 1
            logger.error("  ✗ не удалось получить контент")
            continue

        report[source] += 1
        logger.info(
            "  ✓ %s: %d симв, practical_info=%s",
            source, entry["content_len"], entry["has_practical_info"],
        )

        if not dry_run:
            _backup_existing(city["iata"])
            out_path = KNOWLEDGE_BASE_DIR / f"{city['iata'].lower()}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - start
    logger.info(
        "Готово за %.1f сек: wikivoyage=%d, wikipedia=%d, errors=%d",
        elapsed, report["wikivoyage"], report["wikipedia"], report["errors"],
    )

    if not dry_run:
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info("Отчёт: %s", REPORT_PATH)


def main():
    parser = argparse.ArgumentParser(description="Build cities knowledge base from Wikivoyage")
    parser.add_argument("--only", metavar="IATA",
                        help="Обработать только один город (по IATA)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Не писать файлы, только отчёт в лог")
    args = parser.parse_args()

    build_all(only_iata=args.only, dry_run=args.dry_run)


if __name__ == "__main__":
    main()