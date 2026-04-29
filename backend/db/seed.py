"""
Описание:
Скрипт пересоздаёт БД с нуля и заполняет её примером данных:
- 3 борта в Aircraft (A320, A321, B737)
- 5 маршрутов в Route (Москва-Дубай, Москва-Стамбул, Москва-СПб и т.д.)
- 1 текущий рейс SVO->DXB
- 7 пунктов меню для эконом-класса (с EN-переводами)
- 2 коммерческих предложения

Использование:
    python -m backend.db.seed

Внимание: УДАЛЯЕТ существующую БД.
"""
import os
from pathlib import Path

from backend.db.database import engine, SessionLocal
from backend.db.models import Aircraft, Base, CommercialOffer, Flight, MenuItem, Route


def reset_db():
    """Удаляет файл БД и пересоздаёт схему с нуля."""
    # Путь к БД из database.py: sqlite:///./data/skyassist.db
    db_path = Path("data/skyassist.db")
    if db_path.exists():
        os.remove(db_path)
        print(f"Удалена старая БД: {db_path}")

    Base.metadata.create_all(bind=engine)
    print("Схема создана")


def seed():
    """Заполняет БД примером данных."""
    db = SessionLocal()
    try:
        # Справочник бортов
        aircraft_a320 = Aircraft(
            registration="RA-89012",
            aircraft_type="Airbus A320",
            manufacturer="Airbus",
            capacity_economy=150,
            capacity_business=12,
            year_manufactured=2018,
            status="active",
        )
        aircraft_a321 = Aircraft(
            registration="RA-89045",
            aircraft_type="Airbus A321",
            manufacturer="Airbus",
            capacity_economy=180,
            capacity_business=16,
            year_manufactured=2020,
            status="active",
        )
        aircraft_b737 = Aircraft(
            registration="RA-73210",
            aircraft_type="Boeing 737",
            manufacturer="Boeing",
            capacity_economy=140,
            capacity_business=8,
            year_manufactured=2017,
            status="active",
        )
        db.add_all([aircraft_a320, aircraft_a321, aircraft_b737])
        db.flush()  # чтобы получить id

        # Справочник маршрутов
        route_dxb = Route(
            origin_city="Москва", origin_iata="SVO", origin_country="Россия",
            destination_city="Дубай", destination_iata="DXB", destination_country="ОАЭ",
            is_domestic=0, flight_duration_min=315, distance_km=3500,
        )
        route_ist = Route(
            origin_city="Москва", origin_iata="SVO", origin_country="Россия",
            destination_city="Стамбул", destination_iata="IST", destination_country="Турция",
            is_domestic=0, flight_duration_min=190, distance_km=1755,
        )
        route_led = Route(
            origin_city="Москва", origin_iata="SVO", origin_country="Россия",
            destination_city="Санкт-Петербург", destination_iata="LED", destination_country="Россия",
            is_domestic=1, flight_duration_min=85, distance_km=635,
        )
        route_kzn = Route(
            origin_city="Москва", origin_iata="SVO", origin_country="Россия",
            destination_city="Казань", destination_iata="KZN", destination_country="Россия",
            is_domestic=1, flight_duration_min=110, distance_km=720,
        )
        route_mos = Route(
            origin_city="Дубай", origin_iata="DXB", origin_country="ОАЭ",
            destination_city="Москва", destination_iata="SVO", destination_country="Россия",
            is_domestic=0, flight_duration_min=320, distance_km=3500,
        )
        db.add_all([route_dxb, route_ist, route_led, route_kzn, route_mos])
        db.flush()

        # Текущий рейс: SVO - DXB на A320
        flight = Flight(
            flight_number="AL-1234",
            departure_time="2026-04-26 10:30",
            arrival_time="2026-04-26 16:45",
            aircraft_id=aircraft_a320.id,
            route_id=route_dxb.id,
            cruising_altitude=10500,
            cruising_speed=850,
            meal_type="full",
            # Обратный рейс
            return_flight_number="AL-1235",
            return_departure_time="2026-04-26 18:30",
            return_arrival_time="2026-04-26 23:45",
            # Погода в Дубае
            weather_description_ru="Солнечно, +28°C, ветер слабый",
            weather_description_en="Sunny, +28°C, light wind",
            weather_temp_celsius=28,
            # Курс валюты
            exchange_rate_currency="AED",
            exchange_rate_to_rub=25.30,
            exchange_rate_note_ru="1 AED = 25.30 ₽",
            exchange_rate_note_en="1 AED = 25.30 RUB",
        )
        db.add(flight)
        db.flush()

        # Меню эконом-класса
        menu_items = [
            MenuItem(
                flight_id=flight.id,
                name_ru="Куриное филе с рисом",
                name_en="Grilled chicken with rice",
                description_ru="Нежное куриное филе с гарниром из риса басмати и овощами",
                description_en="Tender chicken fillet with basmati rice and vegetables",
                category="main", cabin_class="economy", is_vegetarian=0, price=0.0,
            ),
            MenuItem(
                flight_id=flight.id,
                name_ru="Паста с томатным соусом",
                name_en="Pasta with tomato sauce",
                description_ru="Спагетти с томатным соусом и свежим базиликом",
                description_en="Spaghetti with tomato sauce and fresh basil",
                category="main", cabin_class="economy", is_vegetarian=1, price=0.0,
            ),
            MenuItem(
                flight_id=flight.id,
                name_ru="Шоколадный кекс",
                name_en="Chocolate cake",
                description_ru="Десертный кекс с тёмным шоколадом",
                description_en="Dessert cake with dark chocolate",
                category="dessert", cabin_class="economy", is_vegetarian=1, price=0.0,
            ),
            MenuItem(
                flight_id=flight.id,
                name_ru="Чай чёрный",
                name_en="Black tea",
                description_ru="Горячий чёрный чай",
                description_en="Hot black tea",
                category="drink", cabin_class="economy", is_vegetarian=1, price=0.0,
            ),
            MenuItem(
                flight_id=flight.id,
                name_ru="Кофе",
                name_en="Coffee",
                description_ru="Свежесваренный кофе",
                description_en="Freshly brewed coffee",
                category="drink", cabin_class="economy", is_vegetarian=1, price=0.0,
            ),
            MenuItem(
                flight_id=flight.id,
                name_ru="Минеральная вода",
                name_en="Mineral water",
                description_ru="Газированная или негазированная",
                description_en="Sparkling or still",
                category="drink", cabin_class="economy", is_vegetarian=1, price=0.0,
            ),
            MenuItem(
                flight_id=flight.id,
                name_ru="Сэндвич с курицей",
                name_en="Chicken sandwich",
                description_ru="Сэндвич с курицей и салатом за дополнительную плату",
                description_en="Chicken sandwich with salad for additional fee",
                category="snack", cabin_class="economy", is_vegetarian=0, price=350.0,
            ),
        ]

        # Меню бизнес-класса
        menu_items.extend([
            MenuItem(
                flight_id=flight.id,
                name_ru="Стейк из говядины с овощами гриль",
                name_en="Beef steak with grilled vegetables",
                description_ru="Стейк рибай средней прожарки с сезонными овощами",
                description_en="Medium-rare ribeye steak with seasonal vegetables",
                category="main", cabin_class="business", is_vegetarian=0, price=0.0,
            ),
            MenuItem(
                flight_id=flight.id,
                name_ru="Лосось на пару",
                name_en="Steamed salmon",
                description_ru="Филе лосося с лимонным соусом и спаржей",
                description_en="Salmon fillet with lemon sauce and asparagus",
                category="main", cabin_class="business", is_vegetarian=0, price=0.0,
            ),
            MenuItem(
                flight_id=flight.id,
                name_ru="Салат Цезарь с курицей",
                name_en="Caesar salad with chicken",
                description_ru="Классический Цезарь с куриной грудкой",
                description_en="Classic Caesar with chicken breast",
                category="starter", cabin_class="business", is_vegetarian=0, price=0.0,
            ),
            MenuItem(
                flight_id=flight.id,
                name_ru="Тирамису",
                name_en="Tiramisu",
                description_ru="Классический итальянский десерт",
                description_en="Classic Italian dessert",
                category="dessert", cabin_class="business", is_vegetarian=1, price=0.0,
            ),
            MenuItem(
                flight_id=flight.id,
                name_ru="Шампанское",
                name_en="Champagne",
                description_ru="Бокал шампанского по выбору экипажа",
                description_en="Glass of champagne by crew choice",
                category="drink", cabin_class="business", is_vegetarian=1, price=0.0,
            ),
        ])

        db.add_all(menu_items)

        # Коммерческие предложения
        offers = [
            CommercialOffer(
                flight_id=flight.id,
                title_ru="Скидка 15% на трансфер в отель",
                title_en="15% discount on hotel transfer",
                description_ru="При предъявлении посадочного талона партнёрская служба такси предоставляет скидку",
                description_en="Show your boarding pass to a partner taxi service for a discount",
                category="transfer",
            ),
            CommercialOffer(
                flight_id=flight.id,
                title_ru="Бесплатный Wi-Fi в Dubai Mall",
                title_en="Free Wi-Fi at Dubai Mall",
                description_ru="Скан QR-кода с посадочного талона активирует бесплатный Wi-Fi на 4 часа",
                description_en="Scan the QR code from your boarding pass for 4 hours of free Wi-Fi",
                category="shopping",
            ),
        ]
        db.add_all(offers)

        db.commit()
        print("База заполнена примером данных:")
        print(f"  Aircraft: 3 борта (A320, A321, B737)")
        print(f"  Routes: 5 маршрутов")
        print(f"  Flight: AL-1234 SVO->DXB на {aircraft_a320.aircraft_type}")
        print(f"  MenuItems: {len(menu_items)} (эконом + бизнес)")
        print(f"  CommercialOffers: {len(offers)}")

    except Exception as exc:
        db.rollback()
        print(f"Ошибка при заполнении: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    reset_db()
    seed()