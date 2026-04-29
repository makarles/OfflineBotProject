from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import Aircraft, CommercialOffer, Flight, MenuItem, Route
from backend.db.queries import (
    get_flight_info,
    list_aircraft,
    list_routes,
    suggest_meal_type,
    validate_menu_for_meal_type,
)

logger = logging.getLogger("skyassist")

router = APIRouter(prefix="/api/admin", tags=["admin"])


# Pydantic-модели

class MenuItemPayload(BaseModel):
    name_ru: str = Field(..., min_length=1, max_length=200)
    name_en: str | None = Field(None, max_length=200)
    description_ru: str | None = Field(None, max_length=500)
    description_en: str | None = Field(None, max_length=500)
    category: str = Field(..., pattern="^(main|starter|dessert|drink|snack)$")
    cabin_class: str = Field(..., pattern="^(economy|business)$")
    is_vegetarian: bool = False
    price: float = 0.0


class CommercialOfferPayload(BaseModel):
    title_ru: str = Field(..., min_length=1, max_length=200)
    title_en: str | None = Field(None, max_length=200)
    description_ru: str | None = Field(None, max_length=500)
    description_en: str | None = Field(None, max_length=500)
    category: str | None = Field(None, max_length=50)


class FlightUpdatePayload(BaseModel):
    flight_number: str = Field(..., min_length=1, max_length=20)
    departure_time: str = Field(..., min_length=1, max_length=50)
    arrival_time: str = Field(..., min_length=1, max_length=50)
    aircraft_id: int
    route_id: int
    cruising_altitude: int | None = None
    cruising_speed: int | None = None
    meal_type: str = Field(..., pattern="^(full|light|snack_only|no_meal)$")

    # Обратный рейс (опционально)
    return_flight_number: str | None = Field(None, max_length=20)
    return_departure_time: str | None = Field(None, max_length=50)
    return_arrival_time: str | None = Field(None, max_length=50)

    # Погода
    weather_description_ru: str | None = Field(None, max_length=200)
    weather_description_en: str | None = Field(None, max_length=200)
    weather_temp_celsius: int | None = None

    # Курс валюты
    exchange_rate_currency: str | None = Field(None, max_length=10)
    exchange_rate_to_rub: float | None = None
    exchange_rate_note_ru: str | None = Field(None, max_length=100)
    exchange_rate_note_en: str | None = Field(None, max_length=100)

    # Меню и предложения (не отдельные эндпоинты — управляются вместе с рейсом)
    menu_items: list[MenuItemPayload] = []
    commercial_offers: list[CommercialOfferPayload] = []


class AircraftPayload(BaseModel):
    registration: str = Field(..., min_length=1, max_length=20)
    aircraft_type: str = Field(..., min_length=1, max_length=50)
    manufacturer: str | None = Field(None, max_length=50)
    capacity_economy: int | None = None
    capacity_business: int | None = None
    year_manufactured: int | None = None
    status: str = Field("active", pattern="^(active|maintenance)$")


class RoutePayload(BaseModel):
    origin_city: str = Field(..., min_length=1, max_length=100)
    origin_iata: str = Field(..., min_length=3, max_length=4)
    origin_country: str | None = Field(None, max_length=100)
    destination_city: str = Field(..., min_length=1, max_length=100)
    destination_iata: str = Field(..., min_length=3, max_length=4)
    destination_country: str | None = Field(None, max_length=100)
    is_domestic: bool = False
    flight_duration_min: int | None = None
    distance_km: int | None = None


# Эндпоинты рейса

