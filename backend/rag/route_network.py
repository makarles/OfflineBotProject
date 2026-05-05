from __future__ import annotations

import re


DOMESTIC_DESTINATIONS = [
    {"city_ru": "Владивосток", "city_en": "Vladivostok", "iata": "VVO", "country_ru": "Россия", "country_en": "Russia"},
    {"city_ru": "Воронеж", "city_en": "Voronezh", "iata": "VOZ", "country_ru": "Россия", "country_en": "Russia"},
    {"city_ru": "Екатеринбург", "city_en": "Yekaterinburg", "iata": "SVX", "country_ru": "Россия", "country_en": "Russia"},
    {"city_ru": "Иркутск", "city_en": "Irkutsk", "iata": "IKT", "country_ru": "Россия", "country_en": "Russia"},
    {"city_ru": "Казань", "city_en": "Kazan", "iata": "KZN", "country_ru": "Россия", "country_en": "Russia"},
    {"city_ru": "Калининград", "city_en": "Kaliningrad", "iata": "KGD", "country_ru": "Россия", "country_en": "Russia"},
    {"city_ru": "Краснодар", "city_en": "Krasnodar", "iata": "KRR", "country_ru": "Россия", "country_en": "Russia"},
    {"city_ru": "Красноярск", "city_en": "Krasnoyarsk", "iata": "KJA", "country_ru": "Россия", "country_en": "Russia"},
    {"city_ru": "Мурманск", "city_en": "Murmansk", "iata": "MMK", "country_ru": "Россия", "country_en": "Russia"},
    {"city_ru": "Нижний Новгород", "city_en": "Nizhny Novgorod", "iata": "GOJ", "country_ru": "Россия", "country_en": "Russia"},
    {"city_ru": "Новосибирск", "city_en": "Novosibirsk", "iata": "OVB", "country_ru": "Россия", "country_en": "Russia"},
    {"city_ru": "Омск", "city_en": "Omsk", "iata": "OMS", "country_ru": "Россия", "country_en": "Russia"},
    {"city_ru": "Пермь", "city_en": "Perm", "iata": "PEE", "country_ru": "Россия", "country_en": "Russia"},
    {"city_ru": "Ростов-на-Дону", "city_en": "Rostov-on-Don", "iata": "ROV", "country_ru": "Россия", "country_en": "Russia"},
    {"city_ru": "Самара", "city_en": "Samara", "iata": "KUF", "country_ru": "Россия", "country_en": "Russia"},
    {"city_ru": "Санкт-Петербург", "city_en": "Saint Petersburg", "iata": "LED", "country_ru": "Россия", "country_en": "Russia"},
    {"city_ru": "Сочи", "city_en": "Sochi", "iata": "AER", "country_ru": "Россия", "country_en": "Russia"},
    {"city_ru": "Тюмень", "city_en": "Tyumen", "iata": "TJM", "country_ru": "Россия", "country_en": "Russia"},
    {"city_ru": "Уфа", "city_en": "Ufa", "iata": "UFA", "country_ru": "Россия", "country_en": "Russia"},
    {"city_ru": "Хабаровск", "city_en": "Khabarovsk", "iata": "KHV", "country_ru": "Россия", "country_en": "Russia"},
]

