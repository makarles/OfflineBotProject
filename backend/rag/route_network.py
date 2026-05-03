from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_AEROLINE_FULL_PATH = Path("data/knowledge_base/aeroline_full.json")

NON_ROUTE_KEYWORDS = [
    "багаж",
    "ручная кладь",
    "чемодан",
    "сверхнорматив",
    "сверхнормативный багаж",
    "дополнительный килограмм",
    "дополнительное место",
    "стоимость",
    "стоит",
    "оплатить",
    "доплата",
    "перевозка",
    "провоз",
    "животное",
    "животных",
    "кошка",
    "кот",
    "собака",
    "питомец",
    "мопс",
    "бульдог",
    "спортинвентарь",
    "спортивный инвентарь",
    "велосипед",
    "лыжи",
    "сноуборд",
    "удочка",
    "удочки",
    "музыкальный инструмент",
    "гитара",
    "скрипка",
    "виолончель",
    "контрабас",
    "саксофон",
    "флейта",
    "пауэрбанк",
    "powerbank",
    "аккумулятор",
    "батарея",
    "жидкость",
    "жидкости",
    "нож",
    "ножницы",
    "зажигалка",
    "коляска",
    "детская коляска",
    "ценные вещи",
    "хрупкий багаж",

    "baggage",
    "luggage",
    "carry-on",
    "carry on",
    "hand luggage",
    "cabin baggage",
    "checked baggage",
    "suitcase",
    "overweight",
    "excess baggage",
    "extra baggage",
    "extra bag",
    "additional baggage",
    "additional bag",
    "additional kilogram",
    "extra kilogram",
    "fee",
    "fees",
    "cost",
    "price",
    "pay",
    "payment",
    "surcharge",
    "transportation",
    "carriage",
    "allowance",

    "animal",
    "animals",
    "pet",
    "pets",
    "cat",
    "dog",
    "service dog",
    "guide dog",
    "pug",
    "bulldog",
    "brachycephalic",

    "sports equipment",
    "sport equipment",
    "ski",
    "skis",
    "snowboard",
    "golf clubs",
    "fishing rod",
    "fishing rods",
    "bicycle",
    "bike",

    "musical instrument",
    "musical instruments",
    "violin",
    "flute",
    "cello",
    "double bass",
    "guitar",
    "saxophone",
    "fragile",

    "power bank",
    "powerbank",
    "battery",
    "batteries",
    "lithium battery",
    "lithium batteries",
    "lithium-ion",
    "wh",
    "watt-hour",
    "watt hours",

    "liquid",
    "liquids",
    "water bottle",
    "bottle",
    "knife",
    "knives",
    "scissors",
    "lighter",
    "weapon",
    "weapons",

    "stroller",
    "baby stroller",
    "pushchair",
    "valuable items",
    "valuables",
    "fragile baggage",
]

ROUTE_KEYWORDS_RU = [
    "куда летает",
    "куда мы летаем",
    "в какие города",
    "какие города",
    "городов из маршрутной сети",
    "города из маршрутной сети",
    "маршрутная сеть",
    "маршрутной сети",
    "направления",
    "направление",
    "маршруты",
    "маршрут",
    "рейсы aeroline",
    "рейсы авиакомпании",
    "рейсы в",
    "рейсы до",
    "летает в",
    "летает ли",
    "есть ли рейсы",
    "есть рейсы",
    "международные",
    "международные направления",
    "международные маршруты",
    "международные рейсы",
    "междунарожные направления",
    "междунарожные",
    "внутренние",
    "внутренние маршруты",
    "внутренние направления",
    "внутренние рейсы",
    "внутрироссийские",
    "внутрироссийские маршруты",
    "внутрироссийские направления",
]

ROUTE_KEYWORDS_EN = [
    "where does aeroline fly",
    "where do you fly",
    "which cities",
    "what cities",
    "route network",
    "destinations",
    "destination",
    "routes",
    "route",
    "flights to",
    "flights from",
    "does aeroline fly",
    "does it fly",
    "do you fly",
    "are there flights",
    "international destinations",
    "international routes",
    "international flights",
    "domestic destinations",
    "domestic routes",
    "domestic flights",
    "within russia",
    "russian destinations",
]

