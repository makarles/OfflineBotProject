from __future__ import annotations

import re


BAGGAGE_KEYWORDS_RU = [
    "багаж",
    "ручная кладь",
    "ручной клади",
    "чемодан",
    "чемоданом",
    "сверхнорматив",
    "сверхнормативный багаж",
    "дополнительный килограмм",
    "дополнительное место",
    "доплата",
    "стоимость багажа",
    "сколько стоит",
    "провоз",
    "перевозка",
    "перевозить",
    "провезти",
    "жидкость",
    "жидкости",
    "флакон",
    "флаконов",
    "бутылка",
    "бутылку",
    "бутылку воды",
    "вода",
    "воды",
    "пауэрбанк",
    "пауэрбанка",
    "пауэрбанков",
    "powerbank",
    "аккумулятор",
    "аккумуляторы",
    "батарея",
    "батареи",
    "литий",
    "втч",
    "нож",
    "ножницы",
    "зажигалка",
    "зажигалку",
    "оружие",
    "животное",
    "животных",
    "животные",
    "питомец",
    "кошка",
    "кот",
    "собака",
    "мопс",
    "бульдог",
    "поводыр",
    "ветеринар",
    "документы",
    "документ",
    "переноска",
    "спортинвентарь",
    "спортивный инвентарь",
    "спортивного инвентаря",
    "спортивное снаряжение",
    "спортивного снаряжения",
    "лыжи",
    "сноуборд",
    "велосипед",
    "удочка",
    "удочки",
    "гольф",
    "музыкальный инструмент",
    "музыкальные инструменты",
    "скрипка",
    "флейта",
    "виолончель",
    "контрабас",
    "гитара",
    "гитару",
    "гитарой",
    "саксофон",
    "хрупкое",
    "хрупкий",
    "коляска",
    "детская коляска",
    "ценные вещи",
    "ценный багаж",
    "рейсом",
    "салон",
    "салоне",
    "багажном отделении",
    "зарегистрированный багаж",
    "зарегистрированном багаже",
]

