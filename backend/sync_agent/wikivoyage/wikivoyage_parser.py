import logging
import re
from typing import Optional

import mwparserfromhell

logger = logging.getLogger("skyassist.wikivoyage.parser")

# Шаблоны-листинги, из которых извлекаем читаемый текст
LISTING_TEMPLATES = {
    "listing", "see", "do", "eat", "drink", "buy", "sleep", "go",
    "marker", "destination", "city", "region",
    # Некоторые статьи используют вариации
    "restaurant", "hotel", "attraction",
}

#  Секции, которые идут в content
CONTENT_SECTIONS = {
    "understand", "see", "do", "eat", "drink", "buy",
    "itineraries", "highlights",
}

# Секции, которые идут в practical_info с указанными ключами
PRACTICAL_SECTIONS = {
    "get in": "get_in",
    "get around": "get_around",
    "stay safe": "stay_safe",
    "stay healthy": "stay_healthy",
}

# Секции, которые игнорируем (реклама, мета, внешние ссылки)
IGNORED_SECTIONS = {
    "respect", "talk", "cope", "connect", "go next",
    "see also", "external links", "references", "further reading",
    "contents",
}

# Человекочитаемые заголовки для content
SECTION_HEADERS_RU = {
    "_lead": "",  # lead без заголовка
    "understand": "О городе",
    "see": "Достопримечательности",
    "do": "Чем заняться",
    "eat": "Рестораны и кухня",
    "drink": "Напитки",
    "buy": "Шопинг",
}


def _is_redirect(wikitext: str) -> Optional[str]:
    match = re.match(r"\s*#REDIRECT\s*\[\[([^\]|#]+)", wikitext, re.IGNORECASE)
    return match.group(1).strip() if match else None


def _is_disambiguation(wikicode) -> bool:
    for template in wikicode.filter_templates():
        name = str(template.name).strip().lower()
        if "disambig" in name or "disamb" in name:
            return True
    return False


def _split_level2_sections(wikitext: str) -> dict[str, str]:
    pattern = re.compile(r"^==([^=].*?)==\s*$", re.MULTILINE)
    sections: dict[str, str] = {}
    matches = list(pattern.finditer(wikitext))

    if not matches:
        text = wikitext.strip()
        if text:
            sections["_lead"] = text
        return sections

    lead = wikitext[: matches[0].start()].strip()
    if lead:
        sections["_lead"] = lead

    for i, m in enumerate(matches):
        section_name = m.group(1).strip().lower()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(wikitext)
        body = wikitext[start:end].strip()
        if body:
            sections[section_name] = body

    return sections


def _render_listing_template(template) -> str:
    parts = []
    if template.has("name"):
        parts.append(str(template.get("name").value).strip())
    if template.has("alt"):
        alt = str(template.get("alt").value).strip()
        if alt:
            parts.append(f"({alt})")
    # Описание может лежать под content или description
    description = None
    for key in ("content", "description"):
        if template.has(key):
            val = str(template.get(key).value).strip()
            if val:
                description = val
                break
    if description:
        parts.append("— " + description)
    if template.has("address"):
        addr = str(template.get("address").value).strip()
        if addr:
            parts.append(f"[{addr}]")
    return " ".join(parts) + ". " if parts else ""


def _clean_wikitext(raw: str) -> str:
    parsed = mwparserfromhell.parse(raw)

    # Обработка шаблонов.
    for template in list(parsed.filter_templates(recursive=False)):
        name = str(template.name).strip().lower()
        try:
            if name in LISTING_TEMPLATES:
                replacement = _render_listing_template(template)
                parsed.replace(template, replacement)
            else:
                # Все прочие шаблоны удаляются (pagebanner, climate, isPartOf, geo, ...)
                parsed.remove(template)
        except ValueError:
            # Шаблон уже не в дереве (вложенное удаление) — пропуск
            continue

    # Комментарии удаляются явно
    for comment in list(parsed.filter_comments()):
        try:
            parsed.remove(comment)
        except ValueError:
            continue

    text = parsed.strip_code(normalize=True, collapse=True)
    # Остатки от картинок: "thumb|350px|описание" или "thumb | 300px | описание"
    text = re.sub(r"thumb\s*\|\s*(?:\d+px\s*\|\s*)?", "", text)
    # Пустые скобки от удалённых wikilinks: "Airport () — chief"
    text = re.sub(r"\(\s*\)", "", text)

    # Схлопывание пустых строк и лишних пробелов
    lines = [line.strip() for line in text.split("\n")]
    lines = [line for line in lines if line]
    text = "\n".join(lines)

    # Несколько подряд идущих пробелов → один
    text = re.sub(r" {2,}", " ", text)

    # Двойные точки/тройные → одна (возникают при рендере шаблонов,
    # чьё content уже заканчивалось точкой)
    text = re.sub(r"\.{2,}", ".", text)

    return text.strip()