AIRLINE_CONTEXT_KEYWORDS_RU = [
    "aeroline",
    "аэролайн",
    "авиакомпани",
    "компани",
    "летает",
    "летаем",
    "маршрут",
    "направлен",
    "рейс",
    "рейсы",
]

AIRLINE_CONTEXT_KEYWORDS_EN = [
    "aeroline",
    "airline",
    "company",
    "fly",
    "flies",
    "flying",
    "flight",
    "flights",
    "route",
    "routes",
    "destination",
    "destinations",
]

ROUTE_INTENT_WORDS_RU = [
    "город",
    "города",
    "страна",
    "страны",
    "куда",
    "международ",
    "междунарож",
    "внутрен",
    "внутрироссий",
    "направлен",
    "маршрут",
    "рейс",
    "рейсы",
    "летает",
]

ROUTE_INTENT_WORDS_EN = [
    "city",
    "cities",
    "country",
    "countries",
    "where",
    "international",
    "domestic",
    "destination",
    "destinations",
    "route",
    "routes",
    "flight",
    "flights",
    "fly",
    "flies",
]

CURRENT_FLIGHT_KEYWORDS = [
    "какой у нас рейс",
    "какой наш рейс",
    "какой мой рейс",
    "какой рейс",
    "номер рейса",
    "какой номер рейса",
    "наш рейс",
    "мой рейс",
    "текущий рейс",
    "информация о рейсе",
    "куда мы летим",
    "куда летим",
    "откуда мы летим",
    "во сколько вылет",
    "во сколько прилет",
    "время вылета",
    "время прилета",
    "время прилёта",
    "когда вылет",
    "когда прилет",
    "когда прилёт",

    "what is our flight",
    "what flight is this",
    "what is my flight",
    "flight number",
    "what is the flight number",
    "our flight",
    "my flight",
    "current flight",
    "flight information",
    "where are we flying",
    "where are we going",
    "where do we fly",
    "where are we flying to",
    "when do we depart",
    "departure time",
    "arrival time",
]

COUNTRY_ALIASES = {
    "оаэ": ["ОАЭ"],
    "эмираты": ["ОАЭ"],
    "объединенные арабские эмираты": ["ОАЭ"],
    "объединённые арабские эмираты": ["ОАЭ"],
    "uae": ["ОАЭ"],
    "united arab emirates": ["ОАЭ"],
    "emirates": ["ОАЭ"],
    "таиланд": ["Таиланд"],
    "тайланд": ["Таиланд"],
    "thailand": ["Таиланд"],
    "казахстан": ["Казахстан"],
    "kazakhstan": ["Казахстан"],
    "турция": ["Турция"],
    "turkey": ["Турция"],
    "египет": ["Египет"],
    "egypt": ["Египет"],
    "индия": ["Индия"],
    "india": ["Индия"],
    "узбекистан": ["Узбекистан"],
    "uzbekistan": ["Узбекистан"],
    "кыргызстан": ["Кыргызстан"],
    "киргизия": ["Кыргызстан"],
    "kyrgyzstan": ["Кыргызстан"],
    "азербайджан": ["Азербайджан"],
    "azerbaijan": ["Азербайджан"],
    "армения": ["Армения"],
    "armenia": ["Армения"],
    "беларусь": ["Беларусь"],
    "belarus": ["Беларусь"],
    "грузия": ["Грузия"],
    "georgia": ["Грузия"],
    "китай": ["Китай"],
    "china": ["Китай"],
    "индонезия": ["Индонезия"],
    "indonesia": ["Индонезия"],
    "малайзия": ["Малайзия"],
    "malaysia": ["Малайзия"],
    "мальдивы": ["Мальдивы"],
    "maldives": ["Мальдивы"],
    "непал": ["Непал"],
    "nepal": ["Непал"],
    "шри-ланка": ["Шри-Ланка"],
    "sri lanka": ["Шри-Ланка"],
}