BAGGAGE_KEYWORDS_EN = [
    "baggage",
    "luggage",
    "carry-on",
    "carry on",
    "hand luggage",
    "cabin baggage",
    "checked baggage",
    "checked luggage",
    "suitcase",
    "overweight",
    "excess baggage",
    "extra baggage",
    "extra bag",
    "additional baggage",
    "additional bag",
    "additional kilogram",
    "extra kilogram",
    "baggage fee",
    "luggage fee",
    "baggage allowance",
    "liquid",
    "liquids",
    "bottle",
    "water bottle",
    "water",
    "power bank",
    "powerbank",
    "power banks",
    "battery",
    "batteries",
    "lithium",
    "watt-hour",
    "watt hours",
    "knife",
    "knives",
    "scissors",
    "lighter",
    "weapon",
    "weapons",
    "animal",
    "animals",
    "pets",
    "cat",
    "dog",
    "pug",
    "bulldog",
    "guide dog",
    "service dog",
    "veterinary",
    "documents",
    "carrier",
    "cabin",
    "hold",
    "cargo",
    "sports equipment",
    "sport equipment",
    "skis",
    "ski",
    "snowboard",
    "bicycle",
    "bike",
    "fishing rod",
    "golf clubs",
    "musical instrument",
    "musical instruments",
    "violin",
    "flute",
    "cello",
    "double bass",
    "guitar",
    "saxophone",
    "fragile",
    "stroller",
    "baby stroller",
    "pushchair",
    "valuables",
    "valuable items",
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


def is_baggage_question(query: str) -> bool:
    q = normalize_query(query)

    return (
        any(keyword in q for keyword in BAGGAGE_KEYWORDS_RU)
        or any(keyword in q for keyword in BAGGAGE_KEYWORDS_EN)
    )


def _has_any(query: str, words: list[str]) -> bool:
    q = normalize_query(query)
    return any(word in q for word in words)


def _extract_weight_kg(query: str) -> int | None:
    q = normalize_query(query)
    match = re.search(r"(\d{1,3})\s*(?:кг|kg|kilograms?|kilos?)", q)

    if match:
        return int(match.group(1))

    return None


def _extract_wh(query: str) -> int | None:
    q = normalize_query(query)
    match = re.search(r"(\d{2,3})\s*(?:втч|wh|watt-hours?|watt hours?)", q)

    if match:
        return int(match.group(1))

    return None


def _extract_ml(query: str) -> int | None:
    q = normalize_query(query)
    match = re.search(r"(\d{2,4})\s*(?:мл|ml|milliliters?|millilitres?)", q)

    if match:
        return int(match.group(1))

    return None


def _extract_bottle_count(query: str) -> int | None:
    q = normalize_query(query)
    match = re.search(
        r"(\d{1,2})\s*(?:флакон(?:а|ов)?|бутыл(?:ка|ки|ок|ку)?|bottles?|containers?|vials?)",
        q,
    )

    if match:
        return int(match.group(1))

    number_words = {
        "один": 1,
        "одна": 1,
        "два": 2,
        "две": 2,
        "три": 3,
        "четыре": 4,
        "пять": 5,
        "шесть": 6,
        "семь": 7,
        "восемь": 8,
        "девять": 9,
        "десять": 10,
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
    }

    for word, value in number_words.items():
        if word in q:
            return value

    return None


def _extract_powerbank_count(query: str) -> int | None:
    q = normalize_query(query)
    match = re.search(
        r"(\d{1,2})\s*(?:пауэрбанк(?:а|ов)?|power banks?|powerbanks?|аккумулятор(?:а|ов|ы)?|batteries)",
        q,
    )

    if match:
        return int(match.group(1))

    number_words = {
        "один": 1,
        "one": 1,
        "два": 2,
        "две": 2,
        "two": 2,
        "три": 3,
        "three": 3,
    }

    for word, value in number_words.items():
        if word in q:
            return value

    return None


def _is_domestic(query: str) -> bool:
    return _has_any(query, [
        "внутрен",
        "внутрироссий",
        "по россии",
        "domestic",
        "within russia",
    ])


def _is_international(query: str) -> bool:
    return _has_any(query, [
        "международ",
        "зарубеж",
        "international",
        "abroad",
        "foreign",
    ])


def _format_by_lang(lang: str, ru: str, en: str) -> str:
    return en if lang == "en" else ru


def build_baggage_answer(query: str) -> str:
    lang = detect_query_language(query)
    q = normalize_query(query)

    if _has_any(q, ["эконом", "economy"]) and _has_any(q, ["чемодан", "багаж", "suitcase", "checked baggage", "checked luggage"]):
        weight = _extract_weight_kg(q)

        if weight is not None and weight > 23:
            excess = weight - 23
            return _format_by_lang(
                lang,
                f"Да, нужно доплатить: в эконом-классе норма зарегистрированного багажа — до 23 кг, а ваш багаж весит {weight} кг. Превышение составляет {excess} кг. На внутренних рейсах доплата — 500 рублей за каждый дополнительный килограмм, на международных — от 8 до 25 евро за килограмм.",
                f"Yes, you need to pay extra: the Economy Class checked baggage allowance is up to 23 kg, and your baggage weighs {weight} kg. The excess is {excess} kg. On domestic flights the fee is 500 rubles per extra kilogram; on international flights it is from 8 to 25 euros per kilogram.",
            )

        return _format_by_lang(
            lang,
            "В эконом-классе AeroLine положено одно место зарегистрированного багажа до 23 кг, сумма трёх измерений — до 158 см.",
            "In AeroLine Economy Class, you can check in one piece of baggage up to 23 kg, with the sum of three dimensions up to 158 cm.",
        )

    if _has_any(q, ["эконом", "economy"]) and _has_any(q, ["ручная кладь", "ручной клади", "hand luggage", "carry-on", "carry on", "cabin baggage"]):
        return _format_by_lang(
            lang,
            "В эконом-классе AeroLine можно бесплатно провезти одно место ручной клади до 10 кг с габаритами не более 55×40×25 см.",
            "In AeroLine Economy Class, you can carry one piece of hand luggage up to 10 kg with dimensions up to 55×40×25 cm free of charge.",
        )

    if _has_any(q, ["бизнес", "business"]) and _has_any(q, ["ручная кладь", "ручной клади", "hand luggage", "carry-on", "carry on", "cabin baggage"]):
        return _format_by_lang(
            lang,
            "В бизнес-классе AeroLine можно бесплатно провезти ручную кладь до 15 кг.",
            "In AeroLine Business Class, you can carry hand luggage up to 15 kg free of charge.",
        )

    if _has_any(q, ["бизнес", "business"]):
        weight = _extract_weight_kg(q)

        if weight is not None and _has_any(q, ["два", "2", "two"]) and weight <= 32:
            return _format_by_lang(
                lang,
                "Да, это входит в норму бизнес-класса: разрешены два места зарегистрированного багажа, каждое до 32 кг.",
                "Yes, this is within the Business Class allowance: two checked baggage pieces are allowed, each up to 32 kg.",
            )

        return _format_by_lang(
            lang,
            "В бизнес-классе AeroLine бесплатно провозится ручная кладь до 15 кг и два места зарегистрированного багажа, каждое до 32 кг.",
            "In AeroLine Business Class, hand luggage up to 15 kg and two checked baggage pieces up to 32 kg each are included free of charge.",
        )

    if _has_any(q, ["ребен", "ребён", "до 2 лет", "infant", "under 2"]):
        return _format_by_lang(
            lang,
            "Ребёнок до 2 лет без отдельного места имеет право на 10 кг зарегистрированного багажа и складную детскую коляску бесплатно.",
            "An infant under 2 years old without a separate seat is entitled to 10 kg of checked baggage and a foldable stroller free of charge.",
        )

    if _has_any(q, ["сумма трех измерений", "сумма трёх измерений", "158", "sum of three dimensions"]):
        return _format_by_lang(
            lang,
            "Максимальная сумма трёх измерений зарегистрированного багажа — 158 см.",
            "The maximum sum of three dimensions for checked baggage is 158 cm.",
        )

    if _has_any(q, ["дополнительный килограмм", "extra kilogram", "additional kilogram"]) or (
        _has_any(q, ["сколько стоит", "cost", "price", "fee", "how much"])
        and _has_any(q, ["килограмм", "kg", "kilogram"])
    ):
        if _is_international(q):
            return _format_by_lang(
                lang,
                "На международных направлениях дополнительный килограмм багажа стоит от 8 до 25 евро в зависимости от маршрута.",
                "On international routes, each extra kilogram of baggage costs from 8 to 25 euros depending on the route.",
            )

        return _format_by_lang(
            lang,
            "На внутренних рейсах по России каждый дополнительный килограмм багажа стоит 500 рублей.",
            "On domestic flights within Russia, each extra kilogram of baggage costs 500 rubles.",
        )

    if _has_any(q, ["дополнительное место", "extra bag", "additional bag", "extra baggage", "additional baggage"]):
        if _is_international(q):
            return _format_by_lang(
                lang,
                "Дополнительное место багажа на международных направлениях стоит от 50 до 150 евро.",
                "An additional baggage piece on international routes costs from 50 to 150 euros.",
            )

        return _format_by_lang(
            lang,
            "Дополнительное место багажа на внутренних рейсах стоит 3000 рублей.",
            "An additional baggage piece on domestic flights costs 3000 rubles.",
        )

    if _has_any(q, ["сверхнорматив", "overweight", "excess baggage", "заранее", "online", "онлайн", "80%"]):
        if _has_any(q, ["80%"]):
            return _format_by_lang(
                lang,
                "Нет, в локальных правилах указана скидка 25–30% при предоплате сверхнормативного багажа онлайн, а не 80%.",
                "No. The local rules mention a 25–30% discount for prepaid excess baggage online, not 80%.",
            )

        return _format_by_lang(
            lang,
            "Да, сверхнормативный багаж рекомендуется оплачивать заранее через сайт или мобильное приложение: это на 25–30% дешевле, чем в аэропорту.",
            "Yes. AeroLine recommends paying for excess baggage in advance via the website or mobile app: it is 25–30% cheaper than at the airport.",
        )

    if _has_any(q, ["жидкость", "жидкости", "флакон", "флаконов", "бутылка", "бутылку", "вода", "воды", "liquid", "liquids", "bottle", "water bottle", "water"]):
        ml = _extract_ml(q)
        count = _extract_bottle_count(q)

        if ml is not None and ml > 100:
            return _format_by_lang(
                lang,
                f"Нет, ёмкость {ml} мл нельзя взять в ручную кладь: каждая ёмкость с жидкостью должна быть не более 100 мл.",
                f"No, a {ml} ml container is not allowed in hand luggage. Each liquid container must be no larger than 100 ml.",
            )

        if count is not None and ml is not None:
            total = count * ml

            if ml <= 100 and total <= 1000:
                return _format_by_lang(
                    lang,
                    f"Да, {count} ёмкостей по {ml} мл можно взять, если все они помещаются в один прозрачный пакет объёмом до 1 литра.",
                    f"Yes, {count} containers of {ml} ml are allowed if they all fit into one transparent bag with a total volume of up to 1 liter.",
                )

            return _format_by_lang(
                lang,
                "Нет, так нельзя: каждая ёмкость должна быть до 100 мл, а общий объём жидкостей в прозрачном пакете — до 1 литра.",
                "No, this is not allowed: each container must be up to 100 ml, and all liquids must fit into one transparent bag of up to 1 liter.",
            )

        if _has_any(q, ["прозрачный пакет", "transparent bag"]):
            return _format_by_lang(
                lang,
                "Жидкости в ручной клади должны быть в ёмкостях до 100 мл каждая и помещаться в один прозрачный пакет объёмом до 1 литра.",
                "Liquids in hand luggage must be in containers of up to 100 ml each and placed in one transparent bag of up to 1 liter.",
            )

        return _format_by_lang(
            lang,
            "Жидкости можно провозить в ручной клади только в ёмкостях до 100 мл каждая. Все ёмкости должны помещаться в один прозрачный пакет объёмом до 1 литра.",
            "Liquids are allowed in hand luggage only in containers of up to 100 ml each. All containers must fit into one transparent bag of up to 1 liter.",
        )

    if _has_any(q, ["пауэрбанк", "пауэрбанка", "пауэрбанков", "power bank", "powerbank", "power banks", "аккумулятор", "аккумуляторы", "батарея", "батареи", "battery", "batteries", "литий", "lithium", "втч"]):
        wh = _extract_wh(q)
        count = _extract_powerbank_count(q)

        if _has_any(q, ["чемодан", "зарегистрирован", "checked baggage", "checked luggage", "suitcase"]):
            return _format_by_lang(
                lang,
                "Нет, пауэрбанки и внешние батареи нельзя сдавать в зарегистрированный багаж. Их можно перевозить только в ручной клади.",
                "No. Power banks and external batteries are not allowed in checked baggage. They may be carried only in hand luggage.",
            )

        if count is not None and count > 2:
            return _format_by_lang(
                lang,
                "Нет, можно взять не более 2 пауэрбанков до 100 Втч на пассажира, только в ручной клади.",
                "No. A passenger may carry no more than 2 power banks up to 100 Wh, and only in hand luggage.",
            )

        if wh is not None:
            if wh <= 100:
                return _format_by_lang(
                    lang,
                    f"Да, пауэрбанк {wh} Втч можно взять, но только в ручную кладь. Разрешено до 2 штук на пассажира.",
                    f"Yes, a {wh} Wh power bank is allowed, but only in hand luggage. Up to 2 pieces per passenger are allowed.",
                )

            if 100 < wh <= 160:
                return _format_by_lang(
                    lang,
                    f"Пауэрбанк {wh} Втч можно провозить только с согласованием с авиакомпанией за 48 часов до вылета.",
                    f"A {wh} Wh power bank may be carried only with AeroLine approval requested 48 hours before departure.",
                )

            return _format_by_lang(
                lang,
                f"Нет, пауэрбанк {wh} Втч к перевозке не принимается, так как ёмкость выше 160 Втч.",
                f"No, a {wh} Wh power bank is not accepted for carriage because it exceeds 160 Wh.",
            )

        return _format_by_lang(
            lang,
            "Пауэрбанки и внешние батареи до 100 Втч можно перевозить только в ручной клади, до 2 штук на пассажира. От 100 до 160 Втч — только с согласованием за 48 часов. Свыше 160 Втч — к перевозке не принимаются.",
            "Power banks and external batteries up to 100 Wh may be carried only in hand luggage, up to 2 per passenger. From 100 to 160 Wh requires approval 48 hours before departure. Above 160 Wh is not accepted.",
        )

    if _has_any(q, ["зажигалка", "зажигалку", "lighter"]):
        return _format_by_lang(
            lang,
            "На борт можно взять одну газовую или бензиновую зажигалку. Другие зажигалки и опасные предметы могут быть запрещены.",
            "You may take one gas or petrol lighter on board. Other lighters and dangerous items may be prohibited.",
        )

    if _has_any(q, ["ножницы", "scissors"]):
        return _format_by_lang(
            lang,
            "Ножницы с лезвием более 6 см запрещены в ручной клади.",
            "Scissors with blades longer than 6 cm are prohibited in hand luggage.",
        )

    if _has_any(q, ["нож", "knife", "knives"]):
        return _format_by_lang(
            lang,
            "Ножи и другие острые предметы запрещены в ручной клади.",
            "Knives and other sharp objects are prohibited in hand luggage.",
        )

    if _has_any(q, ["оружие", "weapon", "weapons"]):
        return _format_by_lang(
            lang,
            "Оружие и его имитации запрещены в ручной клади.",
            "Weapons and weapon imitations are prohibited in hand luggage.",
        )

    if _has_any(q, ["запрещены в зарегистрированном", "запрещено в зарегистрированном", "checked baggage prohibited", "prohibited in checked"]):
        return _format_by_lang(
            lang,
            "В зарегистрированном багаже запрещены литий-ионные аккумуляторы, воспламеняющиеся жидкости, газовые баллоны, пиротехника, магниты большой мощности и ртутные изделия.",
            "Lithium-ion batteries, flammable liquids, gas cylinders, pyrotechnics, high-power magnets, and mercury-containing items are prohibited in checked baggage.",
        )

    if _has_any(q, [
        "кошка", "кот", "cat",
        "животное", "животных", "животные", "animal", "animals",
        "pet", "pets",
        "собака", "dog",
        "переноска", "carrier",
        "мопс", "pug",
        "бульдог", "bulldog",
        "поводыр", "guide dog", "service dog",
        "багажном отделении", "hold", "cargo",
    ]):
        weight = _extract_weight_kg(q)

        if _has_any(q, ["мопс", "pug", "бульдог", "bulldog", "персидск", "persian"]):
            return _format_by_lang(
                lang,
                "Нет, брахицефальные породы, включая мопсов, бульдогов и персидских кошек, не принимаются к перевозке.",
                "No. Brachycephalic breeds, including pugs, bulldogs, and Persian cats, are not accepted for carriage.",
            )

        if _has_any(q, ["поводыр", "guide dog", "service dog"]):
            return _format_by_lang(
                lang,
                "Собаки-поводыри и собаки сопровождения перевозятся бесплатно в салоне при наличии подтверждающих документов.",
                "Guide dogs and service dogs are carried free of charge in the cabin with supporting documents.",
            )

        if _has_any(q, ["без ветеринар", "без документ", "without veterinary", "without documents"]):
            return _format_by_lang(
                lang,
                "Нет, животное нельзя взять в салон без ветеринарных документов и справки о прививках.",
                "No, an animal cannot be taken into the cabin without veterinary documents and vaccination certificates.",
            )

        if _has_any(q, ["какие животные", "животные перевозятся", "багажном отделении", "what animals", "which animals"]):
            return _format_by_lang(
                lang,
                "В багажном отделении перевозятся животные весом свыше 8 кг в специальных контейнерах. Брахицефальные породы, включая мопсов, бульдогов и персидских кошек, к перевозке не принимаются.",
                "Animals weighing more than 8 kg are transported in the hold in special containers. Brachycephalic breeds, including pugs, bulldogs, and Persian cats, are not accepted for carriage.",
            )

        if _has_any(q, ["документ", "ветеринар", "documents", "veterinary"]):
            return _format_by_lang(
                lang,
                "Да, для перевозки животного нужны ветеринарные документы и справка о прививках.",
                "Yes, veterinary documents and vaccination certificates are required for transporting an animal.",
            )

        if _has_any(q, ["сколько животных", "maximum animals", "how many animals"]):
            return _format_by_lang(
                lang,
                "На борту одного самолёта допускается не более 4 животных.",
                "No more than 4 animals are allowed on one aircraft.",
            )

        if _has_any(q, ["размер", "габарит", "dimensions", "size"]):
            return _format_by_lang(
                lang,
                "Переноска для животного в салоне должна быть мягкой и не превышать 45×30×25 см.",
                "The in-cabin pet carrier must be soft-sided and no larger than 45×30×25 cm.",
            )

        if _has_any(q, ["стоимость", "стоит", "сколько", "cost", "price", "fee", "how much"]):
            if _has_any(q, ["багаж", "багажном", "hold", "cargo"]):
                if _is_international(q):
                    return _format_by_lang(
                        lang,
                        "Перевозка животного в багажном отделении на международном рейсе стоит 150 евро.",
                        "Transporting an animal in the hold on an international flight costs 150 euros.",
                    )

                return _format_by_lang(
                    lang,
                    "Перевозка животного в багажном отделении на внутреннем рейсе стоит 8000 рублей.",
                    "Transporting an animal in the hold on a domestic flight costs 8000 rubles.",
                )

            if _is_international(q):
                return _format_by_lang(
                    lang,
                    "Перевозка животного в салоне на международном рейсе стоит 100 евро.",
                    "Transporting an animal in the cabin on an international flight costs 100 euros.",
                )

            return _format_by_lang(
                lang,
                "Перевозка животного в салоне на внутреннем рейсе стоит 5000 рублей.",
                "Transporting an animal in the cabin on a domestic flight costs 5000 rubles.",
            )

        if weight is not None and weight > 8:
            return _format_by_lang(
                lang,
                "Животное весом свыше 8 кг перевозится в багажном отделении в специальном контейнере.",
                "An animal weighing more than 8 kg must be transported in the hold in a special container.",
            )

        return _format_by_lang(
            lang,
            "Мелких животных весом до 8 кг вместе с переноской можно перевозить в салоне. Переноска должна быть мягкой и не более 45×30×25 см. Перевозка платная, нужны ветеринарные документы.",
            "Small animals up to 8 kg including the carrier may be transported in the cabin. The carrier must be soft-sided and no larger than 45×30×25 cm. Transport is paid and veterinary documents are required.",
        )

    if _has_any(q, [
        "лыжи", "сноуборд", "велосипед", "удочка", "удочки", "гольф",
        "спортинвентарь", "спортивный инвентарь", "спортивного инвентаря",
        "спортивное снаряжение", "спортивного снаряжения",
        "sports equipment", "sport equipment", "ski", "skis", "snowboard",
        "bicycle", "bike", "fishing rod", "golf clubs",
    ]):
        if _has_any(q, ["бесплатн", "free"]) and _has_any(q, ["велосипед", "bicycle", "bike"]):
            return _format_by_lang(
                lang,
                "Нет, бесплатная перевозка велосипедов в правилах AeroLine не указана. Велосипед принимается как одно место сверхнормативного багажа: 3000 рублей на внутренних рейсах или от 50 евро на международных.",
                "No, free bicycle carriage is not specified in AeroLine rules. A bicycle is accepted as one piece of excess baggage: 3000 rubles on domestic flights or from 50 euros on international flights.",
            )

        if _has_any(q, ["стоимость", "стоит", "сколько", "cost", "price", "fee", "how much"]):
            if _is_international(q):
                return _format_by_lang(
                    lang,
                    "Перевозка спортивного инвентаря на международном рейсе стоит от 50 евро.",
                    "Sports equipment carriage on an international flight costs from 50 euros.",
                )

            return _format_by_lang(
                lang,
                "Перевозка спортивного инвентаря на внутреннем рейсе стоит 3000 рублей.",
                "Sports equipment carriage on a domestic flight costs 3000 rubles.",
            )

        if _has_any(q, ["ограничения", "габарит", "вес", "dimensions", "weight", "limits"]):
            return _format_by_lang(
                lang,
                "Спортивный инвентарь не должен превышать общие нормы: сумма трёх измерений до 158 см и вес до 23 кг.",
                "Sports equipment must comply with the general limits: the sum of three dimensions up to 158 cm and weight up to 23 kg.",
            )

        if _has_any(q, ["заявлять", "бронировании", "declare", "booking"]):
            return _format_by_lang(
                lang,
                "Да, спортивный инвентарь рекомендуется заявлять при бронировании.",
                "Yes, AeroLine recommends declaring sports equipment during booking.",
            )

        return _format_by_lang(
            lang,
            "Лыжи, сноуборд, гольф-клюшки, удочки, велосипеды и другое спортивное снаряжение принимаются как одно место сверхнормативного багажа. Стоимость: 3000 рублей на внутренних рейсах или от 50 евро на международных.",
            "Skis, snowboards, golf clubs, fishing rods, bicycles, and other sports equipment are accepted as one piece of excess baggage. The fee is 3000 rubles on domestic flights or from 50 euros on international flights.",
        )

    if _has_any(q, [
        "музыкальный инструмент", "музыкальные инструменты",
        "скрипка", "флейта", "виолончель", "контрабас",
        "гитара", "гитару", "гитарой", "саксофон",
        "musical instrument", "musical instruments",
        "violin", "flute", "cello", "double bass", "guitar", "saxophone",
    ]):
        if _has_any(q, ["скрипка", "флейта", "violin", "flute"]):
            return _format_by_lang(
                lang,
                "Маленькие музыкальные инструменты, например скрипку или флейту, можно брать в качестве ручной клади.",
                "Small musical instruments such as a violin or flute may be taken as hand luggage.",
            )

        if _has_any(q, ["виолончель", "контрабас", "cello", "double bass"]):
            return _format_by_lang(
                lang,
                "Крупные музыкальные инструменты, например виолончель или контрабас, оформляются как отдельное место с покупкой дополнительного кресла в салоне.",
                "Large musical instruments such as a cello or double bass are transported as a separate cabin seat, which requires purchasing an additional seat.",
            )

        if _has_any(q, ["гитара", "гитару", "гитарой", "саксофон", "guitar", "saxophone"]):
            return _format_by_lang(
                lang,
                "Гитару или саксофон можно оформить как регистрируемый багаж с маркировкой «хрупкое».",
                "A guitar or saxophone may be checked in as baggage with a “fragile” label.",
            )

        return _format_by_lang(
            lang,
            "Маленькие инструменты можно взять как ручную кладь, крупные — перевозить на отдельном кресле, а гитару и саксофон — оформить как регистрируемый багаж с маркировкой «хрупкое».",
            "Small instruments may be taken as hand luggage, large instruments require a separate cabin seat, and a guitar or saxophone may be checked in with a “fragile” label.",
        )

    if _has_any(q, ["коляска", "stroller", "baby stroller", "pushchair"]):
        return _format_by_lang(
            lang,
            "Складная детская коляска принимается как бесплатный дополнительный багаж. Её можно сдать у трапа и получить в точке прилёта вместе с основным багажом.",
            "A foldable baby stroller is accepted as free additional baggage. It may be handed over at the aircraft stairs and returned at the destination with the main baggage.",
        )

    if _has_any(q, ["ценные вещи", "ценный", "valuable", "valuables"]):
        return _format_by_lang(
            lang,
            "Предметы стоимостью свыше 10 000 рублей не рекомендуется сдавать в регистрируемый багаж. Ответственность AeroLine за утрату ценных вещей ограничена примерно 1600 евро за место багажа.",
            "Items worth more than 10,000 rubles are not recommended for checked baggage. AeroLine's liability for loss of valuables is limited to about 1,600 euros per baggage piece.",
        )

    return _format_by_lang(
        lang,
        "По правилам багажа AeroLine могу уточнить нормы ручной клади и багажа, доплаты, жидкости, пауэрбанки, животных, спортинвентарь, музыкальные инструменты, коляски и запрещённые предметы.",
        "I can help with AeroLine baggage rules: hand luggage and checked baggage allowance, fees, liquids, power banks, pets, sports equipment, musical instruments, strollers, and prohibited items.",
    )