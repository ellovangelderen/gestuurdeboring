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

# ── ADM-5: Systeeminstellingen ────────────────────────────────────────────

@router.get("/instellingen", response_class=HTMLResponse)
def instellingen_pagina(
    request: Request,
    user: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.admin.models import Instelling
    instellingen = {i.sleutel: i.waarde for i in db.query(Instelling).all()}
    return templates.TemplateResponse(
        "admin/instellingen.html",
        {"request": request, "user": user, "inst": instellingen},
    )


@router.post("/instellingen")
def instellingen_opslaan(
    request: Request,
    user: str = Depends(require_admin),
    db: Session = Depends(get_db),
    bundelfactor_1: str = Form("1.0"),
    bundelfactor_2: str = Form("2.0"),
    bundelfactor_3: str = Form("2.15"),
    bundelfactor_4: str = Form("2.73"),
    ruimfactor_enkelbuis: str = Form("1.5"),
    ruimfactor_bundel: str = Form("1.2"),
    ruimfactor_boogzinker: str = Form("1.1"),
    diepte_ld_gas: str = Form("-0.70"),
    diepte_hd_gas: str = Form("-1.00"),
    diepte_bgi: str = Form("-1.00"),
    standaard_dekking: str = Form("3.0"),
    standaard_tekenaar: str = Form("martien"),
):
    from app.admin.models import Instelling
    waarden = {
        "bundelfactor_1": bundelfactor_1,
        "bundelfactor_2": bundelfactor_2,
        "bundelfactor_3": bundelfactor_3,
        "bundelfactor_4": bundelfactor_4,
        "ruimfactor_enkelbuis": ruimfactor_enkelbuis,
        "ruimfactor_bundel": ruimfactor_bundel,
        "ruimfactor_boogzinker": ruimfactor_boogzinker,
        "diepte_ld_gas": diepte_ld_gas,
        "diepte_hd_gas": diepte_hd_gas,
        "diepte_bgi": diepte_bgi,
        "standaard_dekking": standaard_dekking,
        "standaard_tekenaar": standaard_tekenaar,
    }
    for sleutel, waarde in waarden.items():
        inst = db.query(Instelling).filter_by(sleutel=sleutel).first()
        if inst:
            inst.waarde = waarde.strip()
        else:
            db.add(Instelling(sleutel=sleutel, waarde=waarde.strip()))
    db.commit()
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/admin/instellingen", status_code=303)


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


# ── ADM-6: Eisenprofielen ────────────────────────────────────────────────

@router.get("/eisenprofielen", response_class=HTMLResponse)
def eisenprofielen_lijst(
    request: Request,
    user: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.rules.models import EisenProfiel
    profielen = db.query(EisenProfiel).all()
    return templates.TemplateResponse(
        "admin/eisenprofielen.html",
        {"request": request, "user": user, "profielen": profielen},
    )


@router.post("/eisenprofielen/nieuw")
def eisenprofiel_toevoegen(
    naam: str = Form(...),
    dekking_weg_m: str = Form(...),
    dekking_water_m: str = Form(...),
    Rmin_m: str = Form(...),
    user: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.rules.models import EisenProfiel
    from fastapi.responses import RedirectResponse
    db.add(EisenProfiel(
        naam=naam.strip(), dekking_weg_m=float(dekking_weg_m),
        dekking_water_m=float(dekking_water_m), Rmin_m=float(Rmin_m),
    ))
    db.commit()
    return RedirectResponse("/admin/eisenprofielen", status_code=303)


@router.post("/eisenprofielen/{profiel_id}/verwijder")
def eisenprofiel_verwijderen(
    profiel_id: str,
    user: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.rules.models import EisenProfiel
    from fastapi.responses import RedirectResponse
    ep = db.get(EisenProfiel, profiel_id)
    if ep:
        db.delete(ep)
        db.commit()
    return RedirectResponse("/admin/eisenprofielen", status_code=303)


# ── ADM-7: Externe kaartlinks ────────────────────────────────────────────

@router.get("/kaartlinks", response_class=HTMLResponse)
def kaartlinks_pagina(
    request: Request,
    user: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.admin.models import KaartLink
    links = db.query(KaartLink).order_by(KaartLink.volgorde).all()
    return templates.TemplateResponse(
        "admin/kaartlinks.html",
        {"request": request, "user": user, "links": links},
    )


@router.post("/kaartlinks/nieuw")
def kaartlink_toevoegen(
    naam: str = Form(...),
    url: str = Form(...),
    omschrijving: str = Form(""),
    categorie: str = Form("kaart"),
    user: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.admin.models import KaartLink
    from fastapi.responses import RedirectResponse
    max_v = db.query(KaartLink).count()
    db.add(KaartLink(
        naam=naam.strip(), url=url.strip(),
        omschrijving=omschrijving.strip() or None,
        categorie=categorie.strip(), volgorde=max_v + 1,
    ))
    db.commit()
    return RedirectResponse("/admin/kaartlinks", status_code=303)


@router.post("/kaartlinks/{link_id}/verwijder")
def kaartlink_verwijderen(
    link_id: str,
    user: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.admin.models import KaartLink
    from fastapi.responses import RedirectResponse
    link = db.get(KaartLink, link_id)
    if link:
        db.delete(link)
        db.commit()
    return RedirectResponse("/admin/kaartlinks", status_code=303)


# ── ADM-8: Logging / systeem status ──────────────────────────────────────

@router.get("/logs", response_class=HTMLResponse)
def logs_pagina(
    request: Request,
    user: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.order.models import Order
    from datetime import datetime, timezone, timedelta

    nu = datetime.now(timezone.utc)
    week_geleden = nu - timedelta(days=7)

    recente_orders = (
        db.query(Order)
        .filter(Order.ontvangen_op >= week_geleden)
        .order_by(Order.ontvangen_op.desc())
        .limit(20)
        .all()
    )

    from app.core.auth import _auth_failures
    auth_info = {u: len(f) for u, f in _auth_failures.items() if f}

    return templates.TemplateResponse(
        "admin/logs.html",
        {"request": request, "user": user,
         "recente_orders": recente_orders, "auth_failures": auth_info},
    )
