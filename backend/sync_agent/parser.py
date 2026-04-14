import requests
import json
import time
from pathlib import Path
from bs4 import BeautifulSoup


KNOWLEDGE_BASE_DIR = Path("data/knowledge_base/cities")
KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)


# Все наши направления
CITIES = [
    # Российские города
    {"city": "Москва", "iata": "SVO", "country": "Россия",
     "wikivoyage": "Москва", "lang": "ru"},
    {"city": "Санкт-Петербург", "iata": "LED", "country": "Россия",
     "wikivoyage": "Санкт-Петербург", "lang": "ru"},
    {"city": "Сочи", "iata": "AER", "country": "Россия",
     "wikivoyage": "Сочи", "lang": "ru"},
    {"city": "Екатеринбург", "iata": "SVX", "country": "Россия",
     "wikivoyage": "Екатеринбург", "lang": "ru"},
    {"city": "Казань", "iata": "KZN", "country": "Россия",
     "wikivoyage": "Казань", "lang": "ru"},
    {"city": "Новосибирск", "iata": "OVB", "country": "Россия",
     "wikivoyage": "Новосибирск", "lang": "ru"},
    {"city": "Владивосток", "iata": "VVO", "country": "Россия",
     "wikivoyage": "Владивосток", "lang": "ru"},
    {"city": "Краснодар", "iata": "KRR", "country": "Россия",
     "wikivoyage": "Краснодар", "lang": "ru"},
    {"city": "Уфа", "iata": "UFA", "country": "Россия",
     "wikivoyage": "Уфа", "lang": "ru"},
    {"city": "Ростов-на-Дону", "iata": "ROV", "country": "Россия",
     "wikivoyage": "Ростов-на-Дону", "lang": "ru"},
    {"city": "Нижний Новгород", "iata": "GOJ", "country": "Россия",
     "wikivoyage": "Нижний_Новгород", "lang": "ru"},
    {"city": "Самара", "iata": "KUF", "country": "Россия",
     "wikivoyage": "Самара", "lang": "ru"},
    {"city": "Омск", "iata": "OMS", "country": "Россия",
     "wikivoyage": "Омск", "lang": "ru"},
    {"city": "Иркутск", "iata": "IKT", "country": "Россия",
     "wikivoyage": "Иркутск", "lang": "ru"},
    {"city": "Хабаровск", "iata": "KHV", "country": "Россия",
     "wikivoyage": "Хабаровск", "lang": "ru"},
    {"city": "Красноярск", "iata": "KJA", "country": "Россия",
     "wikivoyage": "Красноярск", "lang": "ru"},
    {"city": "Пермь", "iata": "PEE", "country": "Россия",
     "wikivoyage": "Пермь", "lang": "ru"},
    {"city": "Воронеж", "iata": "VOZ", "country": "Россия",
     "wikivoyage": "Воронеж", "lang": "ru"},
    {"city": "Калининград", "iata": "KGD", "country": "Россия",
     "wikivoyage": "Калининград", "lang": "ru"},
    {"city": "Тюмень", "iata": "TJM", "country": "Россия",
     "wikivoyage": "Тюмень", "lang": "ru"},
    {"city": "Мурманск", "iata": "MMK", "country": "Россия",
     "wikivoyage": "Мурманск", "lang": "ru"},
    # Международные города
    {"city": "Дубай", "iata": "DXB", "country": "ОАЭ",
     "wikivoyage": "Дубай", "lang": "ru"},
    {"city": "Стамбул", "iata": "IST", "country": "Турция",
     "wikivoyage": "Стамбул", "lang": "ru"},
    {"city": "Анталья", "iata": "AYT", "country": "Турция",
     "wikivoyage": "Анталья", "lang": "ru"},
    {"city": "Пекин", "iata": "PEK", "country": "Китай",
     "wikivoyage": "Пекин", "lang": "ru"},
    {"city": "Бангкок", "iata": "BKK", "country": "Таиланд",
     "wikivoyage": "Бангкок", "lang": "ru"},
    {"city": "Дели", "iata": "DEL", "country": "Индия",
     "wikivoyage": "Дели", "lang": "ru"},
    {"city": "Ереван", "iata": "EVN", "country": "Армения",
     "wikivoyage": "Ереван", "lang": "ru"},
    {"city": "Тбилиси", "iata": "TBS", "country": "Грузия",
     "wikivoyage": "Тбилиси", "lang": "ru"},
    {"city": "Алматы", "iata": "ALA", "country": "Казахстан",
     "wikivoyage": "Алматы", "lang": "ru"},
    {"city": "Ташкент", "iata": "TAS", "country": "Узбекистан",
     "wikivoyage": "Ташкент", "lang": "ru"},
    {"city": "Баку", "iata": "GYD", "country": "Азербайджан",
     "wikivoyage": "Баку", "lang": "ru"},
    {"city": "Минск", "iata": "MSQ", "country": "Беларусь",
     "wikivoyage": "Минск", "lang": "ru"},
    {"city": "Бишкек", "iata": "FRU", "country": "Кыргызстан",
     "wikivoyage": "Бишкек", "lang": "ru"},
    {"city": "Астана", "iata": "NQZ", "country": "Казахстан",
     "wikivoyage": "Астана", "lang": "ru"},
    {"city": "Самарканд", "iata": "SKD", "country": "Узбекистан",
     "wikivoyage": "Самарканд", "lang": "ru"},
    {"city": "Коломбо", "iata": "CMB", "country": "Шри-Ланка",
     "wikivoyage": "Коломбо", "lang": "ru"},
    {"city": "Мале", "iata": "MLE", "country": "Мальдивы",
     "wikivoyage": "Мале", "lang": "ru"},
    {"city": "Катманду", "iata": "KTM", "country": "Непал",
     "wikivoyage": "Катманду", "lang": "ru"},
    {"city": "Денпасар", "iata": "DPS", "country": "Индонезия",
     "wikivoyage": "Денпасар", "lang": "ru"},
    {"city": "Гоа", "iata": "GOI", "country": "Индия",
     "wikivoyage": "Гоа", "lang": "ru"},
    {"city": "Хургада", "iata": "HRG", "country": "Египет",
     "wikivoyage": "Хургада", "lang": "ru"},
    {"city": "Шарм-эш-Шейх", "iata": "SSH", "country": "Египет",
     "wikivoyage": "Шарм-эш-Шейх", "lang": "ru"},
    {"city": "Пхукет", "iata": "HKT", "country": "Таиланд",
     "wikivoyage": "Пхукет", "lang": "ru"},
    {"city": "Куала-Лумпур", "iata": "KUL", "country": "Малайзия",
     "wikivoyage": "Куала-Лумпур", "lang": "ru"},
    {"city": "Абу-Даби", "iata": "AUH", "country": "ОАЭ",
     "wikivoyage": "Абу-Даби", "lang": "ru"},
]


