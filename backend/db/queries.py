from sqlalchemy.orm import Session

from backend.db.models import Aircraft, CommercialOffer, Flight, MenuItem, Route


def get_flight_info(db: Session, lang: str = "ru") -> dict:
    flight = db.query(Flight).first()
    if not flight:
        return {}

    # Подтягиваем связанные сущности через relationships
    aircraft = flight.aircraft
    route = flight.route

    result = {
        "flight_number": flight.flight_number,
        "departure_time": flight.departure_time,
        "arrival_time": flight.arrival_time,
        "cruising_altitude": flight.cruising_altitude,
        "cruising_speed": flight.cruising_speed,
    }

    # Маршрут
    if route:
        result["origin"] = route.origin_city
        result["origin_iata"] = route.origin_iata
        result["destination"] = route.destination_city
        result["destination_iata"] = route.destination_iata
        result["destination_country"] = route.destination_country
        result["flight_duration_min"] = route.flight_duration_min
        result["distance_km"] = route.distance_km
        result["meal_type"] = flight.meal_type

    # Борт
    if aircraft:
        result["aircraft_type"] = aircraft.aircraft_type
        result["aircraft_reg"] = aircraft.registration
        result["capacity_economy"] = aircraft.capacity_economy
        result["capacity_business"] = aircraft.capacity_business

    # Обратный рейс (опционально)
    if flight.return_flight_number:
        result["return_flight"] = {
            "flight_number": flight.return_flight_number,
            "departure_time": flight.return_departure_time,
            "arrival_time": flight.return_arrival_time,
            # Origin/destination обратного рейса — поменяны местами
            "origin": route.destination_city if route else None,
            "origin_iata": route.destination_iata if route else None,
            "destination": route.origin_city if route else None,
            "destination_iata": route.origin_iata if route else None,
        }

    # Погода в пункте назначения (на выбранном языке)
    weather = (
        flight.weather_description_en if lang == "en"
        else flight.weather_description_ru
    )
    if weather:
        result["weather"] = weather
    if flight.weather_temp_celsius is not None:
        result["weather_temp_celsius"] = flight.weather_temp_celsius

    # Курс валюты
    rate_note = (
        flight.exchange_rate_note_en if lang == "en"
        else flight.exchange_rate_note_ru
    )
    if rate_note:
        result["exchange_rate"] = rate_note
    if flight.exchange_rate_currency:
        result["exchange_rate_currency"] = flight.exchange_rate_currency

    return result


def get_menu(db: Session, cabin_class: str = "economy", lang: str = "ru") -> list:
    items = db.query(MenuItem).filter(
        MenuItem.cabin_class == cabin_class
    ).all()

    result = []
    for item in items:
        # Если EN-перевод есть — используем
        if lang == "en":
            name = item.name_en or item.name_ru
            description = item.description_en or item.description_ru or ""
        else:
            name = item.name_ru
            description = item.description_ru or ""

        result.append({
            "name": name,
            "description": description,
            "category": item.category,
            "is_vegetarian": bool(item.is_vegetarian),
            "price": item.price,
        })

    return result


def get_commercial_offers(db: Session, lang: str = "ru") -> list:
    offers = db.query(CommercialOffer).all()

    result = []
    for offer in offers:
        if lang == "en":
            title = offer.title_en or offer.title_ru
            description = offer.description_en or offer.description_ru or ""
        else:
            title = offer.title_ru
            description = offer.description_ru or ""

        result.append({
            "title": title,
            "description": description,
            "category": offer.category,
        })

    return result


# Справочники для админки

def list_aircraft(db: Session) -> list:
    aircraft_list = db.query(Aircraft).order_by(Aircraft.registration).all()
    return [
        {
            "id": a.id,
            "registration": a.registration,
            "aircraft_type": a.aircraft_type,
            "manufacturer": a.manufacturer,
            "capacity_economy": a.capacity_economy,
            "capacity_business": a.capacity_business,
            "year_manufactured": a.year_manufactured,
            "status": a.status,
        }
        for a in aircraft_list
    ]


def list_routes(db: Session) -> list:
    routes = db.query(Route).order_by(Route.destination_city).all()
    return [
        {
            "id": r.id,
            "origin_city": r.origin_city,
            "origin_iata": r.origin_iata,
            "origin_country": r.origin_country,
            "destination_city": r.destination_city,
            "destination_iata": r.destination_iata,
            "destination_country": r.destination_country,
            "is_domestic": bool(r.is_domestic),
            "flight_duration_min": r.flight_duration_min,
            "distance_km": r.distance_km,
        }
        for r in routes
    ]


# Порог короткого рейса в минутах
SHORT_FLIGHT_THRESHOLD_MIN = 120


def suggest_meal_type(flight_duration_min: int | None) -> str:
    if flight_duration_min is None:
        return "full"
    if flight_duration_min < SHORT_FLIGHT_THRESHOLD_MIN:
        return "light"
    return "full"


def validate_menu_for_meal_type(menu_items: list[dict], meal_type: str, cabin_class: str) -> list[str]:
    errors: list[str] = []
    cabin_label = "эконом-класс" if cabin_class == "economy" else "бизнес-класс"

    by_category: dict[str, list[dict]] = {}
    for item in menu_items:
        cat = item.get("category", "")
        by_category.setdefault(cat, []).append(item)

    n_main = len(by_category.get("main", []))
    n_starter = len(by_category.get("starter", []))
    n_dessert = len(by_category.get("dessert", []))
    n_drink = len(by_category.get("drink", []))
    n_snack = len(by_category.get("snack", []))

    if meal_type == "full":
        # Полный приём пищи: ≥2 main, ≥1 starter/dessert, ≥3 drink
        if n_main < 2:
            errors.append(
                f"{cabin_label}: для полного питания нужно минимум 2 основных блюда "
                f"(например, рыба и курица), сейчас {n_main}"
            )
        if n_starter + n_dessert < 1:
            errors.append(
                f"{cabin_label}: для полного питания нужна минимум 1 закуска или десерт"
            )
        if n_drink < 3:
            errors.append(
                f"{cabin_label}: для полного питания нужно минимум 3 напитка, сейчас {n_drink}"
            )

    elif meal_type == "light":
        # Лёгкий перекус: ≥1 sandwich/snack, ≥3 drinks, БЕЗ main
        if n_main > 0:
            errors.append(
                f"{cabin_label}: на коротком рейсе (light meal) основные блюда не подаются — "
                f"уберите {n_main} блюд категории main"
            )
        if n_snack < 1:
            errors.append(
                f"{cabin_label}: для лёгкого перекуса нужен минимум 1 сэндвич/снэк"
            )
        if n_drink < 3:
            errors.append(
                f"{cabin_label}: для лёгкого перекуса нужно минимум 3 напитка, сейчас {n_drink}"
            )

    elif meal_type == "snack_only":
        # Только закуски и напитки, без main
        if n_main > 0:
            errors.append(
                f"{cabin_label}: при типе snack_only основные блюда не подаются"
            )
        if n_drink < 2:
            errors.append(
                f"{cabin_label}: при типе snack_only нужно минимум 2 напитка"
            )

    elif meal_type == "no_meal":
        # Без питания: меню должно быть пустым
        if menu_items:
            errors.append(
                f"{cabin_label}: тип no_meal — меню должно быть пустым"
            )

    else:
        errors.append(f"Неизвестный meal_type: {meal_type!r}")

    return errors