@router.get("/flight")
def get_flight_endpoint(db: Session = Depends(get_db)) -> dict[str, Any]:
    flight = db.query(Flight).first()

    if not flight:
        return {
            "flight": None,
            "menu_items": [],
            "commercial_offers": [],
        }

    # Меню обоих классов
    menu_items = db.query(MenuItem).filter(MenuItem.flight_id == flight.id).all()
    menu_payload = [
        {
            "id": m.id,
            "name_ru": m.name_ru,
            "name_en": m.name_en,
            "description_ru": m.description_ru,
            "description_en": m.description_en,
            "category": m.category,
            "cabin_class": m.cabin_class,
            "is_vegetarian": bool(m.is_vegetarian),
            "price": m.price,
        }
        for m in menu_items
    ]

    # Коммерческие предложения
    offers = db.query(CommercialOffer).filter(CommercialOffer.flight_id == flight.id).all()
    offers_payload = [
        {
            "id": o.id,
            "title_ru": o.title_ru,
            "title_en": o.title_en,
            "description_ru": o.description_ru,
            "description_en": o.description_en,
            "category": o.category,
        }
        for o in offers
    ]

    return {
        "flight": {
            "id": flight.id,
            "flight_number": flight.flight_number,
            "departure_time": flight.departure_time,
            "arrival_time": flight.arrival_time,
            "aircraft_id": flight.aircraft_id,
            "route_id": flight.route_id,
            "cruising_altitude": flight.cruising_altitude,
            "cruising_speed": flight.cruising_speed,
            "meal_type": flight.meal_type,
            "return_flight_number": flight.return_flight_number,
            "return_departure_time": flight.return_departure_time,
            "return_arrival_time": flight.return_arrival_time,
            "weather_description_ru": flight.weather_description_ru,
            "weather_description_en": flight.weather_description_en,
            "weather_temp_celsius": flight.weather_temp_celsius,
            "exchange_rate_currency": flight.exchange_rate_currency,
            "exchange_rate_to_rub": flight.exchange_rate_to_rub,
            "exchange_rate_note_ru": flight.exchange_rate_note_ru,
            "exchange_rate_note_en": flight.exchange_rate_note_en,
        },
        "menu_items": menu_payload,
        "commercial_offers": offers_payload,
    }


@router.put("/flight")
def update_flight_endpoint(
        payload: FlightUpdatePayload,
        db: Session = Depends(get_db),
) -> dict[str, Any]:
    # Проверка справочников
    aircraft = db.query(Aircraft).filter(Aircraft.id == payload.aircraft_id).first()
    if not aircraft:
        raise HTTPException(404, f"Aircraft id={payload.aircraft_id} не найден")

    route = db.query(Route).filter(Route.id == payload.route_id).first()
    if not route:
        raise HTTPException(404, f"Route id={payload.route_id} не найден")

    # Валидация меню по meal_type — отдельно для эконома и бизнеса
    economy_menu = [m.dict() for m in payload.menu_items if m.cabin_class == "economy"]
    business_menu = [m.dict() for m in payload.menu_items if m.cabin_class == "business"]

    errors = []
    errors.extend(validate_menu_for_meal_type(economy_menu, payload.meal_type, "economy"))
    errors.extend(validate_menu_for_meal_type(business_menu, payload.meal_type, "business"))

    if errors:
        raise HTTPException(
            status_code=400,
            detail={"message": "Меню не соответствует типу питания", "errors": errors},
        )

    # Удаляем старые данные (один Flight, его меню и предложения)
    old_flight = db.query(Flight).first()
    if old_flight:
        db.query(MenuItem).filter(MenuItem.flight_id == old_flight.id).delete()
        db.query(CommercialOffer).filter(CommercialOffer.flight_id == old_flight.id).delete()
        db.delete(old_flight)
        db.flush()

    # Создаём новый Flight
    flight = Flight(
        flight_number=payload.flight_number,
        departure_time=payload.departure_time,
        arrival_time=payload.arrival_time,
        aircraft_id=payload.aircraft_id,
        route_id=payload.route_id,
        cruising_altitude=payload.cruising_altitude,
        cruising_speed=payload.cruising_speed,
        meal_type=payload.meal_type,
        return_flight_number=payload.return_flight_number,
        return_departure_time=payload.return_departure_time,
        return_arrival_time=payload.return_arrival_time,
        weather_description_ru=payload.weather_description_ru,
        weather_description_en=payload.weather_description_en,
        weather_temp_celsius=payload.weather_temp_celsius,
        exchange_rate_currency=payload.exchange_rate_currency,
        exchange_rate_to_rub=payload.exchange_rate_to_rub,
        exchange_rate_note_ru=payload.exchange_rate_note_ru,
        exchange_rate_note_en=payload.exchange_rate_note_en,
    )
    db.add(flight)
    db.flush()

    # Меню
    for m in payload.menu_items:
        db.add(MenuItem(
            flight_id=flight.id,
            name_ru=m.name_ru,
            name_en=m.name_en,
            description_ru=m.description_ru,
            description_en=m.description_en,
            category=m.category,
            cabin_class=m.cabin_class,
            is_vegetarian=int(m.is_vegetarian),
            price=m.price,
        ))

    # Коммерческие предложения
    for o in payload.commercial_offers:
        db.add(CommercialOffer(
            flight_id=flight.id,
            title_ru=o.title_ru,
            title_en=o.title_en,
            description_ru=o.description_ru,
            description_en=o.description_en,
            category=o.category,
        ))

    db.commit()
    logger.info("admin: рейс %s обновлён", payload.flight_number)

    return {"status": "ok", "flight_id": flight.id}