KNOWN_ABSENT_DESTINATIONS = {
    "париж": {"ru": "Париж", "en": "Paris"},
    "paris": {"ru": "Париж", "en": "Paris"},
    "лондон": {"ru": "Лондон", "en": "London"},
    "london": {"ru": "Лондон", "en": "London"},
    "берлин": {"ru": "Берлин", "en": "Berlin"},
    "berlin": {"ru": "Берлин", "en": "Berlin"},
    "рим": {"ru": "Рим", "en": "Rome"},
    "rome": {"ru": "Рим", "en": "Rome"},
    "мадрид": {"ru": "Мадрид", "en": "Madrid"},
    "madrid": {"ru": "Мадрид", "en": "Madrid"},
    "нью-йорк": {"ru": "Нью-Йорк", "en": "New York"},
    "new york": {"ru": "Нью-Йорк", "en": "New York"},
    "токио": {"ru": "Токио", "en": "Tokyo"},
    "tokyo": {"ru": "Токио", "en": "Tokyo"},
}

CITY_TRANSLATIONS = {
    "Владивосток": "Vladivostok",
    "Воронеж": "Voronezh",
    "Екатеринбург": "Yekaterinburg",
    "Иркутск": "Irkutsk",
    "Казань": "Kazan",
    "Калининград": "Kaliningrad",
    "Краснодар": "Krasnodar",
    "Красноярск": "Krasnoyarsk",
    "Мурманск": "Murmansk",
    "Нижний Новгород": "Nizhny Novgorod",
    "Новосибирск": "Novosibirsk",
    "Омск": "Omsk",
    "Пермь": "Perm",
    "Ростов-на-Дону": "Rostov-on-Don",
    "Самара": "Samara",
    "Санкт-Петербург": "Saint Petersburg",
    "Сочи": "Sochi",
    "Тюмень": "Tyumen",
    "Уфа": "Ufa",
    "Хабаровск": "Khabarovsk",
    "Абу-Даби": "Abu Dhabi",
    "Алматы": "Almaty",
    "Анталья": "Antalya",
    "Астана": "Astana",
    "Баку": "Baku",
    "Бангкок": "Bangkok",
    "Бишкек": "Bishkek",
    "Гоа": "Goa",
    "Дели": "Delhi",
    "Денпасар": "Denpasar",
    "Дубай": "Dubai",
    "Ереван": "Yerevan",
    "Катманду": "Kathmandu",
    "Коломбо": "Colombo",
    "Куала-Лумпур": "Kuala Lumpur",
    "Мале": "Male",
    "Минск": "Minsk",
    "Пекин": "Beijing",
    "Пхукет": "Phuket",
    "Самарканд": "Samarkand",
    "Стамбул": "Istanbul",
    "Ташкент": "Tashkent",
    "Тбилиси": "Tbilisi",
    "Хургада": "Hurghada",
    "Шарм-эш-Шейх": "Sharm El Sheikh",
}

COUNTRY_TRANSLATIONS = {
    "ОАЭ": "UAE",
    "Казахстан": "Kazakhstan",
    "Турция": "Turkey",
    "Азербайджан": "Azerbaijan",
    "Таиланд": "Thailand",
    "Кыргызстан": "Kyrgyzstan",
    "Индия": "India",
    "Индонезия": "Indonesia",
    "Армения": "Armenia",
    "Непал": "Nepal",
    "Шри-Ланка": "Sri Lanka",
    "Малайзия": "Malaysia",
    "Мальдивы": "Maldives",
    "Беларусь": "Belarus",
    "Китай": "China",
    "Узбекистан": "Uzbekistan",
    "Грузия": "Georgia",
    "Египет": "Egypt",
}


def _is_current_flight_question(query: str) -> bool:
    q = normalize_query(query)

    return any(keyword in q for keyword in CURRENT_FLIGHT_KEYWORDS)


def normalize_query(text: str) -> str:
    return text.lower().replace("ё", "е").strip()