def parse_wikivoyage(city_name: str, lang: str = "ru") -> str:
    url = f"https://{lang}.wikivoyage.org/wiki/{city_name}"
    headers = {"User-Agent": "SkyAssist-Bot/1.0 (educational project)"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return ""

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup.find_all(["script", "style", "sup"]):
            tag.decompose()

        content_div = soup.find("div", class_="mw-parser-output")
        if not content_div:
            return ""

        # Берём весь текст напрямую
        full_text = content_div.get_text(separator=" ", strip=True)
        print(f"  Текст (первые 300 символов): {full_text[:300]}")

        return full_text[:3000] if full_text else ""

    except Exception as e:
        print(f"Ошибка при парсинге {city_name}: {e}")
        return ""


def parse_all_cities():
    print(f"Начинаем парсинг {len(CITIES)} городов...")
    success = 0
    failed = []

    for i, city in enumerate(CITIES):
        print(f"[{i+1}/{len(CITIES)}] Парсим {city['city']}...")

        content = parse_wikivoyage(city["wikivoyage"], city["lang"])

        if content:
            doc = {
                "title": f"{city['city']} ({city['iata']})",
                "category": "destination",
                "language": "ru",
                "city": city["city"],
                "iata": city["iata"],
                "country": city["country"],
                "content": content
            }

            filename = f"{city['iata'].lower()}.json"
            filepath = KNOWLEDGE_BASE_DIR / filename

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)

            print(f"  ✓ Сохранено: {filepath} ({len(content)} символов)")
            success += 1
        else:
            print(f"  ✗ Не удалось получить данные")
            failed.append(city["city"])

        # Пауза чтобы не перегружать сервер
        time.sleep(1)

    print(f"\nГотово: {success}/{len(CITIES)} городов")
    if failed:
        print(f"Не удалось: {', '.join(failed)}")


if __name__ == "__main__":
    parse_all_cities()