INTERNATIONAL_DESTINATIONS = [
    {"city_ru": "Абу-Даби", "city_en": "Abu Dhabi", "iata": "AUH", "country_ru": "ОАЭ", "country_en": "UAE"},
    {"city_ru": "Алматы", "city_en": "Almaty", "iata": "ALA", "country_ru": "Казахстан", "country_en": "Kazakhstan"},
    {"city_ru": "Анталья", "city_en": "Antalya", "iata": "AYT", "country_ru": "Турция", "country_en": "Turkey"},
    {"city_ru": "Астана", "city_en": "Astana", "iata": "NQZ", "country_ru": "Казахстан", "country_en": "Kazakhstan"},
    {"city_ru": "Баку", "city_en": "Baku", "iata": "GYD", "country_ru": "Азербайджан", "country_en": "Azerbaijan"},
    {"city_ru": "Бангкок", "city_en": "Bangkok", "iata": "BKK", "country_ru": "Таиланд", "country_en": "Thailand"},
    {"city_ru": "Бишкек", "city_en": "Bishkek", "iata": "FRU", "country_ru": "Кыргызстан", "country_en": "Kyrgyzstan"},
    {"city_ru": "Гоа", "city_en": "Goa", "iata": "GOI", "country_ru": "Индия", "country_en": "India"},
    {"city_ru": "Дели", "city_en": "Delhi", "iata": "DEL", "country_ru": "Индия", "country_en": "India"},
    {"city_ru": "Денпасар", "city_en": "Denpasar", "iata": "DPS", "country_ru": "Индонезия", "country_en": "Indonesia", "extra_ru": "Бали", "extra_en": "Bali"},
    {"city_ru": "Дубай", "city_en": "Dubai", "iata": "DXB", "country_ru": "ОАЭ", "country_en": "UAE"},
    {"city_ru": "Ереван", "city_en": "Yerevan", "iata": "EVN", "country_ru": "Армения", "country_en": "Armenia"},
    {"city_ru": "Катманду", "city_en": "Kathmandu", "iata": "KTM", "country_ru": "Непал", "country_en": "Nepal"},
    {"city_ru": "Коломбо", "city_en": "Colombo", "iata": "CMB", "country_ru": "Шри-Ланка", "country_en": "Sri Lanka"},
    {"city_ru": "Куала-Лумпур", "city_en": "Kuala Lumpur", "iata": "KUL", "country_ru": "Малайзия", "country_en": "Malaysia"},
    {"city_ru": "Мале", "city_en": "Male", "iata": "MLE", "country_ru": "Мальдивы", "country_en": "Maldives"},
    {"city_ru": "Минск", "city_en": "Minsk", "iata": "MSQ", "country_ru": "Беларусь", "country_en": "Belarus"},
    {"city_ru": "Пекин", "city_en": "Beijing", "iata": "PEK", "country_ru": "Китай", "country_en": "China"},
    {"city_ru": "Пхукет", "city_en": "Phuket", "iata": "HKT", "country_ru": "Таиланд", "country_en": "Thailand"},
    {"city_ru": "Самарканд", "city_en": "Samarkand", "iata": "SKD", "country_ru": "Узбекистан", "country_en": "Uzbekistan"},
    {"city_ru": "Стамбул", "city_en": "Istanbul", "iata": "IST", "country_ru": "Турция", "country_en": "Turkey"},
    {"city_ru": "Ташкент", "city_en": "Tashkent", "iata": "TAS", "country_ru": "Узбекистан", "country_en": "Uzbekistan"},
    {"city_ru": "Тбилиси", "city_en": "Tbilisi", "iata": "TBS", "country_ru": "Грузия", "country_en": "Georgia"},
    {"city_ru": "Хургада", "city_en": "Hurghada", "iata": "HRG", "country_ru": "Египет", "country_en": "Egypt"},
    {"city_ru": "Шарм-эш-Шейх", "city_en": "Sharm El Sheikh", "iata": "SSH", "country_ru": "Египет", "country_en": "Egypt"},
]

