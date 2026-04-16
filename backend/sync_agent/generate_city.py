import json
import requests
from pathlib import Path

KNOWLEDGE_BASE_DIR = Path("data/knowledge_base/cities")
KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)


def generate_city_content(city: str, country: str, iata: str) -> dict:
    # Промпт для практической информации
    practical_prompt = f"""Ты помощник который создаёт структурированную туристическую информацию.
Создай практическую информацию для туриста о городе {city} ({country}).
Отвечай ТОЛЬКО в формате JSON без каких-либо пояснений и markdown.
Формат ответа:
{{
  "currency": "название валюты, код, примерный курс к рублю и доллару",
  "visa": "визовый режим для граждан России",
  "climate": "климат и температура в разные сезоны",
  "airport_transport": "как добраться из аэропорта {iata} до центра города (транспорт, время, стоимость)",
  "tips": "3-4 важных практических совета для туриста"
}}"""

    # Промпт для туристического текста
    content_prompt = f"""Ты опытный travel-журналист. Напиши подробный туристический гид о городе {city} ({country}) для российских туристов.
    Не используй markdown разметку — только чистый текст без **, ## и других символов.
    ВАЖНО: каждый раздел должен быть развёрнутым, не менее 300-400 слов.

    Структура текста:
    1. История и общее описание города (300-400 слов)
    2. Главные достопримечательности — минимум 8-10 мест с подробным описанием каждого (500-700 слов)
    3. Интересные факты о городе (200-300 слов)
    4. Рестораны и местная кухня — что попробовать, рекомендуемые заведения (300-400 слов)
    5. Шопинг и досуг — рынки, торговые центры, развлечения (200-300 слов)
    6. Районы города — краткое описание основных районов (200-300 слов)

    Общий объём — не менее 2000 слов. Пиши развёрнуто и детально."""

    print(f"  Генерация практической информации...")
    practical_response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3.1:8b",
            "prompt": practical_prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 1024
            }
        },
        timeout=120
    )
    practical_text = practical_response.json()["response"]

    # Чистим JSON от возможных markdown артефактов
    practical_text = practical_text.strip()
    if practical_text.startswith("```"):
        practical_text = practical_text.split("```")[1]
        if practical_text.startswith("json"):
            practical_text = practical_text[4:]
    practical_text = practical_text.strip()

    try:
        practical_info = json.loads(practical_text)
    except json.JSONDecodeError:
        print(f"  Ошибка парсинга JSON, используем сырой текст")
        practical_info = {"raw": practical_text}

    print(f"  Генерация туристического текста...")
    content_response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3.1:8b",
            "prompt": content_prompt,
            "stream": False,
            "options": {
                "temperature": 0.5,
                "num_predict": 4096
            }
        },
        timeout=600
    )
    content_text = content_response.json()["response"]
    content_text = content_text.replace("**", "").replace("##", "").replace("# ", "")

    return {
        "title": f"{city} ({iata})",
        "category": "destination",
        "language": "ru",
        "city": city,
        "iata": iata,
        "country": country,
        "practical_info": practical_info,
        "content": content_text
    }


def generate_single_city(city: str, country: str, iata: str):
    print(f"Генерируем информацию о городе {city}...")

    doc = generate_city_content(city, country, iata)

    filename = f"{iata.lower()}.json"
    filepath = KNOWLEDGE_BASE_DIR / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)

    print(f"Сохранено: {filepath}")
    print(f"Длина контента: {len(doc['content'])} символов")
    print(f"\nПрактическая информация:")
    print(json.dumps(doc['practical_info'], ensure_ascii=False, indent=2))
    print(f"\nНачало контента:")
    print(doc['content'][:500])


if __name__ == "__main__":
    # Тест на одном городе
    generate_single_city(
        city="Стамбул",
        country="Турция",
        iata="IST"
    )
