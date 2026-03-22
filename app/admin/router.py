"""Admin panel — systeembeheer, alleen voor admin users."""
import io
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.admin.models import Klant

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")

ADMIN_USERS = {"martien", "ello", "test"}


def require_admin(user: str = Depends(get_current_user)) -> str:
    if user not in ADMIN_USERS:
        raise HTTPException(status_code=403, detail="Alleen voor beheerders")
    return user


# ── Dashboard ─────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    user: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.order.models import Order, Boring, TracePunt, KLICUpload

    stats = {
        "orders": db.query(Order).count(),
        "boringen": db.query(Boring).count(),
        "tracepunten": db.query(TracePunt).count(),
        "klic_uploads": db.query(KLICUpload).count(),
        "klanten": db.query(Klant).count(),
    }
    db_path = Path("data/hdd.db")
    if not db_path.exists():
        db_path = Path("hdd.db")
    stats["db_grootte_mb"] = round(db_path.stat().st_size / 1024 / 1024, 1) if db_path.exists() else 0

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {"request": request, "user": user, "stats": stats},
    )


# ── ADM-2: Klantbeheer ───────────────────────────────────────────────────

@router.get("/klanten", response_class=HTMLResponse)
def klanten_lijst(
    request: Request,
    user: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    klanten = db.query(Klant).order_by(Klant.nr).all()
    return templates.TemplateResponse(
        "admin/klanten.html",
        {"request": request, "user": user, "klanten": klanten},
    )


@router.post("/klanten/nieuw")
def klant_toevoegen(
    code: str = Form(...),
    naam: str = Form(...),
    contact: str = Form(""),
    logo_bestand: str = Form(""),
    nr: str = Form(""),
    user: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.query(Klant).filter_by(code=code.strip().upper()).first():
        raise HTTPException(400, f"Klantcode '{code}' bestaat al")
    klant = Klant(
        code=code.strip().upper(),
        naam=naam.strip(),
        contact=contact.strip() or None,
        logo_bestand=logo_bestand.strip() or None,
        nr=int(nr) if nr.strip() else None,
    )
    db.add(klant)
    db.commit()
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/admin/klanten", status_code=303)


@router.post("/klanten/{klant_id}/update")
def klant_bewerken(
    klant_id: str,
    code: str = Form(...),
    naam: str = Form(...),
    contact: str = Form(""),
    logo_bestand: str = Form(""),
    user: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    klant = db.get(Klant, klant_id)
    if not klant:
        raise HTTPException(404, "Klant niet gevonden")
    klant.code = code.strip().upper()
    klant.naam = naam.strip()
    klant.contact = contact.strip() or None
    klant.logo_bestand = logo_bestand.strip() or None
    db.commit()
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/admin/klanten", status_code=303)


@router.post("/klanten/{klant_id}/verwijder")
def klant_verwijderen(
    klant_id: str,
    user: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    klant = db.get(Klant, klant_id)
    if not klant:
        raise HTTPException(404, "Klant niet gevonden")
    db.delete(klant)
    db.commit()
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/admin/klanten", status_code=303)


@router.post("/klanten/logo/{klant_id}")
async def klant_logo_upload(
    klant_id: str,
    logo: UploadFile = File(...),
    user: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    klant = db.get(Klant, klant_id)
    if not klant:
        raise HTTPException(404, "Klant niet gevonden")

    content = await logo.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(413, "Logo te groot (max 5MB)")

    logo_dir = Path("static/logos")
    logo_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"logo_{klant.code}.{Path(logo.filename).suffix.lstrip('.')}"
    dest = logo_dir / safe_name
    with open(dest, "wb") as f:
        f.write(content)

    klant.logo_bestand = safe_name
    db.commit()
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/admin/klanten", status_code=303)


# ── ADM-4: Data export ───────────────────────────────────────────────────

@router.get("/export", response_class=HTMLResponse)
def export_pagina(
    request: Request,
    user: str = Depends(require_admin),
):
    return templates.TemplateResponse(
        "admin/export.html",
        {"request": request, "user": user},
    )


@router.get("/export/database")
def export_database(user: str = Depends(require_admin)):
    """Download de SQLite database als bestand."""
    db_path = Path("data/hdd.db")
    if not db_path.exists():
        db_path = Path("hdd.db")
    if not db_path.exists():
        raise HTTPException(404, "Database niet gevonden")

    return StreamingResponse(
        open(db_path, "rb"),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="hdd-backup.db"'},
    )


@router.get("/export/klanten-csv")
def export_klanten_csv(
    user: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Export klantlijst als CSV."""
    import csv
    klanten = db.query(Klant).order_by(Klant.nr).all()
    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Nr", "Code", "Naam", "Contact", "Logo"])
    for k in klanten:
        writer.writerow([k.nr or "", k.code, k.naam, k.contact or "", k.logo_bestand or ""])

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="klanten.csv"'},
    )
