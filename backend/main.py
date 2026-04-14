from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import httpx
import json
import os

from backend.db.database import init_db, get_db
from backend.db.queries import get_flight_info, get_menu, get_commercial_offers
from backend.rag.retriever import retrieve


os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"


app = FastAPI(title="SkyAssist API")


class ChatRequest(BaseModel):
    message: str
    language: str = "ru"


class ChatResponse(BaseModel):
    response: str


# Ключевые слова для маршрутизации
DB_KEYWORDS = [
    "рейс", "вылет", "прилет", "прибытие", "отправление",
    "самолет", "самолёт", "воздушное судно", "высота", "скорость",
    "меню", "еда", "блюдо", "десерт", "напиток", "питание",
    "полет", "полёт", "обратный", "билет",
    "flight", "departure", "arrival", "menu", "food"
]


def is_db_query(message: str) -> bool:
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in DB_KEYWORDS)


@app.on_event("startup")
async def startup():
    init_db()


@app.get("/")
async def root():
    return {"status": "ok", "service": "SkyAssist"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    if is_db_query(request.message):
        flight = get_flight_info(db)
        menu = get_menu(db)
        offers = get_commercial_offers(db)

        # Форматирование информации о рейсе в читаемый текст
        flight_text = f"""Рейс: {flight.get('flight_number', '—')}
    Маршрут: {flight.get('origin', '—')} → {flight.get('destination', '—')}
    Вылет: {flight.get('departure_time', '—')}
    Прибытие: {flight.get('arrival_time', '—')}
    Воздушное судно: {flight.get('aircraft_type', '—')} (бортовой номер {flight.get('aircraft_reg', '—')})
    Крейсерская высота: {flight.get('cruising_altitude', '—')} м
    Крейсерская скорость: {flight.get('cruising_speed', '—')} км/ч"""

        if flight.get('return_flight'):
            rf = flight['return_flight']
            flight_text += f"""

    Обратный рейс: {rf.get('flight_number', '—')}
    Маршрут: {rf.get('origin', '—')} → {rf.get('destination', '—')}
    Вылет: {rf.get('departure_time', '—')}
    Прибытие: {rf.get('arrival_time', '—')}"""

        # Форматирование меню
        menu_text = "Меню (эконом-класс):\n"
        for item in menu:
            veg = " (вегетарианское)" if item['is_vegetarian'] else ""
            price = "включено в билет" if item['price'] == 0.0 else f"{item['price']} руб."
            menu_text += f"- {item['name']}{veg}: {item['description']} — {price}\n"

        # Форматирование предложения
        offers_text = "Специальные предложения:\n"
        for offer in offers:
            offers_text += f"- {offer['title']}: {offer['description']}\n"

        context = f"{flight_text}\n\n{menu_text}\n{offers_text}"

    system_prompt = f"""Ты — бортовой ассистент авиакомпании AeroLine.
Ты работаешь на борту воздушного судна во время полёта.

СТРОГИЕ ПРАВИЛА:
1. Отвечай ТОЛЬКО на основе информации из контекста ниже.
2. Если информации нет в контексте — отвечай: "К сожалению, у меня нет такой информации."
3. Никогда не добавляй данные которых нет в контексте.
4. Не давай советов и рекомендаций которых нет в контексте.
5. Не добавляй прощальных фраз и предложений обратиться к экипажу.
6. Переводи все термины на язык пользователя.
7. Отвечай на языке пользователя (русский или английский).
8. Будь кратким и точным.
9. Отвечай грамотными русскими предложениями, избегай дословного перевода технических терминов.
10. Высоту указывай как «крейсерская высота», скорость как «крейсерская скорость».

{context}"""

    prompt = f"{system_prompt}\n\nВопрос пассажира: {request.message}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        result = await client.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.1:8b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "top_p": 0.9
                }
            }
        )
    data = result.json()
    return ChatResponse(response=data["response"])
