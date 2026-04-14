from sqlalchemy.orm import Session
from backend.db.models import Flight, MenuItem, CommercialOffer


def get_flight_info(db: Session) -> dict:
    flight = db.query(Flight).first()
    if not flight:
        return {}
    result = {
        "flight_number": flight.flight_number,
        "origin": flight.origin,
        "destination": flight.destination,
        "departure_time": flight.departure_time,
        "arrival_time": flight.arrival_time,
        "aircraft_type": flight.aircraft_type,
        "aircraft_reg": flight.aircraft_reg,
        "cruising_altitude": flight.cruising_altitude,
        "cruising_speed": flight.cruising_speed,
    }
    if flight.return_flight_number:
        result["return_flight"] = {
            "flight_number": flight.return_flight_number,
            "departure_time": flight.return_departure_time,
            "arrival_time": flight.return_arrival_time,
            "origin": flight.destination,
            "destination": flight.origin,
        }
    return result


def get_menu(db: Session, cabin_class: str = "economy") -> list:
    items = db.query(MenuItem).filter(
        MenuItem.cabin_class == cabin_class
    ).all()
    return [
        {
            "name": item.name,
            "description": item.description,
            "category": item.category,
            "is_vegetarian": bool(item.is_vegetarian),
            "price": item.price
        }
        for item in items
    ]


def get_commercial_offers(db: Session) -> list:
    offers = db.query(CommercialOffer).all()
    return [
        {
            "title": offer.title,
            "description": offer.description,
            "category": offer.category
        }
        for offer in offers
    ]