ALL_DESTINATIONS = DOMESTIC_DESTINATIONS + INTERNATIONAL_DESTINATIONS

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
    "текущем рейсе",
    "информация о текущем рейсе",
    "информация о рейсе",
    "кратко информацию о текущем рейсе",
    "расскажи кратко информацию о текущем рейсе",
    "куда мы летим",
    "куда летим",
    "откуда мы летим",
    "откуда мы вылетаем",
    "откуда вылетаем",
    "город вылета",
    "город назначения",
    "во сколько вылет",
    "во сколько прилет",
    "во сколько прилёт",
    "во сколько мы прилетаем",
    "время вылета",
    "время прилета",
    "время прилёта",
    "когда вылет",
    "когда прилет",
    "когда прилёт",
    "крейсерская скорость",
    "крейсерская высота",
    "какая крейсерская скорость",
    "какая крейсерская высота",
    "обратный рейс",
    "есть ли обратный рейс",
    "курс валют для этого рейса",
    "нужен ли курс валют",
    "почему нет курса валют",
    "what is our flight",
    "what flight is this",
    "what is my flight",
    "flight number",
    "what is the flight number",
    "our flight",
    "my flight",
    "current flight",
    "flight information",
    "give me a short summary of the current flight",
    "where are we flying",
    "where are we going",
    "where are we departing from",
    "where do we depart from",
    "when do we depart",
    "what time is departure",
    "what time do we arrive",
    "departure time",
    "arrival time",
    "what aircraft are we flying on",
    "cruising speed",
    "cruising altitude",
    "return flight",
    "is the exchange rate needed for this flight",
    "why is there no exchange rate",
]

NON_ROUTE_KEYWORDS = [
    "багаж",
    "ручная кладь",
    "чемодан",
    "сверхнорматив",
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
    "животные",
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
    "гитару",
    "гитарой",
    "скрипка",
    "виолончель",
    "пауэрбанк",
    "аккумулятор",
    "батарея",
    "жидкость",
    "жидкости",
    "нож",
    "ножницы",
    "зажигалка",
    "коляска",
    "ценные вещи",
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
    "fee",
    "fees",
    "cost",
    "price",
    "pay",
    "payment",
    "surcharge",
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
    "sports equipment",
    "sport equipment",
    "ski",
    "skis",
    "snowboard",
    "fishing rod",
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
    "power bank",
    "powerbank",
    "battery",
    "batteries",
    "lithium battery",
    "lithium batteries",
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
    "valuable items",
    "valuables",
]

ROUTE_KEYWORDS_RU = [
    "в какие города летает",
    "куда летает",
    "куда летает aeroline",
    "маршрутная сеть",
    "маршрутной сети",
    "направления aeroline",
    "направления авиакомпании",
    "международные направления",
    "все международные направления",
    "внутрироссийские направления",
    "внутренние направления",
    "внутренние маршруты",
    "города входят в маршрутную сеть",
    "города из маршрутной сети",
    "сколько всего направлений",
    "сколько направлений",
    "сколько внутренних и международных",
]

ROUTE_KEYWORDS_EN = [
    "where does aeroline fly",
    "where aeroline flies",
    "aeroline destinations",
    "aeroline route network",
    "route network",
    "international destinations",
    "domestic destinations",
    "domestic routes",
    "how many destinations",
    "how many domestic and international",
    "cities aeroline flies to",
    "name 10 cities aeroline flies to",
]

AIRLINE_CONTEXT_KEYWORDS_RU = [
    "aeroline",
    "авиакомпания",
    "авиакомпании",
]

AIRLINE_CONTEXT_KEYWORDS_EN = [
    "aeroline",
    "airline",
]

ROUTE_INTENT_WORDS_RU = [
    "летает",
    "направления",
    "направление",
    "маршрутная сеть",
    "маршрутной сети",
    "города",
    "рейсы в",
    "рейс в",
    "рейсы до",
    "рейс до",
]

ROUTE_INTENT_WORDS_EN = [
    "fly to",
    "flies to",
    "flights to",
    "flight to",
    "destinations",
    "route network",
    "cities",
]

DESTINATION_INTENT_RU = [
    "летает",
    "лететь",
    "рейсы в",
    "рейс в",
    "рейсы до",
    "рейс до",
    "направления",
    "направление",
    "маршрутная сеть",
    "куда летает",
    "есть ли рейсы",
    "есть ли рейс",
]

DESTINATION_INTENT_EN = [
    "fly to",
    "flies to",
    "flight to",
    "flights to",
    "destinations",
    "route network",
    "does aeroline fly",
    "where does aeroline fly",
    "are there aeroline flights",
]

