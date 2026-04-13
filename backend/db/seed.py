from datetime import datetime
from backend.db.database import SessionLocal, init_db
from backend.db.models import Flight, MenuItem, CommercialOffer

def seed():
    init_db()
    db = SessionLocal()

    # Очищаем таблицы перед заполнением
    db.query(CommercialOffer).delete()
    db.query(MenuItem).delete()
    db.query(Flight).delete()

    # Тестовый рейс
    flight = Flight(
        flight_number="AL-1234",
        origin="SVO",
        destination="DXB",
        departure_time="2026-04-15 10:30",
        arrival_time="2026-04-15 16:45",
        aircraft_type="Airbus A320",
        aircraft_reg="RA-89012",
        cruising_altitude=10500,
        cruising_speed=850
    )
    db.add(flight)
    db.flush()  # получить flight.id

    # Меню
    menu_items = [
        MenuItem(
            flight_id=flight.id,
            name="Куриное филе с рисом",
            description="Запечённое куриное филе с отварным рисом и овощами",
            category="main",
            cabin_class="economy",
            is_vegetarian=0,
            price=0.0
        ),
        MenuItem(
            flight_id=flight.id,
            name="Паста с томатным соусом",
            description="Паста пенне в томатном соусе с базиликом",
            category="main",
            cabin_class="economy",
            is_vegetarian=1,
            price=0.0
        ),
        MenuItem(
            flight_id=flight.id,
            name="Шоколадный кекс",
            description="Мягкий шоколадный кекс",
            category="dessert",
            cabin_class="economy",
            is_vegetarian=1,
            price=0.0
        ),
        MenuItem(
            flight_id=flight.id,
            name="Кофе",
            description="Американо или капучино",
            category="drink",
            cabin_class="economy",
            is_vegetarian=1,
            price=0.0
        ),
        MenuItem(
            flight_id=flight.id,
            name="Стейк из говядины",
            description="Стейк medium rare с картофельным пюре и спаржей",
            category="main",
            cabin_class="business",
            is_vegetarian=0,
            price=0.0
        ),
    ]
    db.add_all(menu_items)

    # Коммерческие предложения
    offers = [
        CommercialOffer(
            flight_id=flight.id,
            title="Duty Free",
            description="Парфюмерия, косметика и алкоголь со скидкой до 30%",
            category="duty_free"
        ),
        CommercialOffer(
            flight_id=flight.id,
            title="AeroLine Bonus",
            description="Накапливайте мили за каждый полёт и обменивайте на билеты",
            category="loyalty"
        ),
    ]
    db.add_all(offers)

    db.commit()
    db.close()
    print("База данных заполнена тестовыми данными")

if __name__ == "__main__":
    seed()