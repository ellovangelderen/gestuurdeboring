import logging
import time

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.auth import get_current_user
from app.admin.router import router as admin_router
from app.documents.router import router as documents_router
from app.ops import router as ops_router
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
    import app.admin.models      # noqa: F401
    import app.core.audit        # noqa: F401

    # Ad-hoc kolom migraties (SQLite heeft geen IF NOT EXISTS bij ALTER TABLE)
    migrations = [
        "ALTER TABLE orders ADD COLUMN vergunning_checklist TEXT",
        "ALTER TABLE boringen ADD COLUMN revisie INTEGER DEFAULT 0",
        "ALTER TABLE trace_punten ADD COLUMN variant INTEGER DEFAULT 0",
        "ALTER TABLE boringen ADD COLUMN machine_type TEXT",
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

    # Seed referentiedata als tabellen leeg zijn (P5 patroon)
    from sqlalchemy.orm import Session as _Sess
    _db = _Sess(bind=engine)
    try:
        # Kaartlinks
        from app.admin.models import KaartLink, Klant
        if _db.query(KaartLink).count() == 0:
            for n, u, o, c, v in [
                ("RWS Beheerzones", "https://geoweb.rijkswaterstaat.nl/ModuleViewer/?app=635b0d2325b642c38ad0c9c82da66ae1", "Rijkswaterstaat beheergrenzen", "zonering", 1),
                ("ProRail Beperkingengebied", "https://maps.prorail.nl/portal/home/webmap/viewer.html?url=https%3A%2F%2Fmaps.prorail.nl%2Farcgis%2Frest%2Fservices%2FBeperkingengebied%2FFeatureServer&source=sd", "Spoorzone beperkingen", "zonering", 2),
                ("DINOloket", "https://www.dinoloket.nl/ondergrondgegevens", "Sonderingen, boringen, grondwater", "kaart", 3),
                ("Kaart Haarlem", "https://kaart.haarlem.nl/app/map/18", "Gemeente Haarlem riool + bomen", "gemeente", 4),
            ]:
                _db.add(KaartLink(naam=n, url=u, omschrijving=o, categorie=c, volgorde=v))
            _db.commit()
            logger.info("Kaartlinks: defaults geseeded")

        # Klanten (Martien's 50 opdrachtgevers)
        if _db.query(Klant).count() == 0:
            from scripts.seed_klanten import KLANTEN
            from pathlib import Path as _P
            for nr, code, naam, contact, logo in KLANTEN:
                if nr == 3:
                    code = "VB3"
                if not _db.query(Klant).filter_by(code=code).first():
                    _db.add(Klant(nr=nr, code=code, naam=naam, contact=contact, logo_bestand=None))
            _db.commit()
            logger.info("Klanten: %d geseeded", _db.query(Klant).count())

        # Logo cleanup verwijderd — te agressief, wiste waarden
        # voordat bestanden gekopieerd waren naar het volume.

        # Gebruikers (migratie van env vars naar DB)
        from app.admin.models import User
        if _db.query(User).count() == 0:
            from app.core.password import hash_password
            from app.core.config import settings as _settings
            for uname, pw_env, rol in [
                ("martien", _settings.USER_MARTIEN_PASSWORD, "admin"),
                ("ello", _settings.USER_MARTIEN_PASSWORD, "admin"),
                ("sopa", _settings.USER_SOPA_PASSWORD or _settings.USER_MARTIEN_PASSWORD, "tekenaar"),
                ("lucas", _settings.USER_LUCAS_PASSWORD or _settings.USER_MARTIEN_PASSWORD, "tekenaar"),
            ]:
                if pw_env:
                    _db.add(User(username=uname, wachtwoord_hash=hash_password(pw_env), rol=rol))
            if _settings.ENV in ("development", "staging") and _settings.USER_TEST_PASSWORD:
                _db.add(User(username="test", wachtwoord_hash=hash_password(_settings.USER_TEST_PASSWORD), rol="admin"))
            _db.commit()
            logger.info("Users: %d geseeded vanuit env vars", _db.query(User).count())

        # Boormachines
        from app.admin.models import Boormachine
        if _db.query(Boormachine).count() == 0:
            for naam, code, l, b, t in [
                ("Vermeer D7x11", "D7x11", 3.0, 1.5, 3.0),
                ("Vermeer D24x40", "D24x40", 5.0, 2.0, 11.0),
                ("Vermeer D40x55", "D40x55", 6.0, 2.5, 18.0),
                ("Vermeer D100x140", "D100x140", 9.0, 3.0, 45.0),
                ("Pers", "PERS", 2.0, 1.0, 0.0),
                ("Boogzinker", "BZ", 2.0, 1.0, 0.0),
            ]:
                _db.add(Boormachine(naam=naam, code=code, lengte_m=l, breedte_m=b, trekkracht_ton=t))
            _db.commit()
            logger.info("Boormachines: 6 defaults geseeded")

        # Eisenprofielen
        from app.rules.models import EisenProfiel
        if _db.query(EisenProfiel).count() == 0:
            for naam, dw, dwat, rmin in [
                ("RWS Rijksweg", 3.0, 5.0, 150),
                ("Waterschap waterkering", 5.0, 10.0, 200),
                ("Provincie", 2.0, 3.0, 120),
                ("Gemeente", 1.2, 1.5, 100),
                ("ProRail spoor", 4.0, 6.0, 150),
            ]:
                _db.add(EisenProfiel(naam=naam, dekking_weg_m=dw, dekking_water_m=dwat, Rmin_m=rmin))
            _db.commit()
            logger.info("Eisenprofielen: 5 defaults geseeded")

    except Exception as exc:
        logger.warning("Seed fout (niet kritisch): %s", exc)
    finally:
        _db.close()

    logger.info("HDD: Database ready")
    yield
    logger.info("HDD: Shutting down")


app = FastAPI(title="HDD Ontwerp Platform", version="0.1.0", lifespan=lifespan)
app.add_middleware(RequestLoggingMiddleware)

# CSRF bescherming
from app.core.csrf import CSRFMiddleware
app.add_middleware(CSRFMiddleware)

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
app.include_router(ops_router)


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


@app.get("/help", response_class=HTMLResponse)
def help_pagina(request: Request, user: str = Depends(get_current_user)):
    return _error_templates.TemplateResponse("help.html", {"request": request, "user": user})



@app.get("/logout")
def logout():
    """Stuur 401 terug zodat de browser de cached Basic Auth credentials vergeet."""
    return HTMLResponse(
        '<html><head><title>Uitgelogd</title></head>'
        '<body style="font-family:sans-serif;text-align:center;padding:4rem;max-width:500px;margin:0 auto;">'
        '<h2>Uitgelogd</h2>'
        '<p style="color:#666;">Je browser kan oude inloggegevens onthouden.</p>'
        '<p><strong>Om als andere gebruiker in te loggen:</strong></p>'
        '<ul style="text-align:left;display:inline-block;color:#444;">'
        '<li>Open een <strong>incognito/privé venster</strong>, of</li>'
        '<li>Druk <strong>Ctrl+Shift+Delete</strong> (Windows) / <strong>Cmd+Shift+Delete</strong> (Mac)<br>'
        '&nbsp;&nbsp;→ wis "Wachtwoorden" en "Gecachte afbeeldingen"</li>'
        '</ul>'
        '<p style="margin-top:1.5rem;">'
        '<a href="/" style="background:#1a237e;color:#fff;padding:0.5rem 1.5rem;border-radius:4px;text-decoration:none;">Opnieuw inloggen</a>'
        '</p>'
        '</body></html>',
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="HDD Platform"'},
    )


@app.get("/")
def root_redirect():
    return RedirectResponse(url="/orders/")
