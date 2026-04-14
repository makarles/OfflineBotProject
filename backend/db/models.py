from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Flight(Base):
    __tablename__ = "flights"

    id = Column(Integer, primary_key=True)
    flight_number = Column(String, nullable=False)
    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    departure_time = Column(String, nullable=False)
    arrival_time = Column(String, nullable=False)
    aircraft_type = Column(String)
    aircraft_reg = Column(String)
    cruising_altitude = Column(Integer)
    cruising_speed = Column(Integer)
    return_flight_number = Column(String)
    return_departure_time = Column(String)
    return_arrival_time = Column(String)


class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True)
    flight_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String)
    cabin_class = Column(String)
    is_vegetarian = Column(Integer, default=0)
    price = Column(Float, default=0.0)


class CommercialOffer(Base):
    __tablename__ = "commercial_offers"

    id = Column(Integer, primary_key=True)
    flight_id = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String)


class Aircraft(Base):
    __tablename__ = "aircraft"                     # Пример данных

    id = Column(Integer, primary_key=True)
    registration = Column(String, nullable=False)  # RA-89012
    aircraft_type = Column(String, nullable=False)  # Airbus A320
    manufacturer = Column(String)                   # Airbus
    capacity_economy = Column(Integer)              # 150
    capacity_business = Column(Integer)             # 12
    year_manufactured = Column(Integer)             # 2018
    status = Column(String, default="active")       # active / maintenance

class Route(Base):
    __tablename__ = "routes"                            # Пример данных

    id = Column(Integer, primary_key=True)
    destination_city = Column(String, nullable=False)   # Дубай
    destination_iata = Column(String, nullable=False)   # DXB
    destination_country = Column(String)                # ОАЭ
    is_domestic = Column(Integer, default=0)            # 0=международный, 1=внутренний
    flight_duration_min = Column(Integer)               # 255 (минуты)
    distance_km = Column(Integer)                       # 3500