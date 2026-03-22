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

# Logo directory: persistent volume op Railway (/data/logos), static lokaal
LOGO_DIR = Path("/data/logos") if Path("/data").exists() else Path("static/logos")
LOGO_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/logo/{filename}")
def serve_logo(filename: str):
    """Serveer logo bestand (uit persistent volume of static)."""
    from fastapi.responses import FileResponse
    # Check /data/logos eerst (Railway volume), dan static/logos
    for d in [Path("/data/logos"), Path("static/logos")]:
        fpath = d / filename
        if fpath.exists():
            return FileResponse(fpath)
    raise HTTPException(404, "Logo niet gevonden")


def require_admin(user: str = Depends(get_current_user), db: Session = Depends(get_db)) -> str:
    from app.admin.models import User
    db_user = db.query(User).filter_by(username=user).first()
    if not db_user or db_user.rol != "admin":
        raise HTTPException(status_code=403, detail="Alleen voor beheerders")
    return user


# ── Dashboard ─────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    user: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    import os
    from app.core.config import settings
    from app.order.models import Order, Boring, TracePunt, KLICUpload

    stats = {
        "orders": db.query(Order).count(),
        "boringen": db.query(Boring).count(),
        "tracepunten": db.query(TracePunt).count(),
        "klic_uploads": db.query(KLICUpload).count(),
        "klanten": db.query(Klant).count(),
    }

    # Database info
    db_path_str = settings.DATABASE_URL.replace("sqlite:///", "").replace("sqlite:", "")
    db_path = Path(db_path_str)
    stats["db_grootte_mb"] = round(db_path.stat().st_size / 1024 / 1024, 1) if db_path.exists() else 0
    stats["db_path"] = db_path_str

    # Health checks
    health = {
        "db_exists": db_path.exists(),
        "db_on_volume": db_path_str.startswith("/data"),
        "volume_exists": Path("/data").exists(),
        "env": settings.ENV,
    }
    if Path("/data").exists():
        try:
            stat = os.statvfs("/data")
            health["volume_free_mb"] = round(stat.f_frsize * stat.f_bavail / 1024 / 1024)
            health["volume_used_pct"] = round((1 - stat.f_bavail / stat.f_blocks) * 100, 1)
        except Exception:
            health["volume_free_mb"] = 0
            health["volume_used_pct"] = 0

    # Alles OK?
    health["ok"] = health["db_exists"] and health["db_on_volume"] and health["volume_exists"]

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {"request": request, "user": user, "stats": stats, "health": health},
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
    from app.core.audit import log_audit
    log_audit(db, user, "aangemaakt", "Klant", klant.id, f"code={code}, naam={naam}")
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
    from app.core.audit import log_audit
    log_audit(db, user, "verwijderd", "Klant", klant_id, f"code={klant.code}, naam={klant.naam}")
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

    # Check of er een bestand geselecteerd is
    if not logo.filename or not logo.filename.strip():
        from fastapi.responses import RedirectResponse
        return RedirectResponse("/admin/klanten", status_code=303)

    content = await logo.read()
    if len(content) < 10:
        from fastapi.responses import RedirectResponse
        return RedirectResponse("/admin/klanten", status_code=303)

    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(413, "Logo te groot (max 5MB)")

    # Valideer bestandstype
    suffix = Path(logo.filename).suffix.lower()
    if suffix not in (".jpg", ".jpeg", ".png", ".svg", ".webp"):
        raise HTTPException(400, "Alleen JPG, PNG, SVG of WebP logo's toegestaan")

    safe_name = f"logo_{klant.code}{suffix}"
    dest = LOGO_DIR / safe_name
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


# ── ADM-1: Gebruikersbeheer (CRUD) ────────────────────────────────────────

