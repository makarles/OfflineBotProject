from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Aircraft(Base):
    __tablename__ = "aircraft"

    id = Column(Integer, primary_key=True)
    registration = Column(String, nullable=False, unique=True)  # RA-89012
    aircraft_type = Column(String, nullable=False)  # Airbus A320
    manufacturer = Column(String)  # Airbus / Boeing
    capacity_economy = Column(Integer)  # 150
    capacity_business = Column(Integer)  # 12
    year_manufactured = Column(Integer)  # 2018
    status = Column(String, default="active")  # active / maintenance


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True)
    # Откуда летит борт. Обычно SVO (Москва)
    origin_city = Column(String, nullable=False)  # Москва
    origin_iata = Column(String, nullable=False)  # SVO
    origin_country = Column(String)  # Россия

    # Куда летит борт
    destination_city = Column(String, nullable=False)  # Дубай
    destination_iata = Column(String, nullable=False)  # DXB
    destination_country = Column(String)  # ОАЭ

    is_domestic = Column(Integer, default=0)  # 0=международный, 1=внутренний
    flight_duration_min = Column(Integer)  # 255 (минут полёта)
    distance_km = Column(Integer)  # 3500 (км)


class Flight(Base):
    __tablename__ = "flights"

    id = Column(Integer, primary_key=True)

    # Базовая информация о рейсе
    flight_number = Column(String, nullable=False)  # AL-1234
    departure_time = Column(String, nullable=False)  # 2026-04-26 10:30 (по местному вылета)
    arrival_time = Column(String, nullable=False)  # 2026-04-26 16:45 (по местному прилёта)

    # FK на справочники
    aircraft_id = Column(Integer, ForeignKey("aircraft.id"))
    route_id = Column(Integer, ForeignKey("routes.id"))

    # Параметры полёта
    cruising_altitude = Column(Integer)  # 10500 (метры)
    cruising_speed = Column(Integer)  # 850 (км/ч)
    meal_type = Column(String, default="full", nullable=False)

    # Обратный рейс
    return_flight_number = Column(String)  # AL-1235
    return_departure_time = Column(String)  # 2026-04-26 18:30
    return_arrival_time = Column(String)  # 2026-04-26 23:45

    # Динамика per-рейс: погода в пункте назначения
    weather_description_ru = Column(String)  # "Солнечно, +28°C"
    weather_description_en = Column(String)  # "Sunny, +28°C"
    weather_temp_celsius = Column(Integer)  # 28

    # Динамика per-рейс: курс валюты пункта назначения к рублю
    exchange_rate_currency = Column(String)  # "AED"
    exchange_rate_to_rub = Column(Float)  # 25.30 (рублей за 1 AED)
    exchange_rate_note_ru = Column(String)  # "1 AED = 25.30 РУБ" (готовая строка для промпта)
    exchange_rate_note_en = Column(String)  # "1 AED = 25.30 RUB"

    # Relationships для удобного доступа в коде: flight.aircraft.aircraft_type
    aircraft = relationship("Aircraft")
    route = relationship("Route")


class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True)
    flight_id = Column(Integer, ForeignKey("flights.id"))

    # Двуязычные поля
    name_ru = Column(String, nullable=False)  # "Куриное филе с рисом"
    name_en = Column(String)  # "Grilled chicken with rice"
    description_ru = Column(Text)  # "Нежное куриное филе ..."
    description_en = Column(Text)  # "Tender chicken fillet ..."

    category = Column(String)  # "main" / "starter" / "dessert" / "drink"
    cabin_class = Column(String)  # "economy" / "business"
    is_vegetarian = Column(Integer, default=0)  # 0/1
    price = Column(Float, default=0.0)  # 0.0 = включено в билет


class CommercialOffer(Base):
    __tablename__ = "commercial_offers"

    id = Column(Integer, primary_key=True)
    flight_id = Column(Integer, ForeignKey("flights.id"))

    title_ru = Column(String, nullable=False)  # "Скидка на трансфер в отель"
    title_en = Column(String)  # "Discount on hotel transfer"
    description_ru = Column(Text)
    description_en = Column(Text)

    category = Column(String)  # "transfer" / "hotel" / "shopping"