def detect_query_language(query: str) -> str:
    q = normalize_query(query)

    cyrillic_count = len(re.findall(r"[а-я]", q))
    latin_count = len(re.findall(r"[a-z]", q))

    if latin_count > cyrillic_count:
        return "en"

    return "ru"


def load_aeroline_full_doc(path: Path = DEFAULT_AEROLINE_FULL_PATH) -> dict[str, Any]:
    if not path.exists():
        logger.warning("Файл с маршрутной сетью не найден: %s", path)
        return {}

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Не удалось прочитать %s: %s", path, exc)
        return {}

    if not isinstance(data, dict):
        logger.warning("Файл %s должен содержать JSON-объект", path)
        return {}

    return data


def extract_route_text(doc: dict[str, Any]) -> dict[str, str]:
    practical_routes = doc.get("practical_info", {}).get("routes", {})

    summary = str(practical_routes.get("summary", "") or "").strip()
    domestic = str(practical_routes.get("domestic", "") or "").strip()
    international = str(practical_routes.get("international", "") or "").strip()

    content = str(doc.get("content", "") or "")

    if not summary:
        match = re.search(
            r"Авиакомпания выполняет рейсы по .*?\.",
            content,
            flags=re.IGNORECASE | re.DOTALL,
        )
        summary = match.group(0).strip() if match else ""

    if not domestic:
        match = re.search(
            r"Внутрироссийские направления из Москвы:\s*(.*?)(?:\n\n|$)",
            content,
            flags=re.IGNORECASE | re.DOTALL,
        )
        domestic = match.group(1).strip() if match else ""

    if not international:
        match = re.search(
            r"Международные направления из Москвы:\s*(.*?)(?:\n\n|$)",
            content,
            flags=re.IGNORECASE | re.DOTALL,
        )
        international = match.group(1).strip() if match else ""

    return {
        "summary": summary,
        "domestic": domestic,
        "international": international,
    }


def split_cities(value: str) -> list[str]:
    if not value:
        return []

    normalized = " ".join(value.split())

    return [
        item.strip().strip(".")
        for item in re.split(r"(?<=\))\s*,\s*", normalized)
        if item.strip()
    ]


def _load_routes(path: Path = DEFAULT_AEROLINE_FULL_PATH) -> tuple[str, list[str], list[str]]:
    doc = load_aeroline_full_doc(path)
    if not doc:
        return "", [], []

    routes = extract_route_text(doc)

    summary = routes.get("summary", "")
    domestic = split_cities(routes.get("domestic", ""))
    international = split_cities(routes.get("international", ""))

    return summary, domestic, international


def _city_name(item: str) -> str:
    return item.split("(", 1)[0].strip()


def _country_name(item: str) -> str | None:
    match = re.search(r"\(([^()]*)\)$", item)
    if not match:
        return None

    inside = match.group(1)
    parts = [part.strip() for part in inside.split(",")]

    if len(parts) >= 2:
        return parts[-1]

    return None


def _translate_city_name(city: str, lang: str) -> str:
    if lang != "en":
        return city

    return CITY_TRANSLATIONS.get(city, city)


def _translate_country_name(country: str | None, lang: str) -> str | None:
    if country is None:
        return None

    if lang != "en":
        return country

    return COUNTRY_TRANSLATIONS.get(country, country)


def _format_destination(item: str, lang: str) -> str:
    if lang != "en":
        return item

    city = _city_name(item)
    translated_city = _translate_city_name(city, lang)

    code_match = re.search(r"\(([^()]*)\)", item)
    if not code_match:
        return translated_city

    inside = code_match.group(1)
    parts = [part.strip() for part in inside.split(",")]

    if len(parts) >= 2:
        code = parts[0]
        country = _translate_country_name(parts[-1], lang)
        return f"{translated_city} ({code}, {country})"

    return f"{translated_city} ({inside})"


def _all_destinations(path: Path = DEFAULT_AEROLINE_FULL_PATH) -> list[str]:
    _, domestic, international = _load_routes(path)
    return domestic + international


