from typing import Optional

import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.dependencies import fetch_project, get_workspace_id
from app.core.models import Workspace
from app.geo.ahn5 import haal_maaiveld_op
from app.geo.coords import rd_to_wgs84
from app.project.models import Project
from app.order.models import (
    Berekening,
    Doorsnede,
    KLICLeiding,
    KLICUpload,
    MaaiveldOverride,
    TracePunt,
)
from app.rules.models import EisenProfiel, ProjectEisenProfiel

router = APIRouter(prefix="/api/v1")
templates = Jinja2Templates(directory="app/templates")

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def _f(v: str) -> Optional[float]:
    """Converteer leeg Form string-veld naar None (optionele float)."""
    return float(v) if v and v.strip() else None


def _i(v: str) -> Optional[int]:
    """Converteer leeg Form string-veld naar None (optionele int)."""
    return int(v) if v and v.strip() else None


# ── Projectenlijst ──────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def projecten_lijst(
    request: Request,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workspace_id = get_workspace_id(user)
    projecten = (
        db.query(Project)
        .filter_by(workspace_id=workspace_id)
        .order_by(Project.aangemaakt_op.desc())
        .all()
    )
    return templates.TemplateResponse(
        "project/list.html", {"request": request, "projecten": projecten, "user": user}
    )


# ── Project aanmaken ────────────────────────────────────────────────────────

@router.get("/projecten/nieuw", response_class=HTMLResponse)
def project_nieuw_form(
    request: Request,
    user: str = Depends(get_current_user),
):
    return templates.TemplateResponse(
        "project/create.html", {"request": request, "user": user}
    )


