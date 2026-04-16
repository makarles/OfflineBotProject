import logging
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.database import get_db, init_db
from backend.db.queries import get_commercial_offers, get_flight_info, get_menu
from backend.rag.retriever import retrieve

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
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
RAG_CONTEXT_CHUNKS = int(os.getenv("RAG_CONTEXT_CHUNKS", "3"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Инициализация базы данных...")
    init_db()
    logger.info("SkyAssist готов к работе")
    yield
    logger.info("SkyAssist останавливается")


app = FastAPI(title="SkyAssist API", lifespan=lifespan)


# Схемы запроса/ответа
class ChatRequest(BaseModel):
    message: str
    language: str = "ru"


class ChatResponse(BaseModel):
    response: str


# Сборка блока FLIGHT из SQLite
def build_flight_block(db: Session) -> str:
    flight = get_flight_info(db)
    if not flight:
        return ""

    lines = [
        "=== FLIGHT (информация о текущем рейсе) ===",
        f"Рейс: {flight.get('flight_number', '—')}",
        f"Маршрут: {flight.get('origin', '—')} → {flight.get('destination', '—')}",
        f"Вылет: {flight.get('departure_time', '—')}",
        f"Прибытие: {flight.get('arrival_time', '—')}",
        f"Воздушное судно: {flight.get('aircraft_type', '—')} "
        f"(бортовой номер {flight.get('aircraft_reg', '—')})",
        f"Крейсерская высота: {flight.get('cruising_altitude', '—')} м",
        f"Крейсерская скорость: {flight.get('cruising_speed', '—')} км/ч",
    ]

    rf = flight.get("return_flight")
    if rf:
        lines.extend([
            "",
            "Обратный рейс:",
            f"  Рейс: {rf.get('flight_number', '—')}",
            f"  Маршрут: {rf.get('origin', '—')} → {rf.get('destination', '—')}",
            f"  Вылет: {rf.get('departure_time', '—')}",
            f"  Прибытие: {rf.get('arrival_time', '—')}",
        ])

    # Меню
    menu = get_menu(db)
    if menu:
        lines.append("")
        lines.append("Меню (эконом-класс):")
        for item in menu:
            veg = " (вегетарианское)" if item["is_vegetarian"] else ""
            price = "включено в билет" if item["price"] == 0.0 else f"{item['price']} руб."
            lines.append(f"- {item['name']}{veg}: {item['description']} — {price}")

    # Коммерческие предложения
    offers = get_commercial_offers(db)
    if offers:
        lines.append("")
        lines.append("Специальные предложения:")
        for offer in offers:
            lines.append(f"- {offer['title']}: {offer['description']}")

    return "\n".join(lines)


# Сборка блока KNOWLEDGE из RAG
def build_knowledge_block(query: str) -> str:
    chunks = retrieve(query, top_k=RAG_TOP_K)
    if not chunks:
        return ""

    lines = ["=== KNOWLEDGE (справочная информация) ==="]
    for chunk in chunks[:RAG_CONTEXT_CHUNKS]:
        title = chunk.get("title", "")
        text = chunk.get("text", "")
        lines.append(f"[{title}]")
        lines.append(text)
        lines.append("")

    return "\n".join(lines).strip()


# Системный промпт
SYSTEM_PROMPT_TEMPLATE = """Ты — бортовой ассистент авиакомпании AeroLine.
Ты работаешь на борту воздушного судна во время полёта.

СТРОГИЕ ПРАВИЛА:
1. Отвечай ТОЛЬКО на основе информации из блоков FLIGHT и KNOWLEDGE ниже.
2. Если в блоках нет информации для ответа — отвечай: "К сожалению, у меня нет такой информации."
3. Никогда не добавляй данные, которых нет в блоках.
4. Не давай советов и рекомендаций, которых нет в блоках.
5. Не добавляй прощальных фраз и предложений обратиться к экипажу.
6. Отвечай на языке пользователя (русский или английский).
7. Будь кратким и точным.
8. Отвечай грамотными предложениями, избегай дословного перевода технических терминов.
9. Высоту указывай как «крейсерская высота», скорость как «крейсерская скорость».
10. Если блок FLIGHT или KNOWLEDGE отсутствует — не выдумывай его содержимое.

--- КОНТЕКСТ ---
{context}
--- КОНЕЦ КОНТЕКСТА ---"""


def build_prompt(user_message: str, db: Session) -> str:
    flight_block = build_flight_block(db)
    knowledge_block = build_knowledge_block(user_message)

    blocks = [b for b in (flight_block, knowledge_block) if b]
    context = "\n\n".join(blocks) if blocks else "(контекст отсутствует)"

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context)
    return f"{system_prompt}\n\nВопрос пассажира: {user_message}"


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
                    "options": {"temperature": 0.2, "top_p": 0.9},
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


# Эндпоинты
@app.get("/")
async def root():
    return {"status": "ok", "service": "SkyAssist"}


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

    prompt = build_prompt(request.message, db)
    answer = await call_llm(prompt)

    return ChatResponse(response=answer)
