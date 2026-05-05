from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path


from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import Aircraft, CommercialOffer, Flight, MenuItem, Route


router = APIRouter(prefix="/api/sync", tags=["sync"])


def aircraft_to_dict(item: Aircraft) -> dict[str, Any]:
    return {
        "id": item.id,
        "registration": item.registration,
        "aircraft_type": item.aircraft_type,
        "manufacturer": item.manufacturer,
        "capacity_economy": item.capacity_economy,
        "capacity_business": item.capacity_business,
        "year_manufactured": item.year_manufactured,
        "status": item.status,
    }


def route_to_dict(item: Route) -> dict[str, Any]:
    return {
        "id": item.id,
        "origin_city": item.origin_city,
        "origin_iata": item.origin_iata,
        "origin_country": item.origin_country,
        "destination_city": item.destination_city,
        "destination_iata": item.destination_iata,
        "destination_country": item.destination_country,
        "is_domestic": bool(item.is_domestic),
        "flight_duration_min": item.flight_duration_min,
        "distance_km": item.distance_km,
    }


def flight_to_dict(item: Flight | None) -> dict[str, Any] | None:
    if item is None:
        return None

    return {
        "id": item.id,
        "flight_number": item.flight_number,
        "departure_time": item.departure_time,
        "arrival_time": item.arrival_time,
        "aircraft_id": item.aircraft_id,
        "route_id": item.route_id,
        "cruising_altitude": item.cruising_altitude,
        "cruising_speed": item.cruising_speed,
        "meal_type": item.meal_type,
        "return_flight_number": item.return_flight_number,
        "return_departure_time": item.return_departure_time,
        "return_arrival_time": item.return_arrival_time,
        "weather_description_ru": item.weather_description_ru,
        "weather_description_en": item.weather_description_en,
        "weather_temp_celsius": item.weather_temp_celsius,
        "exchange_rate_currency": item.exchange_rate_currency,
        "exchange_rate_to_rub": item.exchange_rate_to_rub,
        "exchange_rate_note_ru": item.exchange_rate_note_ru,
        "exchange_rate_note_en": item.exchange_rate_note_en,
    }


def menu_item_to_dict(item: MenuItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "flight_id": item.flight_id,
        "name_ru": item.name_ru,
        "name_en": item.name_en,
        "description_ru": item.description_ru,
        "description_en": item.description_en,
        "category": item.category,
        "cabin_class": item.cabin_class,
        "is_vegetarian": bool(item.is_vegetarian),
        "price": item.price,
    }


def offer_to_dict(item: CommercialOffer) -> dict[str, Any]:
    return {
        "id": item.id,
        "flight_id": item.flight_id,
        "title_ru": item.title_ru,
        "title_en": item.title_en,
        "description_ru": item.description_ru,
        "description_en": item.description_en,
        "category": item.category,
    }


@router.get("/export")
def export_operational_data(db: Session = Depends(get_db)) -> dict[str, Any]:
    flight = db.query(Flight).first()

    return {
        "schema": "skyassist.flight_package.v1",
        "exported_at": datetime.utcnow().isoformat(),
        "aircraft": [aircraft_to_dict(item) for item in db.query(Aircraft).all()],
        "routes": [route_to_dict(item) for item in db.query(Route).all()],
        "flight": flight_to_dict(flight),
        "menu_items": [menu_item_to_dict(item) for item in db.query(MenuItem).all()],
        "commercial_offers": [offer_to_dict(item) for item in db.query(CommercialOffer).all()],
    }