@router.get("/flight/suggest-meal-type")
def suggest_meal_type_endpoint(route_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(404, f"Route id={route_id} не найден")

    suggested = suggest_meal_type(route.flight_duration_min)
    return {
        "meal_type": suggested,
        "duration_min": route.flight_duration_min or 0,
    }


# Эндпоинты бортов

@router.get("/aircraft")
def list_aircraft_endpoint(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return list_aircraft(db)


@router.post("/aircraft", status_code=201)
def create_aircraft_endpoint(
        payload: AircraftPayload,
        db: Session = Depends(get_db),
) -> dict[str, Any]:
    # Проверка уникальности registration
    existing = db.query(Aircraft).filter(Aircraft.registration == payload.registration).first()
    if existing:
        raise HTTPException(409, f"Борт {payload.registration} уже существует")

    aircraft = Aircraft(**payload.dict())
    db.add(aircraft)
    db.commit()
    db.refresh(aircraft)
    return {"id": aircraft.id, "registration": aircraft.registration}


@router.put("/aircraft/{aircraft_id}")
def update_aircraft_endpoint(
        aircraft_id: int,
        payload: AircraftPayload,
        db: Session = Depends(get_db),
) -> dict[str, Any]:
    aircraft = db.query(Aircraft).filter(Aircraft.id == aircraft_id).first()
    if not aircraft:
        raise HTTPException(404, f"Aircraft id={aircraft_id} не найден")

    for field, value in payload.dict().items():
        setattr(aircraft, field, value)
    db.commit()
    return {"id": aircraft.id}


@router.delete("/aircraft/{aircraft_id}", status_code=204)
def delete_aircraft_endpoint(aircraft_id: int, db: Session = Depends(get_db)) -> None:
    aircraft = db.query(Aircraft).filter(Aircraft.id == aircraft_id).first()
    if not aircraft:
        raise HTTPException(404, f"Aircraft id={aircraft_id} не найден")

    in_use = db.query(Flight).filter(Flight.aircraft_id == aircraft_id).first()
    if in_use:
        raise HTTPException(
            409,
            f"Борт {aircraft.registration} используется в текущем рейсе. "
            "Сначала выберите другой борт для рейса."
        )

    db.delete(aircraft)
    db.commit()


# Эндпоинты маршрутов

@router.get("/routes")
def list_routes_endpoint(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return list_routes(db)


@router.post("/routes", status_code=201)
def create_route_endpoint(
    payload: RoutePayload,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    route = Route(**{**payload.dict(), "is_domestic": int(payload.is_domestic)})
    db.add(route)
    db.commit()
    db.refresh(route)
    return {"id": route.id, "destination_city": route.destination_city}


@router.put("/routes/{route_id}")
def update_route_endpoint(
        route_id: int,
        payload: RoutePayload,
        db: Session = Depends(get_db),
) -> dict[str, Any]:
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(404, f"Route id={route_id} не найден")

    data = payload.dict()
    data["is_domestic"] = int(payload.is_domestic)
    for field, value in data.items():
        setattr(route, field, value)
    db.commit()
    return {"id": route.id}


@router.delete("/routes/{route_id}", status_code=204)
def delete_route_endpoint(route_id: int, db: Session = Depends(get_db)) -> None:
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(404, f"Route id={route_id} не найден")

    in_use = db.query(Flight).filter(Flight.route_id == route_id).first()
    if in_use:
        raise HTTPException(
            409,
            f"Маршрут {route.origin_iata}→{route.destination_iata} "
            "используется в текущем рейсе."
        )

    db.delete(route)
    db.commit()