def _has_known_destination_mention(query: str, path: Path = DEFAULT_AEROLINE_FULL_PATH) -> bool:
    q = normalize_query(query)
    destinations = _all_destinations(path)

    for item in destinations:
        city = normalize_query(_city_name(item))
        country = _country_name(item)

        translated_city = normalize_query(CITY_TRANSLATIONS.get(_city_name(item), ""))
        translated_country = normalize_query(COUNTRY_TRANSLATIONS.get(country or "", ""))

        if city and city in q:
            return True

        if translated_city and translated_city in q:
            return True

        if country and normalize_query(country) in q:
            return True

        if translated_country and translated_country in q:
            return True

    for alias in COUNTRY_ALIASES:
        if alias in q:
            return True

    return any(destination in q for destination in KNOWN_ABSENT_DESTINATIONS)


def is_route_network_question(query: str) -> bool:
    q = normalize_query(query)

    if _is_current_flight_question(query):
        return False

    if any(keyword in q for keyword in NON_ROUTE_KEYWORDS):
        return False

    direct_match_ru = any(keyword in q for keyword in ROUTE_KEYWORDS_RU)
    direct_match_en = any(keyword in q for keyword in ROUTE_KEYWORDS_EN)

    contextual_match_ru = (
        any(keyword in q for keyword in AIRLINE_CONTEXT_KEYWORDS_RU)
        and any(word in q for word in ROUTE_INTENT_WORDS_RU)
    )

    contextual_match_en = (
        any(keyword in q for keyword in AIRLINE_CONTEXT_KEYWORDS_EN)
        and any(word in q for word in ROUTE_INTENT_WORDS_EN)
    )

    destination_match = (
        any(keyword in q for keyword in [
            "летает",
            "рейс",
            "рейсы",
            "направлен",
            "fly",
            "flies",
            "flight",
            "flights",
            "destination",
            "destinations",
        ])
        and _has_known_destination_mention(query)
    )

    return (
        direct_match_ru
        or direct_match_en
        or contextual_match_ru
        or contextual_match_en
        or destination_match
    )


def _wants_domestic(query: str) -> bool:
    q = normalize_query(query)

    return any(word in q for word in [
        "внутрен",
        "внутрироссий",
        "по россии",
        "российск",
        "domestic",
        "within russia",
        "russian destinations",
    ])


def _wants_international(query: str) -> bool:
    q = normalize_query(query)

    return any(word in q for word in [
        "международ",
        "междунарож",
        "зарубеж",
        "за границ",
        "international",
        "abroad",
        "foreign",
    ])


def _wants_count(query: str) -> bool:
    q = normalize_query(query)

    return any(word in q for word in [
        "сколько",
        "количество",
        "число",
        "how many",
        "number of",
        "count",
    ])


def _is_yes_no_question(query: str) -> bool:
    q = normalize_query(query)

    return any(pattern in q for pattern in [
        "есть ли",
        "летает ли",
        "есть рейсы",
        "есть ли рейсы",
        "does aeroline fly",
        "does it fly",
        "do you fly",
        "are there flights",
        "is there a flight",
        "are there any flights",
    ])


def _requested_limit(query: str) -> int | None:
    q = normalize_query(query)

    match = re.search(r"\b(\d{1,2})\b", q)
    if match:
        return int(match.group(1))

    number_words = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "десять": 10,
        "пять": 5,
    }

    for word, value in number_words.items():
        if word in q:
            return value

    return None


def _requested_countries(query: str) -> list[str]:
    q = normalize_query(query)
    countries: list[str] = []

    for alias, canonical_values in COUNTRY_ALIASES.items():
        if alias in q:
            countries.extend(canonical_values)

    return list(dict.fromkeys(countries))


def _requested_city(query: str, destinations: list[str], lang: str) -> str | None:
    q = normalize_query(query)

    for item in destinations:
        city = _city_name(item)
        translated_city = CITY_TRANSLATIONS.get(city, city)

        if normalize_query(city) in q:
            return city

        if normalize_query(translated_city) in q:
            return city

    for absent_key, names in KNOWN_ABSENT_DESTINATIONS.items():
        if absent_key in q:
            return names.get(lang, names["ru"])

    return None


