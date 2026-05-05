import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.api import admin as admin_api
from backend.api import sync as sync_api
from backend.db.database import get_db, init_db
from backend.db.queries import get_flight_info


os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

logger = logging.getLogger("skyassist.company")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Инициализация БД сервера авиакомпании...")
    init_db()
    logger.info("Сервер авиакомпании готов")
    yield
    logger.info("Сервер авиакомпании останавливается")


app = FastAPI(title="SkyAssist Company Server", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")

app.include_router(admin_api.router)
app.include_router(sync_api.router)


@app.get("/")
async def root():
    return RedirectResponse(url="/admin/")


@app.get("/admin", response_class=HTMLResponse)
@app.get("/admin/", response_class=HTMLResponse)
async def admin_ui(request: Request):
    return templates.TemplateResponse(request, "admin.html")


@app.get("/health")
async def health(db: Session = Depends(get_db)):
    flight = get_flight_info(db)

    return {
        "server": "company",
        "status": "ok",
        "flight_loaded": bool(flight),
        "flight_number": flight.get("flight_number") if flight else None,
    }
