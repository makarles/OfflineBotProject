import json
import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

from pathlib import Path
from backend.db.database import SessionLocal, init_db
from backend.db.models import Flight, MenuItem, CommercialOffer
from backend.rag.indexer import build_index

SNAPSHOT_PATH = Path("data/snapshots/flight_snapshot.json")


def sync():
    print("Sync Agent запущен")

    # Шаг 1: Чтение снапшота
    if not SNAPSHOT_PATH.exists():
        print(f"Снапшот не найден: {SNAPSHOT_PATH}")
        return

    with open(SNAPSHOT_PATH, "r", encoding="utf-8") as f:
        snapshot = json.load(f)
    print("Снапшот запущен")

    # Шаг 2: Обновление БД
    init_db()
    db = SessionLocal()

    db.query(CommercialOffer).delete()
    db.query(MenuItem).delete()
    db.query(Flight).delete()

    flight_data = snapshot["flight"]
    flight = Flight(**flight_data)
    db.add(flight)
    db.flush()

    for item_data in snapshot["menu"]:
        item = MenuItem(flight_id=flight.id, **item_data)
        db.add(item)

    for offer_data in snapshot["commercial_offers"]:
        offer = CommercialOffer(flight_id=flight.id, **offer_data)
        db.add(offer)

    db.commit()
    db.close()
    print("База данных обновлена")

    # Шаг 3: перестройка векторного индекса
    print("Перестройка векторного индекса...")
    build_index()

    print("Синхронизация завершена")


if __name__ == "__main__":
    sync()