def _filter_by_countries(destinations: list[str], countries: list[str]) -> list[str]:
    result = []

    for item in destinations:
        country = _country_name(item)
        if country in countries:
            result.append(item)

    return result


def _find_by_city(destinations: list[str], city: str) -> str | None:
    normalized_city = normalize_query(city)

    for item in destinations:
        ru_city = _city_name(item)
        en_city = CITY_TRANSLATIONS.get(ru_city, ru_city)

        if normalize_query(ru_city) == normalized_city:
            return item

        if normalize_query(en_city) == normalized_city:
            return item

    return None


def format_city_list(cities: list[str], lang: str = "ru") -> str:
    return "\n".join(f"- {_format_destination(city, lang)}" for city in cities)


def _format_summary(summary: str, domestic: list[str], international: list[str], lang: str) -> str:
    if lang == "en":
        return (
            f"AeroLine has {len(domestic) + len(international)} destinations in its route network: "
            f"{len(domestic)} domestic and {len(international)} international. Hub: Moscow (SVO)."
        )

    if summary:
        return summary

    return (
        f"Всего направлений: {len(domestic) + len(international)} "
        f"({len(domestic)} внутренних, {len(international)} международных)."
    )


def _country_for_response(country: str, lang: str) -> str:
    if lang == "en":
        return COUNTRY_TRANSLATIONS.get(country, country)

    return country


def _city_for_response(city: str, lang: str) -> str:
    if lang == "en":
        for ru_name, en_name in CITY_TRANSLATIONS.items():
            if normalize_query(city) == normalize_query(en_name):
                return en_name
        return city

    for absent_names in KNOWN_ABSENT_DESTINATIONS.values():
        if normalize_query(city) == normalize_query(absent_names.get("en", "")):
            return absent_names["ru"]

    return city