COUNTRY_ALIASES = {
    "оаэ": ["оаэ", "эмираты", "объединенные арабские эмираты", "объединённые арабские эмираты", "uae", "united arab emirates"],
    "таиланд": ["таиланд", "тайланд", "thailand"],
    "казахстан": ["казахстан", "kazakhstan"],
    "турция": ["турция", "turkey"],
    "египет": ["египет", "egypt"],
    "индия": ["индия", "india"],
    "узбекистан": ["узбекистан", "uzbekistan"],
    "россия": ["россия", "russia"],
    "китай": ["китай", "china"],
    "кыргызстан": ["кыргызстан", "киргизия", "kyrgyzstan", "kyrgyz republic"],
    "армения": ["армения", "armenia"],
    "беларусь": ["беларусь", "belarus"],
    "грузия": ["грузия", "georgia"],
    "азербайджан": ["азербайджан", "azerbaijan"],
    "индонезия": ["индонезия", "indonesia"],
    "малайзия": ["малайзия", "malaysia"],
    "мальдивы": ["мальдивы", "maldives"],
    "непал": ["непал", "nepal"],
    "шри-ланка": ["шри-ланка", "sri lanka"],
}

KNOWN_ABSENT_CITIES = [
    "париж",
    "лондон",
    "нью-йорк",
    "new york",
    "paris",
    "london",
]


def normalize_query(text: str) -> str:
    return text.lower().replace("ё", "е").strip()


def detect_query_language(query: str) -> str:
    q = normalize_query(query)
    cyrillic_count = len(re.findall(r"[а-я]", q))
    latin_count = len(re.findall(r"[a-z]", q))

    if latin_count > cyrillic_count:
        return "en"

    return "ru"


def _has_any(query: str, words: list[str]) -> bool:
    q = normalize_query(query)
    return any(word in q for word in words)


def _is_current_flight_question(query: str) -> bool:
    q = normalize_query(query)
    return any(keyword in q for keyword in CURRENT_FLIGHT_KEYWORDS)


def _has_known_destination_mention(query: str) -> bool:
    q = normalize_query(query)

    for item in ALL_DESTINATIONS:
        values = [
            item["city_ru"],
            item["city_en"],
            item["country_ru"],
            item["country_en"],
            item.get("extra_ru", ""),
            item.get("extra_en", ""),
        ]

        if any(value and normalize_query(value) in q for value in values):
            return True

    for aliases in COUNTRY_ALIASES.values():
        if any(alias in q for alias in aliases):
            return True

    return False


def _has_absent_destination_mention(query: str) -> bool:
    q = normalize_query(query)
    return any(city in q for city in KNOWN_ABSENT_CITIES)


def _has_route_destination_intent(query: str) -> bool:
    q = normalize_query(query)

    ru_match = any(keyword in q for keyword in DESTINATION_INTENT_RU)
    en_match = any(keyword in q for keyword in DESTINATION_INTENT_EN)

    return ru_match or en_match


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
        _has_route_destination_intent(query)
        and (
            _has_known_destination_mention(query)
            or _has_absent_destination_mention(query)
            or any(keyword in q for keyword in AIRLINE_CONTEXT_KEYWORDS_RU + AIRLINE_CONTEXT_KEYWORDS_EN)
        )
    )

    return (
        direct_match_ru
        or direct_match_en
        or contextual_match_ru
        or contextual_match_en
        or destination_match
    )


def _format_destination(item: dict[str, str], lang: str) -> str:
    if lang == "en":
        city = item["city_en"]
        country = item["country_en"]
        extra = item.get("extra_en")

        if extra:
            return f"{city} ({extra}) ({item['iata']}, {country})"

        return f"{city} ({item['iata']}, {country})"

    city = item["city_ru"]
    country = item["country_ru"]
    extra = item.get("extra_ru")

    if extra:
        return f"{city} ({extra}) ({item['iata']}, {country})"

    return f"{city} ({item['iata']}, {country})"


