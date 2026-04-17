import json
import logging
from collections import Counter
from pathlib import Path

from backend.db.database import SessionLocal, init_db
from backend.db.models import Aircraft, Route

logger = logging.getLogger("skyassist.build_aeroline")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

OUTPUT_PATH = Path("data/knowledge_base/aeroline_full.json")
HUB_CITY = "Москва"
HUB_IATA = "SVO"


def _plural_directions(n: int) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return "направление"
    if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return "направления"
    return "направлений"


def _format_duration(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} мин"
    hours = minutes // 60
    rest = minutes % 60
    if rest == 0:
        return f"{hours} ч"
    return f"{hours} ч {rest} мин"


def build_fleet_section(aircraft_list: list[Aircraft]) -> tuple[str, dict]:
    by_type: dict[str, list[Aircraft]] = {}
    for ac in aircraft_list:
        by_type.setdefault(ac.aircraft_type, []).append(ac)

    total = len(aircraft_list)
    active = sum(1 for ac in aircraft_list if ac.status == "active")
    in_maintenance = sum(1 for ac in aircraft_list if ac.status == "maintenance")

    type_lines = []
    fleet_dict: dict[str, str] = {}

    for ac_type, items in sorted(by_type.items()):
        count = len(items)
        manufacturer = items[0].manufacturer
        cap_econ = items[0].capacity_economy
        cap_biz = items[0].capacity_business
        years = sorted({ac.year_manufactured for ac in items if ac.year_manufactured})
        year_range = f"{years[0]}–{years[-1]}" if len(years) > 1 else str(years[0])

        description = (
            f"{count} воздушных судов ({manufacturer}), "
            f"выпуск {year_range}, вместимость {cap_econ} мест эконом-класса и "
            f"{cap_biz} мест бизнес-класса"
        )
        type_lines.append(f"{ac_type} — " + description + ".")
        fleet_dict[ac_type] = description

    text = (
        f"Флот AeroLine состоит из {total} воздушных судов, из них {active} "
        f"в активной эксплуатации, {in_maintenance} на плановом техническом "
        f"обслуживании. "
        + " ".join(type_lines)
    )

    return text, fleet_dict


def build_routes_section(routes: list[Route]) -> tuple[str, dict]:
    domestic = [r for r in routes if r.is_domestic == 1]
    international = [r for r in routes if r.is_domestic == 0]

    # Страны международных направлений
    countries = Counter(r.destination_country for r in international)

    # Самый длинный / короткий рейс
    sorted_by_dist = sorted(routes, key=lambda r: r.distance_km or 0)
    shortest = sorted_by_dist[0]
    longest = sorted_by_dist[-1]

    domestic_names = sorted(r.destination_city for r in domestic)
    intl_names = sorted(r.destination_city for r in international)

    text = (
        f"Хаб AeroLine — международный аэропорт {HUB_CITY} Шереметьево ({HUB_IATA}). "
        f"Авиакомпания выполняет рейсы по {len(routes)} направлениям: "
        f"{len(domestic)} внутрироссийских и {len(international)} международных.\n\n"
        f"Внутрироссийские направления из Москвы: {', '.join(domestic_names)}.\n\n"
        f"Международные направления из Москвы: {', '.join(intl_names)}.\n\n"
        f"Страны международных полётов: "
        + ", ".join(
            f"{country} ({cnt} {_plural_directions(cnt)})" if cnt > 1 else country
            for country, cnt in sorted(countries.items())
        )
        + ".\n\n"
        f"Самый короткий рейс AeroLine: {HUB_CITY} → {shortest.destination_city} "
        f"({shortest.distance_km} км, {_format_duration(shortest.flight_duration_min)}). "
        f"Самый длинный рейс: {HUB_CITY} → {longest.destination_city} "
        f"({longest.distance_km} км, {_format_duration(longest.flight_duration_min)})."
    )

    # Структурированный dict (для practical_info). Плоский, чтобы индексер
    # положил его одним чанком без резки. Без завершающих точек в значениях —
    # _flatten_section_value в indexer склеивает через ". ".
    routes_dict = {
        "summary": (
            f"Всего направлений: {len(routes)} "
            f"({len(domestic)} внутренних, {len(international)} международных). "
            f"Хаб: {HUB_CITY} ({HUB_IATA})"
        ),
        "domestic": ", ".join(
            f"{r.destination_city} ({r.destination_iata})" for r in sorted(
                domestic, key=lambda r: r.destination_city
            )
        ),
        "international": ", ".join(
            f"{r.destination_city} ({r.destination_iata}, {r.destination_country})"
            for r in sorted(international, key=lambda r: r.destination_city)
        ),
    }

    return text, routes_dict


def build_document() -> dict:
    init_db()
    db = SessionLocal()
    try:
        aircraft_list = db.query(Aircraft).all()
        routes = db.query(Route).all()
    finally:
        db.close()

    if not aircraft_list:
        raise RuntimeError(
            "В БД нет записей Aircraft. Сначала запустите seed: "
            "python -m backend.db.seed"
        )
    if not routes:
        raise RuntimeError("В БД нет записей Route. Сначала запустите seed.")

    fleet_text, fleet_info = build_fleet_section(aircraft_list)
    routes_text, routes_info = build_routes_section(routes)

    content = (
        "AeroLine — российская авиакомпания с хабом в Москве. "
        "Далее — подробная справка о флоте, маршрутной сети и характеристиках рейсов.\n\n"
        "Флот.\n" + fleet_text + "\n\n"
        "Маршрутная сеть.\n" + routes_text
    )

    document = {
        "title": "AeroLine — флот и маршрутная сеть",
        "category": "airline",
        "language": "ru",
        "content": content,
        "practical_info": {
            "fleet": fleet_info,
            "routes": routes_info,
            "hub": f"{HUB_CITY} Шереметьево ({HUB_IATA})",
        },
    }
    return document


def main() -> None:
    doc = build_document()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)

    logger.info("Документ сохранён: %s", OUTPUT_PATH)
    logger.info("Длина content: %d символов", len(doc["content"]))
    logger.info("Ключи practical_info: %s", list(doc["practical_info"].keys()))


if __name__ == "__main__":
    main()