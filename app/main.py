import logging
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

from app.admin.router import router as admin_router
from app.documents.router import router as documents_router
from app.order.router import router as order_router
from app.project.router import router as project_router

# ── Logging setup ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("hdd")


# ── Request logging middleware ──
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000
        if request.url.path not in ("/health", "/static"):
            logger.info(
                "%s %s %d %.0fms",
                request.method, request.url.path, response.status_code, duration_ms,
            )
        return response


from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup: ad-hoc migraties + database tabellen aanmaken."""
    from app.core.database import engine, Base
    from sqlalchemy import text
    import app.core.models       # noqa: F401
    import app.project.models    # noqa: F401
    import app.rules.models      # noqa: F401

    # Ad-hoc kolom migraties (SQLite heeft geen IF NOT EXISTS bij ALTER TABLE)
    migrations = [
        "ALTER TABLE orders ADD COLUMN vergunning_checklist TEXT",
        "ALTER TABLE boringen ADD COLUMN revisie INTEGER DEFAULT 0",
        "ALTER TABLE trace_punten ADD COLUMN variant INTEGER DEFAULT 0",
    ]
    with engine.connect() as conn:
        for stmt in migrations:
            try:
                conn.execute(text(stmt))
                conn.commit()
                logger.info("Migration OK: %s", stmt[:50])
            except Exception:
                pass  # kolom bestaat al

    Base.metadata.create_all(bind=engine)
    logger.info("HDD: Database ready")
    yield
    logger.info("HDD: Shutting down")


app = FastAPI(title="HDD Ontwerp Platform", version="0.1.0", lifespan=lifespan)
app.add_middleware(RequestLoggingMiddleware)

# ── Rate limiting ──
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/static", StaticFiles(directory="static"), name="static")

_error_templates = Jinja2Templates(directory="app/templates")

app.include_router(order_router)
app.include_router(project_router)
app.include_router(documents_router)
app.include_router(admin_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP errors als nette HTML pagina. 401 behoudt WWW-Authenticate header."""
    # 401 moet de browser login popup triggeren — niet overriden
    if exc.status_code == 401:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            {"detail": exc.detail},
            status_code=401,
            headers=exc.headers or {"WWW-Authenticate": "Basic"},
        )

    messages = {
        400: ("Ongeldige invoer", exc.detail or "De invoer is ongeldig."),
        403: ("Geen toegang", "Je hebt geen rechten voor deze pagina."),
        404: ("Niet gevonden", exc.detail or "De pagina die je zoekt bestaat niet."),
    }
    titel, bericht = messages.get(exc.status_code, ("Fout", exc.detail or "Er ging iets mis."))
    return _error_templates.TemplateResponse("error.html", {
        "request": request, "code": exc.status_code,
        "titel": titel, "bericht": bericht,
    }, status_code=exc.status_code)


@app.exception_handler(500)
async def server_error(request: Request, exc):
    return _error_templates.TemplateResponse("error.html", {
        "request": request, "code": 500,
        "titel": "Er ging iets mis",
        "bericht": "Er is een onverwachte fout opgetreden. Probeer het opnieuw of neem contact op.",
    }, status_code=500)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root_redirect():
    return RedirectResponse(url="/orders/")