def build_route_network_answer(
    query: str,
    path: Path = DEFAULT_AEROLINE_FULL_PATH,
) -> str:
    lang = detect_query_language(query)
    summary, domestic, international = _load_routes(path)

    if not domestic and not international:
        if lang == "en":
            return "I do not have route network data for AeroLine in the local knowledge base."
        return "У меня нет данных о маршрутной сети AeroLine в локальной базе знаний."

    all_destinations = domestic + international

    wants_count = _wants_count(query)
    wants_domestic = _wants_domestic(query)
    wants_international = _wants_international(query)
    is_yes_no = _is_yes_no_question(query)
    limit = _requested_limit(query)
    countries = _requested_countries(query)
    city = _requested_city(query, all_destinations, lang)

    if wants_count:
        if lang == "en":
            return (
                f"AeroLine has {len(domestic) + len(international)} destinations in total: "
                f"{len(domestic)} domestic and {len(international)} international."
            )

        return (
            f"В маршрутной сети AeroLine всего {len(domestic) + len(international)} направлений: "
            f"{len(domestic)} внутрироссийских и {len(international)} международных."
        )

    if countries:
        matched = _filter_by_countries(international, countries)
        country_names = [_country_for_response(country, lang) for country in countries]
        country_text = ", ".join(country_names)

        if is_yes_no:
            if matched:
                if lang == "en":
                    return (
                        f"Yes, AeroLine flies to {country_text}. "
                        f"Destinations: {', '.join(_format_destination(item, lang) for item in matched)}."
                    )

                return (
                    f"Да, AeroLine летает в {country_text}. "
                    f"Направления: {', '.join(matched)}."
                )

            if lang == "en":
                return f"No, AeroLine has no destinations in {country_text} in the local route network."

            return f"Нет, в локальной маршрутной сети AeroLine нет направлений в {country_text}."

        if matched:
            if lang == "en":
                return (
                    f"AeroLine destinations in {country_text}:\n\n"
                    f"{format_city_list(matched, lang)}"
                )

            return (
                f"Направления AeroLine в {country_text}:\n\n"
                f"{format_city_list(matched, lang)}"
            )

        if lang == "en":
            return f"AeroLine has no destinations in {country_text} in the local route network."

        return f"В локальной маршрутной сети AeroLine нет направлений в {country_text}."

    if city:
        matched_city = _find_by_city(all_destinations, city)
        city_text = _city_for_response(city, lang)

        if is_yes_no:
            if matched_city:
                if lang == "en":
                    return f"Yes, AeroLine flies to {_format_destination(matched_city, lang)}."

                return f"Да, AeroLine летает в город {matched_city}."

            if lang == "en":
                return f"No, {city_text} is not in AeroLine's local route network."

            return f"Нет, города {city_text} нет в локальной маршрутной сети AeroLine."

        if matched_city:
            if lang == "en":
                return f"Yes, {_format_destination(matched_city, lang)} is in AeroLine's route network."

            return f"Да, город {matched_city} есть в маршрутной сети AeroLine."

        if lang == "en":
            return f"{city_text} is not in AeroLine's local route network."

        return f"Города {city_text} нет в локальной маршрутной сети AeroLine."

    if wants_international and not wants_domestic:
        cities = international[:limit] if limit else international

        if lang == "en":
            return (
                "AeroLine international destinations from Moscow:\n\n"
                f"{format_city_list(cities, lang)}"
            )

        return (
            "Международные направления AeroLine из Москвы:\n\n"
            f"{format_city_list(cities, lang)}"
        )

    if wants_domestic and not wants_international:
        cities = domestic[:limit] if limit else domestic

        if lang == "en":
            return (
                "AeroLine domestic destinations from Moscow:\n\n"
                f"{format_city_list(cities, lang)}"
            )

        return (
            "Внутрироссийские направления AeroLine из Москвы:\n\n"
            f"{format_city_list(cities, lang)}"
        )

    if limit:
        cities = all_destinations[:limit]

        if lang == "en":
            return (
                f"{limit} cities from AeroLine's route network:\n\n"
                f"{format_city_list(cities, lang)}"
            )

        return (
            f"{limit} городов из маршрутной сети AeroLine:\n\n"
            f"{format_city_list(cities, lang)}"
        )

    if lang == "en":
        return (
            f"{_format_summary(summary, domestic, international, lang)}\n\n"
            "Domestic destinations from Moscow:\n\n"
            f"{format_city_list(domestic, lang)}\n\n"
            "International destinations from Moscow:\n\n"
            f"{format_city_list(international, lang)}"
        )

    return (
        f"{_format_summary(summary, domestic, international, lang)}\n\n"
        "Внутрироссийские направления из Москвы:\n\n"
        f"{format_city_list(domestic, lang)}\n\n"
        "Международные направления из Москвы:\n\n"
        f"{format_city_list(international, lang)}"
    )


def build_route_network_block(
    query: str,
    path: Path = DEFAULT_AEROLINE_FULL_PATH,
) -> str:
    if not is_route_network_question(query):
        return ""

    lang = detect_query_language(query)
    summary, domestic, international = _load_routes(path)

    if not domestic and not international:
        return ""

    if lang == "en":
        lines: list[str] = [
            "ROUTE_NETWORK (AeroLine route network)",
            "Answer strictly using this block. Do not add destinations that are not listed here.",
        ]

        lines.append(_format_summary(summary, domestic, international, lang))

        if domestic:
            lines.extend([
                "",
                "Domestic destinations from Moscow:",
                ", ".join(_format_destination(item, lang) for item in domestic),
            ])

        if international:
            lines.extend([
                "",
                "International destinations from Moscow:",
                ", ".join(_format_destination(item, lang) for item in international),
            ])

        return "\n".join(lines)

    lines = [
        "ROUTE_NETWORK (маршрутная сеть AeroLine)",
        "Отвечай строго по этому блоку. Не добавляй города, которых здесь нет.",
    ]

    if summary:
        lines.append(summary)

    if domestic:
        lines.extend([
            "",
            "Внутрироссийские направления из Москвы:",
            ", ".join(domestic),
        ])

    if international:
        lines.extend([
            "",
            "Международные направления из Москвы:",
            ", ".join(international),
        ])

    return "\n".join(lines)