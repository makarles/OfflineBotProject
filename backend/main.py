from fastapi import FastAPI
from pydantic import BaseModel
import httpx

app = FastAPI(title="SkyAssist API")


class ChatRequest(BaseModel):
    message: str
    language: str = "ru"


class ChatResponse(BaseModel):
    response: str


@app.get("/")
async def root():
    return {"status": "ok", "service": "SkyAssist"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    async with httpx.AsyncClient(timeout=60.0) as client:
        result = await client.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.1:8b",
                "prompt": request.message,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "top_p": 0.9
                }
            }
        )
    data = result.json()
    return ChatResponse(response=data["response"])
