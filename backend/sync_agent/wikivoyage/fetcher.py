import logging
import time
from typing import Optional

import requests

logger = logging.getLogger("skyassist.wikivoyage.fetcher")

USER_AGENT = "SkyAssist-Thesis/1.0 (educational project; contact via repository)"
REQUEST_TIMEOUT = 30  # секунд
THROTTLE_SECONDS = 1.0  # пауза между запросами

WIKIVOYAGE_API = "https://en.wikivoyage.org/w/api.php"
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"


def _fetch_wikitext(api_url: str, page_title: str) -> Optional[str]:
    params = {
        "action": "parse",
        "page": page_title,
        "prop": "wikitext",
        "format": "json",
        "redirects": 1,
        "formatversion": 2,
    }
    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(
            api_url, params=params, headers=headers, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        logger.warning("HTTP ошибка при запросе %s: %s", page_title, e)
        return None

    if "error" in data:
        logger.warning(
            "API ошибка для %s: %s", page_title, data["error"].get("info", "?")
        )
        return None

    parse_block = data.get("parse")
    if not parse_block:
        logger.warning("Пустой ответ API для %s", page_title)
        return None

    wikitext = parse_block.get("wikitext")
    if not wikitext:
        logger.warning("Нет поля wikitext для %s", page_title)
        return None

    # formatversion=2 возвращает строку напрямую; v1 возвращает {"*": "..."}
    if isinstance(wikitext, dict):
        wikitext = wikitext.get("*", "")

    resolved_title = parse_block.get("title", page_title)
    if resolved_title != page_title:
        logger.info("Редирект: %s → %s", page_title, resolved_title)

    return wikitext


def fetch_wikivoyage(page_title: str) -> Optional[str]:
    logger.info("Wikivoyage: %s", page_title)
    text = _fetch_wikitext(WIKIVOYAGE_API, page_title)
    time.sleep(THROTTLE_SECONDS)
    return text


def fetch_wikipedia(page_title: str) -> Optional[str]:
    logger.info("Wikipedia fallback: %s", page_title)
    text = _fetch_wikitext(WIKIPEDIA_API, page_title)
    time.sleep(THROTTLE_SECONDS)
    return text