def _format_list(items: list[dict[str, str]], lang: str) -> str:
    return "\n".join(_format_destination(item, lang) for item in items)


def _find_country_key(query: str) -> str | None:
    q = normalize_query(query)

    for country_key, aliases in COUNTRY_ALIASES.items():
        if any(alias in q for alias in aliases):
            return country_key

    return None


def _destinations_by_country(country_key: str) -> list[dict[str, str]]:
    aliases = COUNTRY_ALIASES.get(country_key, [])
    result = []

    for item in ALL_DESTINATIONS:
        country_values = [
            normalize_query(item["country_ru"]),
            normalize_query(item["country_en"]),
        ]

        if any(alias in country_values for alias in aliases):
            result.append(item)

    return result


def _find_city(query: str) -> dict[str, str] | None:
    q = normalize_query(query)

    sorted_destinations = sorted(
        ALL_DESTINATIONS,
        key=lambda item: max(len(item["city_ru"]), len(item["city_en"])),
        reverse=True,
    )

    for item in sorted_destinations:
        values = [
            item["city_ru"],
            item["city_en"],
            item.get("extra_ru", ""),
            item.get("extra_en", ""),
        ]

        if any(value and normalize_query(value) in q for value in values):
            return item

    return None


def _find_absent_city(query: str) -> str | None:
    q = normalize_query(query)

    names = {
        "париж": "Париж",
        "paris": "Paris",
        "лондон": "Лондон",
        "london": "London",
        "нью-йорк": "Нью-Йорк",
        "new york": "New York",
    }

    for key, name in names.items():
        if key in q:
            return name

    return None


def _is_count_question(query: str) -> bool:
    return _has_any(query, [
        "сколько всего направлений",
        "сколько направлений",
        "сколько у aeroline",
        "how many destinations",
        "how many domestic and international",
    ])


def _is_split_count_question(query: str) -> bool:
    return _has_any(query, [
        "сколько внутренних и международных",
        "внутренних и международных",
        "domestic and international",
    ])


def _is_domestic_question(query: str) -> bool:
    return _has_any(query, [
        "внутрироссий",
        "внутренние направления",
        "внутренние маршруты",
        "domestic destinations",
        "domestic routes",
    ])


def _is_international_question(query: str) -> bool:
    return _has_any(query, [
        "международные направления",
        "все международные направления",
        "international destinations",
        "all international destinations",
    ])


def _is_ten_cities_question(query: str) -> bool:
    return _has_any(query, [
        "10 городов",
        "десять городов",
        "name 10 cities",
        "10 cities",
    ])


def _is_general_route_question(query: str) -> bool:
    return _has_any(query, [
        "в какие города",
        "куда летает",
        "маршрутная сеть",
        "города входят",
        "where does aeroline fly",
        "where aeroline flies",
        "route network",
        "aeroline destinations",
        "which cities",
    ])


