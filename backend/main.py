from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import httpx
import json

from backend.db.database import init_db, get_db
from backend.db.queries import get_flight_info, get_menu, get_commercial_offers


app = FastAPI(title="SkyAssist API")


class ChatRequest(BaseModel):
    message: str
    language: str = "ru"


class ChatResponse(BaseModel):
    response: str


@app.on_event("startup")
async def startup():
    init_db()


@app.get("/")
async def root():
    return {"status": "ok", "service": "SkyAssist"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    # Собираем контекст из БД
    flight = get_flight_info(db)
    menu = get_menu(db)
    offers = get_commercial_offers(db)

    context = f"""
Информация о рейсе:
{json.dumps(flight, ensure_ascii=False, indent=2)}

Меню (эконом-класс):
{json.dumps(menu, ensure_ascii=False, indent=2)}

Специальные предложения:
{json.dumps(offers, ensure_ascii=False, indent=2)}
"""

    system_prompt = f"""Ты — бортовой ассистент авиакомпании AeroLine.
    Ты работаешь на борту воздушного судна во время полёта.
    Отвечай ТОЛЬКО на основе предоставленной информации ниже.
    Не добавляй никаких советов, рекомендаций и информации, которой нет в контексте.
    Если информации нет — скажи: "К сожалению, у меня нет такой информации."
    Отвечай на языке пользователя (русский или английский).
    Будь вежливым и кратким. Все технические термины переводи на язык пользователя. Не добавляй прощальных фраз и предложений обратиться за помощью.
    
    

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
