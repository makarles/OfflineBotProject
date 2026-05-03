from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend import chat_db
from backend.db.database import get_db
from backend.rag.route_network import build_route_network_answer, is_route_network_question
from backend.rag.baggage_rules import build_baggage_answer, is_baggage_question

logger = logging.getLogger("skyassist")

router = APIRouter(prefix="/api", tags=["chat"])

_process_message_fn: Callable[[str, Session], Awaitable[str]] | None = None


def register_processor(fn: Callable[[str, Session], Awaitable[str]]) -> None:
    global _process_message_fn
    _process_message_fn = fn
    logger.info("chat_api: зарегистрирован обработчик сообщений")


# Модели запросов/ответов

class SessionCreate(BaseModel):
    title: str | None = Field(None, max_length=200)


class SessionRename(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class MessageFeedbackUpdate(BaseModel):
    feedback: Literal["like", "dislike"] | None = None


class MessageResponse(BaseModel):
    user_message: dict[str, Any]
    assistant_message: dict[str, Any]
    session: dict[str, Any]


# Вспомогательные

def _ensure_session_exists(session_id: str) -> dict[str, Any]:
    session = chat_db.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Сессия {session_id} не найдена")
    return session


def _derive_title(content: str, max_len: int = 50) -> str:
    cleaned = " ".join(content.split())
    if len(cleaned) <= max_len:
        return cleaned
    truncated = cleaned[:max_len].rsplit(" ", 1)[0]
    return truncated + "…"


# Эндпоинты сессий

@router.get("/sessions")
def list_sessions_endpoint() -> list[dict[str, Any]]:
    return chat_db.list_sessions()


@router.post("/sessions", status_code=201)
def create_session_endpoint(payload: SessionCreate | None = None) -> dict[str, Any]:
    title = (payload.title if payload else None) or "Новый чат"
    session_id = chat_db.create_session(title)
    return chat_db.get_session(session_id)


@router.get("/sessions/{session_id}")
def get_session_endpoint(session_id: str) -> dict[str, Any]:
    return _ensure_session_exists(session_id)


@router.patch("/sessions/{session_id}")
def rename_session_endpoint(session_id: str, payload: SessionRename) -> dict[str, Any]:
    _ensure_session_exists(session_id)
    chat_db.rename_session(session_id, payload.title)
    return chat_db.get_session(session_id)


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session_endpoint(session_id: str) -> None:
    _ensure_session_exists(session_id)
    chat_db.delete_session(session_id)


# Эндпоинты сообщений

@router.get("/sessions/{session_id}/messages")
def list_messages_endpoint(session_id: str) -> list[dict[str, Any]]:
    _ensure_session_exists(session_id)
    return chat_db.get_messages(session_id)


@router.patch("/sessions/{session_id}/messages/{message_id}/feedback")
def update_message_feedback_endpoint(
    session_id: str,
    message_id: int,
    payload: MessageFeedbackUpdate,
) -> dict[str, Any]:
    _ensure_session_exists(session_id)
    try:
        message = chat_db.set_message_feedback(session_id, message_id, payload.feedback)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if message is None:
        raise HTTPException(
            status_code=404,
            detail="Ответ ассистента не найден в этой сессии",
        )
    return message


@router.post("/sessions/{session_id}/messages", status_code=201)
async def send_message_endpoint(
    session_id: str,
    payload: MessageCreate,
    db: Session = Depends(get_db),
) -> MessageResponse:
    _ensure_session_exists(session_id)

    if _process_message_fn is None:
        logger.error("chat_api: обработчик сообщений не зарегистрирован")
        raise HTTPException(
            status_code=500,
            detail="Обработчик сообщений не инициализирован",
        )

    # сохранить пользовательское сообщение
    is_first_message = chat_db.count_messages(session_id) == 0
    user_msg_id = chat_db.add_message(session_id, "user", payload.content)

    # если первое сообщение — сделать его заголовком
    if is_first_message:
        new_title = _derive_title(payload.content)
        chat_db.rename_session(session_id, new_title)

    # получить ответ ассистента
    try:
        if is_baggage_question(payload.content):
            assistant_response = build_baggage_answer(payload.content)
        elif is_route_network_question(payload.content):
            assistant_response = build_route_network_answer(payload.content)
        else:
            assistant_response = await _process_message_fn(payload.content, db)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("chat_api: ошибка при обработке сообщения: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка обработки сообщения: {exc}",
        )

    # сохранить ответ ассистента
    assistant_msg_id = chat_db.add_message(session_id, "assistant", assistant_response)

    # собрать финальный ответ
    all_messages = chat_db.get_messages(session_id)
    user_msg = next(m for m in all_messages if m["id"] == user_msg_id)
    assistant_msg = next(m for m in all_messages if m["id"] == assistant_msg_id)
    updated_session = chat_db.get_session(session_id)

    return MessageResponse(
        user_message=user_msg,
        assistant_message=assistant_msg,
        session=updated_session,
    )
