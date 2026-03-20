from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.documents.router import router as documents_router
from app.order.router import router as order_router
from app.project.router import router as project_router

app = FastAPI(title="HDD Ontwerp Platform", version="0.1.0")

app.mount("/static", StaticFiles(directory="static"), name="static")

_error_templates = Jinja2Templates(directory="app/templates")

app.include_router(order_router)
app.include_router(project_router)
app.include_router(documents_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Alle HTTP errors als nette HTML pagina i.p.v. raw JSON."""
    messages = {
        400: ("Ongeldige invoer", exc.detail or "De invoer is ongeldig."),
        401: ("Niet ingelogd", "Log in om deze pagina te bekijken."),
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


@app.on_event("startup")
def on_startup():
    """Create database tables on startup if they don't exist."""
    from app.core.database import engine, Base
    import app.core.models       # noqa: F401
    import app.project.models    # noqa: F401
    import app.rules.models      # noqa: F401
    Base.metadata.create_all(bind=engine)
    print("HDD: Database tables created")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root_redirect():
    return RedirectResponse(url="/orders/")
