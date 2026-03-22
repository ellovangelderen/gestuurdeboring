"""Admin panel — systeembeheer, alleen voor admin users."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")

ADMIN_USERS = {"martien", "ello", "test"}


def require_admin(user: str = Depends(get_current_user)) -> str:
    if user not in ADMIN_USERS:
        raise HTTPException(status_code=403, detail="Alleen voor beheerders")
    return user


@router.get("/", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    user: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin dashboard — overzicht van systeemstatus."""
    from app.order.models import Order, Boring, TracePunt, KLICUpload
    from pathlib import Path

    stats = {
        "orders": db.query(Order).count(),
        "boringen": db.query(Boring).count(),
        "tracepunten": db.query(TracePunt).count(),
        "klic_uploads": db.query(KLICUpload).count(),
    }

    # Database grootte
    db_path = Path("data/hdd.db")
    if not db_path.exists():
        db_path = Path("hdd.db")
    stats["db_grootte_mb"] = round(db_path.stat().st_size / 1024 / 1024, 1) if db_path.exists() else 0

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {"request": request, "user": user, "stats": stats},
    )
