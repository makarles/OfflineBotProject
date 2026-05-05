from __future__ import annotations

import json
from pathlib import Path

import httpx


COMPANY_EXPORT_URL = "http://127.0.0.1:8500/api/sync/export"
AIRCRAFT_IMPORT_URL = "http://127.0.0.1:8000/api/sync/import"
SYNC_DIR = Path("data/sync")
SYNC_FILE = SYNC_DIR / "flight_package.json"


def main() -> None:
    SYNC_DIR.mkdir(parents=True, exist_ok=True)

    with httpx.Client(timeout=30.0) as client:
        export_response = client.get(COMPANY_EXPORT_URL)
        export_response.raise_for_status()
        package = export_response.json()

        SYNC_FILE.write_text(
            json.dumps(package, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        import_response = client.post(AIRCRAFT_IMPORT_URL, json=package)
        import_response.raise_for_status()

        print("JSON-пакет сохранён:", SYNC_FILE)
        print("Импорт на бортовой сервер:", import_response.json())


if __name__ == "__main__":
    main()