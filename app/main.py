from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.documents.router import router as documents_router
from app.order.router import router as order_router
from app.project.router import router as project_router

app = FastAPI(title="HDD Ontwerp Platform", version="0.1.0")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(order_router)
app.include_router(project_router)
app.include_router(documents_router)


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
