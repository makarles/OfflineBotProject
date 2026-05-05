import logging
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend import chat_db
from backend.api import chat as chat_api
from backend.api import sync as sync_api
from backend.db.database import get_db, init_db
from backend.db.models import CommercialOffer, Flight, MenuItem
from backend.db.queries import get_commercial_offers, get_flight_info, get_menu
from backend.rag.city_filter import filter_by_city
from backend.rag.route_network import build_route_network_block
from backend.rag.hybrid_retriever import retrieve
from backend.rag.reranker import rerank

os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

logger = logging.getLogger("skyassist")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

# Конфиг LLM
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "60"))

# Конфиг RAG
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "6"))
RAG_CONTEXT_CHUNKS = int(os.getenv("RAG_CONTEXT_CHUNKS", "10"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Инициализация базы данных...")
    init_db()
    chat_db.init_db()
    logger.info("SkyAssist готов к работе")
    yield
    logger.info("SkyAssist останавливается")


app = FastAPI(title="SkyAssist API", lifespan=lifespan)


# Схемы запроса/ответа
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


# Сборка блока FLIGHT из SQLite
def _format_menu_item(item: MenuItem, lang: str = "ru") -> str:
    if lang == "en":
        name = item.name_en or item.name_ru or "Menu"
        description = item.description_en or item.description_ru or ""
        price = "included in the ticket" if not item.price else f"{item.price:g} RUB"
    else:
        name = item.name_ru or item.name_en or "Меню"
        description = item.description_ru or item.description_en or ""
        price = "включено в билет" if not item.price else f"{item.price:g} руб."

    if description:
        return f"- {name}: {description} — {price}"

    return f"- {name} — {price}"


def build_flight_block(db: Session, lang: str = "ru") -> str:
    flight_obj = db.query(Flight).first()
    if not flight_obj:
        return ""

    route = flight_obj.route
    aircraft = flight_obj.aircraft
    is_domestic = bool(route.is_domestic) if route else False

    origin = route.origin_city if route else "—"
    destination = route.destination_city if route else "—"

    if lang == "en":
        lines = [
            "=== FLIGHT (current flight information) ===",
            f"Flight: {flight_obj.flight_number}",
            f"Route: {origin} → {destination}",
            f"Flight type: {'domestic' if is_domestic else 'international'}",
            f"Departure: {flight_obj.departure_time}",
            f"Arrival: {flight_obj.arrival_time}",
            f"Aircraft: {aircraft.aircraft_type if aircraft else '—'} "
            f"(registration {aircraft.registration if aircraft else '—'})",
            f"Cruising altitude: {flight_obj.cruising_altitude or '—'} m",
            f"Cruising speed: {flight_obj.cruising_speed or '—'} km/h",
        ]
    else:
        lines = [
            "=== FLIGHT (информация о текущем рейсе) ===",
            f"Рейс: {flight_obj.flight_number}",
            f"Маршрут: {origin} → {destination}",
            f"Тип рейса: {'внутренний' if is_domestic else 'международный'}",
            f"Вылет: {flight_obj.departure_time}",
            f"Прибытие: {flight_obj.arrival_time}",
            f"Воздушное судно: {aircraft.aircraft_type if aircraft else '—'} "
            f"(бортовой номер {aircraft.registration if aircraft else '—'})",
            f"Крейсерская высота: {flight_obj.cruising_altitude or '—'} м",
            f"Крейсерская скорость: {flight_obj.cruising_speed or '—'} км/ч",
        ]

    if flight_obj.weather_description_ru or flight_obj.weather_description_en or flight_obj.weather_temp_celsius is not None:
        weather_parts = []

        if lang == "en":
            weather_description = flight_obj.weather_description_en or flight_obj.weather_description_ru
        else:
            weather_description = flight_obj.weather_description_ru or flight_obj.weather_description_en

        if weather_description:
            weather_parts.append(weather_description)

        if flight_obj.weather_temp_celsius is not None:
            temp_text = f"{flight_obj.weather_temp_celsius:+d}°C"
            if temp_text not in " ".join(weather_parts):
                weather_parts.append(temp_text)

        if lang == "en":
            lines.extend([
                "",
                f"Current weather at destination ({destination}): " + ", ".join(weather_parts),
            ])
        else:
            lines.extend([
                "",
                f"Текущая погода в пункте назначения ({destination}): " + ", ".join(weather_parts),
            ])

    if is_domestic:
        if lang == "en":
            lines.extend([
                "",
                "Exchange rate: this is a domestic flight, so exchange rate information is not used for the destination.",
            ])
        else:
            lines.extend([
                "",
                "Курс валюты: рейс внутренний, курс валют для пункта назначения не используется.",
            ])
    else:
        exchange_text = None

        if lang == "en":
            if flight_obj.exchange_rate_note_en:
                exchange_text = flight_obj.exchange_rate_note_en
            elif flight_obj.exchange_rate_note_ru:
                exchange_text = flight_obj.exchange_rate_note_ru
        else:
            if flight_obj.exchange_rate_note_ru:
                exchange_text = flight_obj.exchange_rate_note_ru
            elif flight_obj.exchange_rate_note_en:
                exchange_text = flight_obj.exchange_rate_note_en

        if not exchange_text and flight_obj.exchange_rate_currency and flight_obj.exchange_rate_to_rub:
            if lang == "en":
                exchange_text = (
                    f"1 {flight_obj.exchange_rate_currency} = "
                    f"{flight_obj.exchange_rate_to_rub:g} RUB"
                )
            else:
                exchange_text = (
                    f"1 {flight_obj.exchange_rate_currency} = "
                    f"{flight_obj.exchange_rate_to_rub:g} ₽"
                )

        if exchange_text:
            if lang == "en":
                lines.extend([
                    "",
                    f"Exchange rate at destination: {exchange_text}",
                ])
            else:
                lines.extend([
                    "",
                    f"Курс валюты для пункта назначения: {exchange_text}",
                ])

    if flight_obj.return_flight_number:
        if lang == "en":
            lines.extend([
                "",
                "Return flight:",
                f"  Flight: {flight_obj.return_flight_number}",
                f"  Route: {destination} → {origin}",
                f"  Departure: {flight_obj.return_departure_time or '—'}",
                f"  Arrival: {flight_obj.return_arrival_time or '—'}",
            ])
        else:
            lines.extend([
                "",
                "Обратный рейс:",
                f"  Рейс: {flight_obj.return_flight_number}",
                f"  Маршрут: {destination} → {origin}",
                f"  Вылет: {flight_obj.return_departure_time or '—'}",
                f"  Прибытие: {flight_obj.return_arrival_time or '—'}",
            ])

    menu_items = (
        db.query(MenuItem)
        .filter(MenuItem.flight_id == flight_obj.id)
        .order_by(MenuItem.cabin_class.asc(), MenuItem.id.asc())
        .all()
    )

    economy_menu = [item for item in menu_items if item.cabin_class == "economy"]
    business_menu = [item for item in menu_items if item.cabin_class == "business"]

    if economy_menu:
        lines.append("")
        lines.append("Economy class meal:" if lang == "en" else "Питание эконом-класса:")
        for item in economy_menu:
            lines.append(_format_menu_item(item, lang))

    if business_menu:
        lines.append("")
        lines.append("Business class meal:" if lang == "en" else "Питание бизнес-класса:")
        for item in business_menu:
            lines.append(_format_menu_item(item, lang))

    offers = db.query(CommercialOffer).filter(CommercialOffer.flight_id == flight_obj.id).all()
    if offers:
        lines.append("")
        lines.append("Special offers:" if lang == "en" else "Специальные предложения:")

        for offer in offers:
            if lang == "en":
                title = offer.title_en or offer.title_ru or "Offer"
                description = offer.description_en or offer.description_ru or ""
            else:
                title = offer.title_ru or offer.title_en or "Предложение"
                description = offer.description_ru or offer.description_en or ""

            lines.append(f"- {title}: {description}")

    return "\n".join(lines)


# Сборка блока KNOWLEDGE из RAG
def build_knowledge_block(query: str) -> str:
    candidates = retrieve(query, top_k=20)

    if not candidates:
        return ""

    candidates = filter_by_city(query, candidates)

    if not candidates:
        logger.info("KNOWLEDGE dropped: no chunks for mentioned city")
        return ""

    chunks = rerank(query, candidates, top_k=RAG_CONTEXT_CHUNKS)

    MIN_RERANK_SCORE = 0.30
    top_score = chunks[0].get("rerank_score", 0.0)
    if top_score < MIN_RERANK_SCORE:
        logger.info(
            "KNOWLEDGE dropped: top rerank_score=%.3f < %.2f",
            top_score, MIN_RERANK_SCORE
        )
        return ""

    logger.info("KNOWLEDGE top-%d chunks", len(chunks))
    for i, chunk in enumerate(chunks):
        text_preview = chunk.get("text", "")[:200].replace("\n", " ")
        logger.info(
            "  top[%d] rerank=%.3f city=%s section=%s | %s",
            i,
            chunk.get("rerank_score", 0.0),
            chunk.get("city", "-") or "-",
            chunk.get("section", "-"),
            text_preview,
        )

    lines = ["KNOWLEDGE (справочная информация)"]
    for chunk in chunks:
        title = chunk.get("title", "")
        text = chunk.get("text", "")
        lines.append(f"[{title}]")
        lines.append(text)
        lines.append("")

    return "\n".join(lines).strip()


# Определение языка пользователя
def detect_language(text: str) -> str:
    if not text:
        return "ru"
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "ru"
    cyrillic = sum(1 for c in letters if "\u0400" <= c <= "\u04FF")
    return "ru" if cyrillic / len(letters) > 0.3 else "en"


SYSTEM_PROMPT_RU = """Ты — бортовой ассистент авиакомпании AeroLine.

ИНСТРУКЦИИ:
1. Отвечай на вопрос пассажира, используя ТОЛЬКО факты из блока КОНТЕКСТ ниже.
2. Для вопросов о текущем рейсе, меню, времени вылета/прилёта — используй
   блок FLIGHT. Для вопросов о маршрутной сети AeroLine, направлениях,
   городах полётов, внутренних и международных маршрутах — используй
   блок ROUTE_NETWORK. Для вопросов о городах, визах, транспорте,
   достопримечательностях — используй блок KNOWLEDGE.
3. Если в контексте есть подходящая информация — давай прямой, полезный ответ.
   Не начинай ответ с оговорок о том, что есть или чего нет в контексте.
4. Используй ТОЛЬКО те названия, места, цены и факты, которые буквально
   написаны в контексте. Не добавляй достопримечательности, музеи или детали
   из своих общих знаний — даже если они известные или скорее всего верные.
5. Если в контексте ничего нет по теме, кратко скажи что у тебя нет такой
   информации — и остановись. Не отвечай дальше.
6. Отвечай ТОЛЬКО на русском языке. Будь кратким: 2-5 предложений или
   короткие маркеры для списков.
7. Не добавляй прощальных фраз и предложений обратиться к экипажу.
8. Высоту указывай как «крейсерская высота», скорость — «крейсерская скорость».
9. Для вопросов о ТЕКУЩЕЙ погоде, температуре, курсе валют — используй ТОЛЬКО блок FLIGHT.
   В блоке KNOWLEDGE содержатся общеклиматические сведения по сезонам — не используй
   их как ответ на вопрос «какая погода сейчас» или «сколько градусов».
10. Не пиши слово "KNOWLEDGE" в ответе.
   
КОНТЕКСТ:
{context}

Вопрос: {question}
Ответ:"""


SYSTEM_PROMPT_EN = """You are an in-flight assistant for AeroLine airline.

INSTRUCTIONS:
1. Answer the passenger's question using ONLY facts from the CONTEXT below.
2. For questions about the current flight, menu, departure/arrival times —
   use the FLIGHT block. For questions about AeroLine route network,
   destinations, domestic routes, and international routes — use the
   ROUTE_NETWORK block. For questions about cities, visas, transport,
   attractions — use the KNOWLEDGE block.
3. If the context contains relevant information — give a direct, helpful answer.
   Do not preface your answer with disclaimers about what the context does or
   does not contain.
4. Use ONLY names, places, prices and facts that are literally written in the
   context. Never add landmarks, museums, or details from your general
   knowledge — even if they are famous or likely correct.
5. If the context has nothing on the topic, briefly say you don't have that
   information and stop. Do not then proceed to answer anyway.
6. Reply ONLY in English. Be concise: 2-5 sentences, or short bullet points
   for lists.
7. Do not add farewells or suggestions to contact the crew.
8. Use "cruising altitude" and "cruising speed" for altitude and speed.
9. For questions about CURRENT weather, temperature, or exchange rates — use 
   ONLY the FLIGHT block. The KNOWLEDGE block contains seasonal climate 
   information and general currency facts — these are NOT answers to questions 
   like "what's the weather now" or "how many degrees".
10. Do not write "KNOWLEDGE" in your answer.

CONTEXT:
{context}

Question: {question}
Answer:"""


def build_prompt(user_message: str, db: Session) -> str:
    lang = detect_language(user_message)

    route_network_block = build_route_network_block(user_message)
    flight_block = build_flight_block(db, lang)
    knowledge_block = build_knowledge_block(user_message)

    blocks = [b for b in (route_network_block, knowledge_block, flight_block) if b]
    context = "\n\n".join(blocks) if blocks else "(контекст отсутствует)"

    template = SYSTEM_PROMPT_EN if lang == "en" else SYSTEM_PROMPT_RU
    logger.info("Detected language: %s", lang)
    return template.format(context=context, question=user_message)


# Вызов Ollama
async def call_llm(prompt: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            result = await client.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "top_p": 0.9},
                },
            )
            result.raise_for_status()
            data = result.json()
            return data.get("response", "").strip()
    except httpx.TimeoutException:
        logger.error("Ollama timeout")
        raise HTTPException(
            status_code=504,
            detail="Сервис ассистента не ответил вовремя. Попробуйте ещё раз.",
        )
    except httpx.HTTPError as e:
        logger.error("Ollama HTTP error: %s", e)
        raise HTTPException(
            status_code=503,
            detail="Сервис ассистента временно недоступен. Обратитесь к бортпроводнику.",
        )


async def process_message(message: str, db: Session) -> str:
    prompt = build_prompt(message, db)
    return await call_llm(prompt)


chat_api.register_processor(process_message)

app.include_router(chat_api.router)

app.include_router(sync_api.router)

# Статика (CSS, JS) и шаблоны (HTML) для UI
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")


# Эндпоинты
@app.get("/", response_class=HTMLResponse)
async def chat_ui(request: Request):
    return templates.TemplateResponse(request, "chat.html")


@app.get("/health")
async def health(db: Session = Depends(get_db)):
    flight = get_flight_info(db)
    return {
        "status": "ok",
        "flight_loaded": bool(flight),
        "flight_number": flight.get("flight_number") if flight else None,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    logger.info("Запрос: %s", request.message[:120])
    answer = await process_message(request.message, db)
    return ChatResponse(response=answer)
