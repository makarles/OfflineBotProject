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