def parse_wikivoyage_article(
    wikitext: str,
    city_ru: str,
    iata: str,
    country_ru: str,
    source_url: str,
) -> Optional[dict]:
    if not wikitext or not wikitext.strip():
        logger.warning("Пустой викитекст для %s", city_ru)
        return None

    redirect_target = _is_redirect(wikitext)
    if redirect_target:
        logger.info("Страница %s — редирект на '%s'", city_ru, redirect_target)
        return {"_redirect_to": redirect_target}

    wikicode = mwparserfromhell.parse(wikitext)
    if _is_disambiguation(wikicode):
        logger.info("Страница %s — disambig", city_ru)
        return None

    raw_sections = _split_level2_sections(wikitext)
    if not raw_sections:
        logger.warning("В %s не найдено секций уровня 2", city_ru)
        return None

    # Сборка content (связный описательный текст)
    content_parts: list[str] = []
    practical_info: dict[str, str] = {}

    # Lead идёт первым
    if "_lead" in raw_sections:
        lead_clean = _clean_wikitext(raw_sections["_lead"])
        if lead_clean:
            content_parts.append(lead_clean)

    # Обычные секции
    for section_name, raw in raw_sections.items():
        if section_name == "_lead":
            continue
        if section_name in IGNORED_SECTIONS:
            continue

        cleaned = _clean_wikitext(raw)
        if not cleaned:
            continue

        if section_name in CONTENT_SECTIONS:
            header = SECTION_HEADERS_RU.get(section_name, section_name.capitalize())
            if header:
                content_parts.append(f"{header}.\n{cleaned}")
            else:
                content_parts.append(cleaned)
        elif section_name in PRACTICAL_SECTIONS:
            key = PRACTICAL_SECTIONS[section_name]
            practical_info[key] = cleaned

    content = "\n\n".join(content_parts).strip()

    if not content and not practical_info:
        logger.warning("Для %s не извлечено ни content, ни practical_info", city_ru)
        return None

    document = {
        "title": f"{city_ru} ({iata})",
        "category": "destination",
        "language": "en",
        "city": city_ru,
        "iata": iata,
        "country": country_ru,
        "source": "wikivoyage",
        "source_url": source_url,
        "content": content,
    }
    if practical_info:
        document["practical_info"] = practical_info

    return document


def parse_wikipedia_fallback(
    wikitext: str,
    city_ru: str,
    iata: str,
    country_ru: str,
    source_url: str,
) -> Optional[dict]:
    if not wikitext or not wikitext.strip():
        return None

    if _is_redirect(wikitext):
        # Редиректы Wikipedia обрабатываются через API-параметр redirects=1
        return None

    wikicode = mwparserfromhell.parse(wikitext)
    if _is_disambiguation(wikicode):
        return None

    raw_sections = _split_level2_sections(wikitext)
    content_parts: list[str] = []

    # Для Wikipedia в приоритете lead + история + культура + достопримечательности
    wanted_sections = {
        "_lead",
        "history",
        "geography",
        "climate",
        "culture",
        "tourism",
        "landmarks",
        "sights",
        "architecture",
        "transport",
        "transportation",
    }

    for section_name, raw in raw_sections.items():
        if section_name not in wanted_sections:
            continue
        cleaned = _clean_wikitext(raw)
        if not cleaned:
            continue
        header = "" if section_name == "_lead" else section_name.capitalize() + "."
        content_parts.append(f"{header}\n{cleaned}" if header else cleaned)

    content = "\n\n".join(content_parts).strip()
    if not content:
        return None

    return {
        "title": f"{city_ru} ({iata})",
        "category": "destination",
        "language": "en",
        "city": city_ru,
        "iata": iata,
        "country": country_ru,
        "source": "wikipedia",
        "source_url": source_url,
        "content": content,
    }