def build_route_network_answer(query: str) -> str:
    lang = detect_query_language(query)
    q = normalize_query(query)

    total_count = len(ALL_DESTINATIONS)
    domestic_count = len(DOMESTIC_DESTINATIONS)
    international_count = len(INTERNATIONAL_DESTINATIONS)

    if _is_split_count_question(q):
        if lang == "en":
            return f"AeroLine has {domestic_count} domestic destinations and {international_count} international destinations."

        return f"В маршрутной сети AeroLine {domestic_count} внутрироссийских и {international_count} международных направлений."

    if _is_count_question(q):
        if lang == "en":
            return f"AeroLine's route network has {total_count} destinations: {domestic_count} domestic and {international_count} international."

        return f"В маршрутной сети AeroLine всего {total_count} направлений: {domestic_count} внутрироссийских и {international_count} международных."

    if _is_domestic_question(q):
        if lang == "en":
            return "AeroLine domestic destinations from Moscow:\n\n" + _format_list(DOMESTIC_DESTINATIONS, lang)

        return "Внутрироссийские направления AeroLine из Москвы:\n\n" + _format_list(DOMESTIC_DESTINATIONS, lang)

    if _is_international_question(q):
        if lang == "en":
            return "AeroLine international destinations from Moscow:\n\n" + _format_list(INTERNATIONAL_DESTINATIONS, lang)

        return "Международные направления AeroLine из Москвы:\n\n" + _format_list(INTERNATIONAL_DESTINATIONS, lang)

    if _is_ten_cities_question(q):
        destinations = ALL_DESTINATIONS[:10]

        if lang == "en":
            return "10 cities from AeroLine's route network:\n\n" + _format_list(destinations, lang)

        return "10 городов из маршрутной сети AeroLine:\n\n" + _format_list(destinations, lang)

    absent_city = _find_absent_city(q)

    if absent_city:
        if lang == "en":
            return f"No, {absent_city} is not in AeroLine's local route network."

        return f"Нет, города {absent_city} нет в локальной маршрутной сети AeroLine."

    if _is_general_route_question(q):
        if lang == "en":
            return (
                f"Total destinations: {total_count} "
                f"({domestic_count} domestic, {international_count} international). Hub: Moscow (SVO).\n\n"
                "Domestic destinations from Moscow:\n\n"
                + _format_list(DOMESTIC_DESTINATIONS, lang)
                + "\n\nInternational destinations from Moscow:\n\n"
                + _format_list(INTERNATIONAL_DESTINATIONS, lang)
            )

        return (
            f"Всего направлений: {total_count} "
            f"({domestic_count} внутренних, {international_count} международных). Хаб: Москва (SVO).\n\n"
            "Внутрироссийские направления из Москвы:\n\n"
            + _format_list(DOMESTIC_DESTINATIONS, lang)
            + "\n\nМеждународные направления из Москвы:\n\n"
            + _format_list(INTERNATIONAL_DESTINATIONS, lang)
        )

    country_key = _find_country_key(q)

    if country_key:
        destinations = _destinations_by_country(country_key)

        if destinations:
            country_ru = destinations[0]["country_ru"]
            country_en = destinations[0]["country_en"]

            if lang == "en":
                return f"Yes, AeroLine flies to {country_en}. Destinations:\n\n" + _format_list(destinations, lang)

            return f"Да, AeroLine летает в {country_ru}. Направления:\n\n" + _format_list(destinations, lang)

    city = _find_city(q)

    if city:
        if lang == "en":
            return (
                f"Yes, AeroLine flies to {city['city_en']} "
                f"({city['iata']}, {city['country_en']})."
            )

        return (
            f"Да, AeroLine летает в город {city['city_ru']} "
            f"({city['iata']}, {city['country_ru']})."
        )

    if lang == "en":
        return "No, this destination is not in AeroLine's local route network."

    return "Нет, такого направления нет в локальной маршрутной сети AeroLine."


def build_route_network_block(query: str | None = None) -> str:
    domestic_lines = [
        f"- {item['city_ru']} ({item['iata']}, {item['country_ru']})"
        for item in DOMESTIC_DESTINATIONS
    ]

    international_lines = [
        f"- {_format_destination(item, 'ru')}"
        for item in INTERNATIONAL_DESTINATIONS
    ]

    return (
        "ROUTE_NETWORK (маршрутная сеть AeroLine)\n"
        f"Хаб: Москва (SVO)\n"
        f"Всего направлений: {len(ALL_DESTINATIONS)}\n"
        f"Внутрироссийских направлений: {len(DOMESTIC_DESTINATIONS)}\n"
        f"Международных направлений: {len(INTERNATIONAL_DESTINATIONS)}\n\n"
        "Внутрироссийские направления из Москвы:\n"
        + "\n".join(domestic_lines)
        + "\n\n"
        "Международные направления из Москвы:\n"
        + "\n".join(international_lines)
    )