import logging
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.database import get_db, init_db
from backend.db.queries import get_commercial_offers, get_flight_info, get_menu
from backend.rag.hybrid_retriever import retrieve

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

    MIN_DENSE_SCORE = 0.55
    MIN_BM25_SCORE = 5.0
    top = chunks[0]
    top_dense = top.get("score", 0.0) or 0.0
    top_bm25 = top.get("bm25_score", 0.0) or 0.0
    if top_dense < MIN_DENSE_SCORE and top_bm25 < MIN_BM25_SCORE:
        logger.info(
            "KNOWLEDGE dropped: top dense=%.3f bm25=%.2f below thresholds (%.2f / %.1f)",
            top_dense, top_bm25, MIN_DENSE_SCORE, MIN_BM25_SCORE
        )
        return ""

    lines = ["=== KNOWLEDGE (справочная информация) ==="]
    for chunk in chunks[:RAG_CONTEXT_CHUNKS]:
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


# Системный промпт RU
SYSTEM_PROMPT_RU = """Ты — бортовой ассистент авиакомпании AeroLine.

ИНСТРУКЦИИ:
1. Отвечай на вопрос пассажира, используя ТОЛЬКО факты из блока КОНТЕКСТ ниже.
2. Для вопросов о текущем рейсе, меню, времени вылета/прилёта — используй
   блок FLIGHT. Для вопросов о городах, визах, транспорте, достопримечатель-
   ностях — используй блок KNOWLEDGE.
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

КОНТЕКСТ:
{context}

Вопрос: {question}
Ответ:"""


# Системный промпт EN
SYSTEM_PROMPT_EN = """You are an in-flight assistant for AeroLine airline.

INSTRUCTIONS:
1. Answer the passenger's question using ONLY facts from the CONTEXT below.
2. For questions about the current flight, menu, departure/arrival times —
   use the FLIGHT block. For questions about cities, visas, transport,
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

CONTEXT:
{context}

Question: {question}
Answer:"""


def build_prompt(user_message: str, db: Session) -> str:
    flight_block = build_flight_block(db)
    knowledge_block = build_knowledge_block(user_message)

    blocks = [b for b in (knowledge_block, flight_block) if b]
    context = "\n\n".join(blocks) if blocks else "(контекст отсутствует)"

    lang = detect_language(user_message)
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
