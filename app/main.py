from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db import get_database_path, init_db
from app.i18n import load_catalogs
from app.routers import api, pages
from app.seed import seed_if_empty


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Path(get_database_path()).parent.mkdir(parents=True, exist_ok=True)
    load_catalogs()
    init_db()
    seed_if_empty()
    yield


_STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Lunchie", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")
app.include_router(pages.router)
app.include_router(api.router)