@router.post("/projecten/nieuw")
def project_nieuw_opslaan(
    request: Request,
    naam: str = Form(...),
    opdrachtgever: str = Form(""),
    ordernummer: str = Form(""),
    materiaal: str = Form("PE100"),
    SDR: str = Form("11"),
    De_mm: str = Form("160.0"),
    dn_mm: str = Form(""),
    medium: str = Form("Drukloos"),
    Db_mm: str = Form("60.0"),
    Dp_mm: str = Form("110.0"),
    Dg_mm: str = Form("240.0"),
    intreehoek_gr: str = Form("18.0"),
    uittreehoek_gr: str = Form("22.0"),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not naam or not naam.strip():
        raise HTTPException(status_code=400, detail="Naam is verplicht")

    workspace_id = get_workspace_id(user)
    project = Project(
        workspace_id=workspace_id,
        naam=naam.strip(),
        opdrachtgever=opdrachtgever or None,
        ordernummer=ordernummer or None,
        materiaal=materiaal,
        SDR=_i(SDR) or 11,
        De_mm=_f(De_mm) or 160.0,
        dn_mm=_f(dn_mm),
        medium=medium,
        Db_mm=_f(Db_mm) or 60.0,
        Dp_mm=_f(Dp_mm) or 110.0,
        Dg_mm=_f(Dg_mm) or 240.0,
        intreehoek_gr=_f(intreehoek_gr) or 18.0,
        uittreehoek_gr=_f(uittreehoek_gr) or 22.0,
        aangemaakt_door=user,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return RedirectResponse(f"/api/v1/projecten/{project.id}", status_code=303)


# ── Project detail ───────────────────────────────────────────────────────────

@router.get("/projecten/{project_id}", response_class=HTMLResponse)
def project_detail(
    request: Request,
    project_id: str,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = fetch_project(project_id, db)
    return templates.TemplateResponse(
        "project/detail.html", {"request": request, "project": project, "user": user}
    )


@router.post("/projecten/{project_id}/update")
def project_update(
    project_id: str,
    naam: str = Form(...),
    opdrachtgever: str = Form(""),
    ordernummer: str = Form(""),
    materiaal: str = Form("PE100"),
    SDR: str = Form("11"),
    De_mm: str = Form("160.0"),
    dn_mm: str = Form(""),
    medium: str = Form("Drukloos"),
    Db_mm: str = Form("60.0"),
    Dp_mm: str = Form("110.0"),
    Dg_mm: str = Form("240.0"),
    intreehoek_gr: str = Form("18.0"),
    uittreehoek_gr: str = Form("22.0"),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not naam or not naam.strip():
        raise HTTPException(status_code=400, detail="Naam is verplicht")
    project = fetch_project(project_id, db)
    project.naam = naam.strip()
    project.opdrachtgever = opdrachtgever or None
    project.ordernummer = ordernummer or None
    project.materiaal = materiaal
    project.SDR = _i(SDR) or 11
    project.De_mm = _f(De_mm) or 160.0
    project.dn_mm = _f(dn_mm)
    project.medium = medium
    project.Db_mm = _f(Db_mm) or 60.0
    project.Dp_mm = _f(Dp_mm) or 110.0
    project.Dg_mm = _f(Dg_mm) or 240.0
    project.intreehoek_gr = _f(intreehoek_gr) or 18.0
    project.uittreehoek_gr = _f(uittreehoek_gr) or 22.0
    db.commit()
    return RedirectResponse(f"/api/v1/projecten/{project_id}", status_code=303)


# ── Tracé ────────────────────────────────────────────────────────────────────

@router.get("/projecten/{project_id}/trace", response_class=HTMLResponse)
def trace_form(
    request: Request,
    project_id: str,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = fetch_project(project_id, db)
    punten_wgs84 = []
    for p in project.trace_punten:
        lat, lon = rd_to_wgs84(p.RD_x, p.RD_y)
        punten_wgs84.append({"label": p.label, "lat": lat, "lon": lon})
    return templates.TemplateResponse(
        "project/trace.html",
        {"request": request, "project": project, "punten_wgs84": punten_wgs84, "user": user},
    )


@router.post("/projecten/{project_id}/trace")
def trace_opslaan(
    project_id: str,
    RD_x_list: str = Form(...),
    RD_y_list: str = Form(...),
    type_list: str = Form(...),
    label_list: str = Form(...),
    Rh_list: str = Form(""),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = fetch_project(project_id, db)

    try:
        xs = [float(v.strip()) for v in RD_x_list.split(",") if v.strip()]
        ys = [float(v.strip()) for v in RD_y_list.split(",") if v.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Ongeldige RD-coördinaten")

    types = [v.strip() for v in type_list.split(",") if v.strip()]
    labels = [v.strip() for v in label_list.split(",") if v.strip()]
    rhs = [v.strip() for v in Rh_list.split(",")] if Rh_list else [""] * len(xs)

    for punt in project.trace_punten:
        db.delete(punt)
    db.flush()

    for i, (x, y, t, label) in enumerate(zip(xs, ys, types, labels)):
        rh_val = rhs[i] if i < len(rhs) else ""
        try:
            rh = float(rh_val) if rh_val else None
        except ValueError:
            rh = None
        punt = TracePunt(
            project_id=project_id,
            volgorde=i,
            type=t,
            RD_x=x,
            RD_y=y,
            label=label,
            Rh_m=rh,
        )
        db.add(punt)

    db.commit()
    return RedirectResponse(f"/api/v1/projecten/{project_id}", status_code=303)


# ── Brondata ─────────────────────────────────────────────────────────────────

@router.get("/projecten/{project_id}/brondata", response_class=HTMLResponse)
def brondata_form(
    request: Request,
    project_id: str,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = fetch_project(project_id, db)

    # Bouw leidingen-samenvatting per (beheerder, leidingtype)
    klic_samenvatting: list[dict] = []
    diepte_waarschuwing = False
    laatste_upload = None
    klic_uploads = db.query(KLICUpload).filter_by(order_id=project_id).order_by(KLICUpload.upload_datum).all()
    if klic_uploads:
        laatste_upload = klic_uploads[-1]
        if laatste_upload.verwerkt:
            leidingen = (
                db.query(KLICLeiding)
                .filter_by(klic_upload_id=laatste_upload.id)
                .all()
            )
            # Aggregeer per (beheerder, leidingtype)
            agg: dict[tuple, dict] = {}
            for l in leidingen:
                key = (l.beheerder or "", l.leidingtype or "")
                if key not in agg:
                    agg[key] = {"beheerder": key[0], "leidingtype": key[1],
                                "aantal": 0, "sleufloze": False}
                agg[key]["aantal"] += 1
                if l.sleufloze_techniek:
                    agg[key]["sleufloze"] = True
            klic_samenvatting = sorted(agg.values(), key=lambda r: (r["beheerder"], r["leidingtype"]))

            # Diepte waarschuwing als alle leidingen geen diepte hebben
            total = len(leidingen)
            met_diepte = sum(1 for l in leidingen if l.diepte_m is not None)
            diepte_waarschuwing = total > 0 and met_diepte == 0

    return templates.TemplateResponse(
        "project/brondata.html",
        {
            "request": request,
            "project": project,
            "user": user,
            "klic_samenvatting": klic_samenvatting,
            "diepte_waarschuwing": diepte_waarschuwing,
            "laatste_upload": laatste_upload,
        },
    )


@router.post("/projecten/{project_id}/maaiveld")
def maaiveld_opslaan(
    project_id: str,
    MVin_NAP_m: float = Form(...),
    MVuit_NAP_m: float = Form(...),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sla handmatige maaiveldwaarden op. Zet bron op 'handmatig'. AHN5-referentiewaarden blijven bewaard."""
    project = fetch_project(project_id, db)
    if project.maaiveld_override:
        mv = project.maaiveld_override
        mv.MVin_NAP_m = MVin_NAP_m
        mv.MVuit_NAP_m = MVuit_NAP_m
        mv.bron = "handmatig"
        mv.MVin_bron = "handmatig"
        mv.MVuit_bron = "handmatig"
        # MVin_ahn5_m en MVuit_ahn5_m blijven ongewijzigd (override-principe)
    else:
        mv = MaaiveldOverride(
            project_id=project_id,
            MVin_NAP_m=MVin_NAP_m,
            MVuit_NAP_m=MVuit_NAP_m,
            bron="handmatig",
            MVin_bron="handmatig",
            MVuit_bron="handmatig",
        )
        db.add(mv)
    db.commit()
    return RedirectResponse(f"/api/v1/projecten/{project_id}/brondata", status_code=303)


@router.post("/projecten/{project_id}/maaiveld/ahn5")
def maaiveld_ahn5_ophalen(
    project_id: str,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Roep AHN5 WCS aan voor intree- en uittree-punt. Sla resultaat op. Retourneert altijd HTTP 200."""
    project = fetch_project(project_id, db)

    intree = next((p for p in project.trace_punten if p.type == "intree"), None)
    uittree = next((p for p in project.trace_punten if p.type == "uittree"), None)

    if intree is None and uittree is None:
        return JSONResponse({
            "status": "fout",
            "melding": "Geen intree- of uittree-punt gevonden — sla eerst het tracé op",
        })

    mv_in: Optional[float] = None
    mv_uit: Optional[float] = None

    if intree is not None:
        mv_in = haal_maaiveld_op(intree.RD_x, intree.RD_y)
    if uittree is not None:
        mv_uit = haal_maaiveld_op(uittree.RD_x, uittree.RD_y)

    if mv_in is None and mv_uit is None:
        return JSONResponse({
            "status": "fout",
            "melding": "AHN5 service niet bereikbaar — vul handmatig in",
        })

    # Bepaal bron per punt
    in_bron  = "ahn5" if mv_in  is not None else "niet_beschikbaar"
    uit_bron = "ahn5" if mv_uit is not None else "niet_beschikbaar"

    # Gebruik bestaande waarden als AHN5 gedeeltelijk mislukt
    mv = project.maaiveld_override
    if mv is None:
        mv = MaaiveldOverride(project_id=project_id)
        db.add(mv)

    if mv_in is not None:
        mv.MVin_NAP_m = mv_in
        mv.MVin_ahn5_m = mv_in
    if mv_uit is not None:
        mv.MVuit_NAP_m = mv_uit
        mv.MVuit_ahn5_m = mv_uit

    mv.MVin_bron  = in_bron
    mv.MVuit_bron = uit_bron
    mv.bron = "ahn5"
    db.commit()

    status = "ok" if (mv_in is not None and mv_uit is not None) else "partial"
    response: dict = {
        "status": status,
        "MVin_NAP_m": mv_in,
        "MVuit_NAP_m": mv_uit,
        "MVin_bron": in_bron,
        "MVuit_bron": uit_bron,
    }
    if status == "partial":
        ontbrekend = []
        if mv_in is None:
            ontbrekend.append("intree")
        if mv_uit is None:
            ontbrekend.append("uittree")
        response["melding"] = f"AHN5 niet beschikbaar voor: {', '.join(ontbrekend)}"

    return JSONResponse(response)


@router.post("/projecten/{project_id}/klic")
async def klic_upload(
    project_id: str,
    klic_zip: UploadFile = File(...),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = fetch_project(project_id, db)
    dest_dir = UPLOAD_DIR / project_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    # Path().name voorkomt path traversal (bijv. ../../etc/passwd)
    safe_filename = Path(klic_zip.filename).name
    dest_path = dest_dir / safe_filename

    with open(dest_path, "wb") as f:
        shutil.copyfileobj(klic_zip.file, f)

    upload = KLICUpload(
        order_id=project_id,
        bestandsnaam=safe_filename,
        bestandspad=str(dest_path),
        verwerkt=False,
    )
    db.add(upload)
    db.commit()
    return RedirectResponse(f"/api/v1/projecten/{project_id}/brondata", status_code=303)


@router.post("/projecten/{project_id}/klic/{upload_id}/verwerken")
def klic_verwerken(
    project_id: str,
    upload_id: str,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger KLIC parsing synchroon. Redirect naar brondata na verwerking."""
    fetch_project(project_id, db)
    upload = db.get(KLICUpload, upload_id)
    if not upload or upload.order_id != project_id:
        raise HTTPException(status_code=404, detail="KLIC upload niet gevonden")

    from app.geo.klic_parser import verwerk_klic_zip
    verwerk_klic_zip(upload.bestandspad, project_id, upload_id, db)
    return RedirectResponse(f"/api/v1/projecten/{project_id}/brondata", status_code=303)


@router.get("/projecten/{project_id}/klic/status")
def klic_status(
    project_id: str,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """JSON status van de meest recente KLIC upload voor dit project."""
    fetch_project(project_id, db)
    upload = (
        db.query(KLICUpload)
        .filter_by(order_id=project_id)
        .order_by(KLICUpload.upload_datum.desc())
        .first()
    )
    if not upload:
        return JSONResponse({"verwerkt": False, "aantal_leidingen": 0,
                             "aantal_beheerders": 0, "diepte_waarschuwing": False,
                             "sleufloze_count": 0})

    sleufloze_count = (
        db.query(KLICLeiding)
        .filter_by(klic_upload_id=upload.id, sleufloze_techniek=True)
        .count()
    )

    diepte_waarschuwing = False
    if upload.verwerkt:
        total = db.query(KLICLeiding).filter_by(klic_upload_id=upload.id).count()
        met_diepte = (
            db.query(KLICLeiding)
            .filter(
                KLICLeiding.klic_upload_id == upload.id,
                KLICLeiding.diepte_m.isnot(None),
            )
            .count()
        )
        diepte_waarschuwing = total > 0 and met_diepte == 0

    return JSONResponse({
        "verwerkt": upload.verwerkt,
        "aantal_leidingen": upload.aantal_leidingen or 0,
        "aantal_beheerders": upload.aantal_beheerders or 0,
        "diepte_waarschuwing": diepte_waarschuwing,
        "sleufloze_count": sleufloze_count,
    })


@router.post("/projecten/{project_id}/doorsneden")
def doorsneden_opslaan(
    project_id: str,
    afstand_list: str = Form(...),
    NAP_list: str = Form(...),
    grondtype_list: str = Form(...),
    GWS_list: str = Form(""),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = fetch_project(project_id, db)

    try:
        afstanden = [float(v.strip()) for v in afstand_list.split(",") if v.strip()]
        naps = [float(v.strip()) for v in NAP_list.split(",") if v.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Ongeldige afstanden of NAP-waarden")

    grondtypen = [v.strip() for v in grondtype_list.split(",") if v.strip()]
    gwssen = [v.strip() for v in GWS_list.split(",")] if GWS_list else [""] * len(afstanden)

    for d in project.doorsneden:
        db.delete(d)
    db.flush()

    for i, (afstand, nap, grondtype) in enumerate(zip(afstanden, naps, grondtypen)):
        gws_val = gwssen[i] if i < len(gwssen) else ""
        try:
            gws = float(gws_val) if gws_val else None
        except ValueError:
            gws = None
        ds = Doorsnede(
            project_id=project_id,
            volgorde=i,
            afstand_m=afstand,
            NAP_m=nap,
            grondtype=grondtype,
            GWS_m=gws,
        )
        db.add(ds)
    db.commit()
    return RedirectResponse(f"/api/v1/projecten/{project_id}/brondata", status_code=303)


@router.post("/projecten/{project_id}/intrekkracht")
def intrekkracht_opslaan(
    project_id: str,
    Ttot_N: float = Form(...),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = fetch_project(project_id, db)
    if project.berekening:
        project.berekening.Ttot_N = Ttot_N
        project.berekening.bron = "sigma_override"
    else:
        b = Berekening(project_id=project_id, Ttot_N=Ttot_N, bron="sigma_override")
        db.add(b)
    db.commit()
    return RedirectResponse(f"/api/v1/projecten/{project_id}/brondata", status_code=303)


# ── Eisenprofiel ──────────────────────────────────────────────────────────────

@router.get("/projecten/{project_id}/eisen", response_class=HTMLResponse)
def eisen_form(
    request: Request,
    project_id: str,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = fetch_project(project_id, db)
    workspace_id = get_workspace_id(user)
    eisenprofielen = db.query(EisenProfiel).filter(
        (EisenProfiel.workspace_id == None) | (EisenProfiel.workspace_id == workspace_id)
    ).all()
    return templates.TemplateResponse(
        "rules/select.html",
        {"request": request, "project": project, "eisenprofielen": eisenprofielen, "user": user},
    )


@router.post("/projecten/{project_id}/eisen")
def eisen_opslaan(
    project_id: str,
    eisenprofiel_id: str = Form(...),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = fetch_project(project_id, db)
    if project.project_eisenprofiel:
        project.project_eisenprofiel.eisenprofiel_id = eisenprofiel_id
        project.project_eisenprofiel.override_eisen = None
    else:
        pep = ProjectEisenProfiel(project_id=project_id, eisenprofiel_id=eisenprofiel_id)
        db.add(pep)
    db.commit()
    return RedirectResponse(f"/api/v1/projecten/{project_id}", status_code=303)


# ── Review ────────────────────────────────────────────────────────────────────

@router.get("/projecten/{project_id}/review", response_class=HTMLResponse)
def review(
    request: Request,
    project_id: str,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = fetch_project(project_id, db)
    punten_wgs84 = []
    for p in project.trace_punten:
        lat, lon = rd_to_wgs84(p.RD_x, p.RD_y)
        punten_wgs84.append({"label": p.label, "lat": lat, "lon": lon})
    return templates.TemplateResponse(
        "project/review.html",
        {"request": request, "project": project, "punten_wgs84": punten_wgs84, "user": user},
    )


# ── Output pagina ─────────────────────────────────────────────────────────────

@router.get("/projecten/{project_id}/output", response_class=HTMLResponse)
def output_pagina(
    request: Request,
    project_id: str,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = fetch_project(project_id, db)
    return templates.TemplateResponse(
        "project/output.html", {"request": request, "project": project, "user": user}
    )
