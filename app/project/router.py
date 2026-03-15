import os
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.models import Workspace
from app.geo.coords import rd_to_wgs84
from app.project.models import (
    Berekening,
    Doorsnede,
    KLICUpload,
    MaaiveldOverride,
    Project,
    TracePunt,
)
from app.rules.models import EisenProfiel, ProjectEisenProfiel

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

WORKSPACE_ID = "gbt-workspace-001"


def _f(v: str) -> float | None:
    """Converteer leeg Form string-veld naar None (optionele float)."""
    return float(v) if v and v.strip() else None


def _i(v: str) -> int | None:
    """Converteer leeg Form string-veld naar None (optionele int)."""
    return int(v) if v and v.strip() else None


def _get_project(project_id: str, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project niet gevonden")
    return project


# ── Projectenlijst ──────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def projecten_lijst(
    request: Request,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    projecten = (
        db.query(Project)
        .filter_by(workspace_id=WORKSPACE_ID)
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

    project = Project(
        workspace_id=WORKSPACE_ID,
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
    return RedirectResponse(f"/projecten/{project.id}", status_code=303)


# ── Project detail ───────────────────────────────────────────────────────────

@router.get("/projecten/{project_id}", response_class=HTMLResponse)
def project_detail(
    request: Request,
    project_id: str,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project(project_id, db)
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
    project = _get_project(project_id, db)
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
    return RedirectResponse(f"/projecten/{project_id}", status_code=303)


# ── Tracé ────────────────────────────────────────────────────────────────────

@router.get("/projecten/{project_id}/trace", response_class=HTMLResponse)
def trace_form(
    request: Request,
    project_id: str,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project(project_id, db)
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
    # Komma-gescheiden lijsten van velden
    RD_x_list: str = Form(...),
    RD_y_list: str = Form(...),
    type_list: str = Form(...),
    label_list: str = Form(...),
    Rh_list: str = Form(""),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project(project_id, db)

    # Verwijder bestaande punten
    for punt in project.trace_punten:
        db.delete(punt)
    db.flush()

    xs = [float(v.strip()) for v in RD_x_list.split(",") if v.strip()]
    ys = [float(v.strip()) for v in RD_y_list.split(",") if v.strip()]
    types = [v.strip() for v in type_list.split(",") if v.strip()]
    labels = [v.strip() for v in label_list.split(",") if v.strip()]
    rhs = [v.strip() for v in Rh_list.split(",")] if Rh_list else [""] * len(xs)

    for i, (x, y, t, label) in enumerate(zip(xs, ys, types, labels)):
        rh_val = rhs[i] if i < len(rhs) else ""
        punt = TracePunt(
            project_id=project_id,
            volgorde=i,
            type=t,
            RD_x=x,
            RD_y=y,
            label=label,
            Rh_m=float(rh_val) if rh_val else None,
        )
        db.add(punt)

    db.commit()
    return RedirectResponse(f"/projecten/{project_id}", status_code=303)


# ── Brondata ─────────────────────────────────────────────────────────────────

@router.get("/projecten/{project_id}/brondata", response_class=HTMLResponse)
def brondata_form(
    request: Request,
    project_id: str,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project(project_id, db)
    return templates.TemplateResponse(
        "project/brondata.html", {"request": request, "project": project, "user": user}
    )


@router.post("/projecten/{project_id}/maaiveld")
def maaiveld_opslaan(
    project_id: str,
    MVin_NAP_m: float = Form(...),
    MVuit_NAP_m: float = Form(...),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project(project_id, db)
    if project.maaiveld_override:
        project.maaiveld_override.MVin_NAP_m = MVin_NAP_m
        project.maaiveld_override.MVuit_NAP_m = MVuit_NAP_m
        project.maaiveld_override.bron = "handmatig"
    else:
        mv = MaaiveldOverride(
            project_id=project_id,
            MVin_NAP_m=MVin_NAP_m,
            MVuit_NAP_m=MVuit_NAP_m,
            bron="handmatig",
        )
        db.add(mv)
    db.commit()
    return RedirectResponse(f"/projecten/{project_id}/brondata", status_code=303)


@router.post("/projecten/{project_id}/klic")
async def klic_upload(
    project_id: str,
    klic_zip: UploadFile = File(...),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project(project_id, db)
    dest_dir = UPLOAD_DIR / project_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / klic_zip.filename

    with open(dest_path, "wb") as f:
        shutil.copyfileobj(klic_zip.file, f)

    upload = KLICUpload(
        project_id=project_id,
        bestandsnaam=klic_zip.filename,
        bestandspad=str(dest_path),
        verwerkt=False,
    )
    db.add(upload)
    db.commit()
    return RedirectResponse(f"/projecten/{project_id}/brondata", status_code=303)


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
    project = _get_project(project_id, db)
    for d in project.doorsneden:
        db.delete(d)
    db.flush()

    afstanden = [float(v.strip()) for v in afstand_list.split(",") if v.strip()]
    naps = [float(v.strip()) for v in NAP_list.split(",") if v.strip()]
    grondtypen = [v.strip() for v in grondtype_list.split(",") if v.strip()]
    gwssen = [v.strip() for v in GWS_list.split(",")] if GWS_list else [""] * len(afstanden)

    for i, (afstand, nap, grondtype) in enumerate(zip(afstanden, naps, grondtypen)):
        gws_val = gwssen[i] if i < len(gwssen) else ""
        ds = Doorsnede(
            project_id=project_id,
            volgorde=i,
            afstand_m=afstand,
            NAP_m=nap,
            grondtype=grondtype,
            GWS_m=float(gws_val) if gws_val else None,
        )
        db.add(ds)
    db.commit()
    return RedirectResponse(f"/projecten/{project_id}/brondata", status_code=303)


@router.post("/projecten/{project_id}/intrekkracht")
def intrekkracht_opslaan(
    project_id: str,
    Ttot_N: float = Form(...),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project(project_id, db)
    if project.berekening:
        project.berekening.Ttot_N = Ttot_N
        project.berekening.bron = "sigma_override"
    else:
        b = Berekening(project_id=project_id, Ttot_N=Ttot_N, bron="sigma_override")
        db.add(b)
    db.commit()
    return RedirectResponse(f"/projecten/{project_id}/brondata", status_code=303)


# ── Eisenprofiel ──────────────────────────────────────────────────────────────

@router.get("/projecten/{project_id}/eisen", response_class=HTMLResponse)
def eisen_form(
    request: Request,
    project_id: str,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project(project_id, db)
    eisenprofielen = db.query(EisenProfiel).filter(
        (EisenProfiel.workspace_id == None) | (EisenProfiel.workspace_id == WORKSPACE_ID)
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
    project = _get_project(project_id, db)
    if project.project_eisenprofiel:
        project.project_eisenprofiel.eisenprofiel_id = eisenprofiel_id
        project.project_eisenprofiel.override_eisen = None
    else:
        pep = ProjectEisenProfiel(project_id=project_id, eisenprofiel_id=eisenprofiel_id)
        db.add(pep)
    db.commit()
    return RedirectResponse(f"/projecten/{project_id}", status_code=303)


# ── Review ────────────────────────────────────────────────────────────────────

@router.get("/projecten/{project_id}/review", response_class=HTMLResponse)
def review(
    request: Request,
    project_id: str,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project(project_id, db)
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
    project = _get_project(project_id, db)
    return templates.TemplateResponse(
        "project/output.html", {"request": request, "project": project, "user": user}
    )