@router.post("/import")
def import_operational_data(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any]:
    if payload.get("schema") != "skyassist.flight_package.v1":
        raise HTTPException(status_code=400, detail="Неверный формат sync-пакета")

    db.query(MenuItem).delete()
    db.query(CommercialOffer).delete()
    db.query(Flight).delete()
    db.query(Aircraft).delete()
    db.query(Route).delete()
    db.flush()

    for item in payload.get("aircraft", []):
        db.add(Aircraft(
            id=item["id"],
            registration=item["registration"],
            aircraft_type=item["aircraft_type"],
            manufacturer=item.get("manufacturer"),
            capacity_economy=item.get("capacity_economy"),
            capacity_business=item.get("capacity_business"),
            year_manufactured=item.get("year_manufactured"),
            status=item.get("status") or "active",
        ))

    for item in payload.get("routes", []):
        db.add(Route(
            id=item["id"],
            origin_city=item["origin_city"],
            origin_iata=item["origin_iata"],
            origin_country=item.get("origin_country"),
            destination_city=item["destination_city"],
            destination_iata=item["destination_iata"],
            destination_country=item.get("destination_country"),
            is_domestic=int(bool(item.get("is_domestic"))),
            flight_duration_min=item.get("flight_duration_min"),
            distance_km=item.get("distance_km"),
        ))

    db.flush()

    flight = payload.get("flight")
    if flight:
        db.add(Flight(
            id=flight["id"],
            flight_number=flight["flight_number"],
            departure_time=flight["departure_time"],
            arrival_time=flight["arrival_time"],
            aircraft_id=flight["aircraft_id"],
            route_id=flight["route_id"],
            cruising_altitude=flight.get("cruising_altitude"),
            cruising_speed=flight.get("cruising_speed"),
            meal_type=flight.get("meal_type") or "full",
            return_flight_number=flight.get("return_flight_number"),
            return_departure_time=flight.get("return_departure_time"),
            return_arrival_time=flight.get("return_arrival_time"),
            weather_description_ru=flight.get("weather_description_ru"),
            weather_description_en=flight.get("weather_description_en"),
            weather_temp_celsius=flight.get("weather_temp_celsius"),
            exchange_rate_currency=flight.get("exchange_rate_currency"),
            exchange_rate_to_rub=flight.get("exchange_rate_to_rub"),
            exchange_rate_note_ru=flight.get("exchange_rate_note_ru"),
            exchange_rate_note_en=flight.get("exchange_rate_note_en"),
        ))

    db.flush()

    for item in payload.get("menu_items", []):
        db.add(MenuItem(
            id=item["id"],
            flight_id=item["flight_id"],
            name_ru=item["name_ru"],
            name_en=item.get("name_en"),
            description_ru=item.get("description_ru"),
            description_en=item.get("description_en"),
            category=item.get("category") or "main",
            cabin_class=item.get("cabin_class") or "economy",
            is_vegetarian=int(bool(item.get("is_vegetarian"))),
            price=item.get("price") or 0.0,
        ))

    for item in payload.get("commercial_offers", []):
        db.add(CommercialOffer(
            id=item["id"],
            flight_id=item["flight_id"],
            title_ru=item["title_ru"],
            title_en=item.get("title_en"),
            description_ru=item.get("description_ru"),
            description_en=item.get("description_en"),
            category=item.get("category"),
        ))

    db.commit()

    return {
        "status": "ok",
        "imported_at": datetime.utcnow().isoformat(),
        "aircraft_count": len(payload.get("aircraft", [])),
        "routes_count": len(payload.get("routes", [])),
        "menu_items_count": len(payload.get("menu_items", [])),
        "commercial_offers_count": len(payload.get("commercial_offers", [])),
        "flight_loaded": bool(payload.get("flight")),
    }


AIRCRAFT_IMPORT_URL = os.getenv(
    "SKYASSIST_AIRCRAFT_IMPORT_URL",
    "http://127.0.0.1:8000/api/sync/import",
)

SYNC_DIR = Path("data/sync")
SYNC_FILE = SYNC_DIR / "flight_package.json"


@router.post("/push-to-aircraft")
def push_to_aircraft_server(db: Session = Depends(get_db)) -> dict[str, Any]:
    package = export_operational_data(db)

    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    SYNC_FILE.write_text(
        json.dumps(package, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    request = urllib.request.Request(
        AIRCRAFT_IMPORT_URL,
        data=json.dumps(package, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
            aircraft_result = json.loads(response_body) if response_body else {}
    except urllib.error.URLError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Не удалось передать данные на бортовой сервер: {exc}",
        )

    return {
        "status": "ok",
        "message": "Данные успешно переданы на бортовой сервер",
        "aircraft_import_url": AIRCRAFT_IMPORT_URL,
        "sync_file": str(SYNC_FILE),
        "aircraft_result": aircraft_result,
    }