@router.get("/users", response_class=HTMLResponse)
def users_overzicht(
    request: Request,
    user: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.admin.models import User
    users = db.query(User).order_by(User.username).all()
    return templates.TemplateResponse(
        "admin/users.html",
        {"request": request, "user": user, "users": users, "rollen": ["admin", "tekenaar", "viewer"]},
    )


@router.post("/users/nieuw")
def user_aanmaken(
    username: str = Form(...),
    wachtwoord: str = Form(...),
    rol: str = Form("tekenaar"),
    user: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.admin.models import User
    from app.core.password import hash_password, validate_password

    from urllib.parse import quote
    from fastapi.responses import RedirectResponse

    username = username.strip().lower()
    if not username:
        return RedirectResponse(f"/admin/users?fout={quote('Gebruikersnaam is verplicht')}", status_code=303)
    if db.query(User).filter_by(username=username).first():
        return RedirectResponse(f"/admin/users?fout={quote(f'Gebruiker {username} bestaat al')}", status_code=303)
    if rol not in ("admin", "tekenaar", "viewer"):
        return RedirectResponse(f"/admin/users?fout={quote('Ongeldige rol')}", status_code=303)

    fouten = validate_password(wachtwoord, username)
    if fouten:
        return RedirectResponse(f"/admin/users?fout={quote('; '.join(fouten))}", status_code=303)

    db.add(User(
        username=username,
        wachtwoord_hash=hash_password(wachtwoord),
        rol=rol,
    ))
    db.commit()

    from app.core.audit import log_audit
    log_audit(db, user, "aangemaakt", "User", username, f"rol={rol}")

    return RedirectResponse("/admin/users", status_code=303)


@router.post("/users/{user_id}/update")
def user_update(
    user_id: str,
    rol: str = Form(...),
    user: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.admin.models import User
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "Gebruiker niet gevonden")
    if rol not in ("admin", "tekenaar", "viewer"):
        raise HTTPException(400, "Ongeldige rol")
    target.rol = rol
    db.commit()

    from app.core.audit import log_audit
    log_audit(db, user, "gewijzigd", "User", target.username, f"rol={rol}")

    from fastapi.responses import RedirectResponse
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/users/{user_id}/wachtwoord")
def user_wachtwoord_wijzigen(
    user_id: str,
    wachtwoord: str = Form(...),
    user: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.admin.models import User
    from app.core.password import hash_password, validate_password
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "Gebruiker niet gevonden")

    fouten = validate_password(wachtwoord, target.username)
    if fouten:
        from urllib.parse import quote
        from fastapi.responses import RedirectResponse
        return RedirectResponse(f"/admin/users?fout={quote('; '.join(fouten))}", status_code=303)

    target.wachtwoord_hash = hash_password(wachtwoord)
    db.commit()

    from app.core.audit import log_audit
    log_audit(db, user, "wachtwoord_gewijzigd", "User", target.username)

    from fastapi.responses import RedirectResponse
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/users/{user_id}/deactiveer")
def user_deactiveer(
    user_id: str,
    user: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.admin.models import User
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "Gebruiker niet gevonden")
    if target.username == user:
        raise HTTPException(400, "Je kunt jezelf niet deactiveren")

    target.actief = not target.actief
    db.commit()

    from app.core.audit import log_audit
    status = "geactiveerd" if target.actief else "gedeactiveerd"
    log_audit(db, user, status, "User", target.username)

    from fastapi.responses import RedirectResponse
    return RedirectResponse("/admin/users", status_code=303)


# ── B4: Boormachines ──────────────────────────────────────────────────────

@router.get("/boormachines", response_class=HTMLResponse)
def boormachines_lijst(
    request: Request,
    user: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.admin.models import Boormachine
    machines = db.query(Boormachine).order_by(Boormachine.naam).all()
    fout = request.query_params.get("fout", "")
    return templates.TemplateResponse(
        "admin/boormachines.html",
        {"request": request, "user": user, "machines": machines, "fout": fout},
    )


@router.post("/boormachines/nieuw")
def boormachine_toevoegen(
    naam: str = Form(...),
    code: str = Form(...),
    lengte_m: str = Form("3.0"),
    breedte_m: str = Form("1.5"),
    trekkracht_ton: str = Form("0"),
    user: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.admin.models import Boormachine
    from urllib.parse import quote
    from fastapi.responses import RedirectResponse

    code = code.strip().upper()
    if db.query(Boormachine).filter_by(code=code).first():
        return RedirectResponse(f"/admin/boormachines?fout={quote(f'Code {code} bestaat al')}", status_code=303)

    try:
        db.add(Boormachine(
            naam=naam.strip(), code=code,
            lengte_m=float(lengte_m), breedte_m=float(breedte_m),
            trekkracht_ton=float(trekkracht_ton or 0),
        ))
        db.commit()
    except Exception:
        db.rollback()
        return RedirectResponse(f"/admin/boormachines?fout={quote('Ongeldige invoer')}", status_code=303)

    from app.core.audit import log_audit
    log_audit(db, user, "aangemaakt", "Boormachine", code)

    return RedirectResponse("/admin/boormachines", status_code=303)


@router.post("/boormachines/{machine_id}/update")
def boormachine_wijzigen(
    machine_id: str,
    naam: str = Form(...),
    code: str = Form(...),
    lengte_m: str = Form("3.0"),
    breedte_m: str = Form("1.5"),
    trekkracht_ton: str = Form("0"),
    user: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.admin.models import Boormachine
    from fastapi.responses import RedirectResponse

    m = db.get(Boormachine, machine_id)
    if not m:
        raise HTTPException(404, "Boormachine niet gevonden")

    m.naam = naam.strip()
    m.code = code.strip().upper()
    m.lengte_m = float(lengte_m)
    m.breedte_m = float(breedte_m)
    m.trekkracht_ton = float(trekkracht_ton or 0)
    db.commit()

    from app.core.audit import log_audit
    log_audit(db, user, "gewijzigd", "Boormachine", m.code)

    return RedirectResponse("/admin/boormachines", status_code=303)


@router.post("/boormachines/{machine_id}/verwijder")
def boormachine_verwijderen(
    machine_id: str,
    user: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from app.admin.models import Boormachine
    from fastapi.responses import RedirectResponse

    m = db.get(Boormachine, machine_id)
    if m:
        from app.core.audit import log_audit
        log_audit(db, user, "verwijderd", "Boormachine", m.code)
        db.delete(m)
        db.commit()

    return RedirectResponse("/admin/boormachines", status_code=303)


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

    # Gebruik naive datetime voor vergelijking (SQLite slaat naive op)
    nu = datetime.now(timezone.utc).replace(tzinfo=None)
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

    # Audit log
    from app.core.audit import AuditLog
    audit_entries = (
        db.query(AuditLog)
        .order_by(AuditLog.tijdstip.desc())
        .limit(50)
        .all()
    )

    return templates.TemplateResponse(
        "admin/logs.html",
        {"request": request, "user": user,
         "recente_orders": recente_orders, "auth_failures": auth_info,
         "audit_entries": audit_entries},
    )
