from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.dependencies import fetch_project, fetch_order, fetch_boring
from app.documents.dxf_generator import generate_dxf
from app.documents.pdf_generator import generate_pdf
from app.documents.werkplan_generator import generate_werkplan

router = APIRouter(prefix="/api/v1")
templates = Jinja2Templates(directory="app/templates")


@router.get("/projecten/{project_id}/dxf")
def download_dxf_legacy(
    project_id: str,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Legacy route — redirect naar nieuwe route als mogelijk."""
    project = fetch_project(project_id, db)
    dxf_bytes = generate_dxf(project, project, db)
    ordernr = project.ordernummer or project.id[:8]
    filename = f"{ordernr}-rev.1.dxf"
    return Response(
        content=dxf_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/projecten/{project_id}/pdf")
def download_pdf_legacy(
    project_id: str,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Legacy route."""
    project = fetch_project(project_id, db)
    pdf_bytes = generate_pdf(project, project)
    ordernr = project.ordernummer or project.id[:8]
    filename = f"{ordernr}-rev.1.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Werkplan (Word) ────────────────────────────────────────────────────────

@router.get("/orders/{order_id}/boringen/{volgnr}/werkplan", response_class=HTMLResponse)
def werkplan_form(
    request: Request,
    order_id: str,
    volgnr: int,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Formulier om werkplan-opties in te vullen voor generatie."""
    order = fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)
    return templates.TemplateResponse(
        "documents/werkplan_form.html",
        {
            "request": request,
            "order": order,
            "boring": boring,
            "user": user,
        },
    )


@router.post("/orders/{order_id}/boringen/{volgnr}/werkplan")
def werkplan_download(
    order_id: str,
    volgnr: int,
    auteur: str = Form("Martien Luijben"),
    hoofdaannemer: str = Form(""),
    opdrachtgever_naam: str = Form(""),
    inleiding_tekst: str = Form(""),
    kwel_gebied: str = Form(""),
    gebruik_ai: str = Form(""),
    revisie: str = Form("0"),
    revisie_omschrijving: str = Form("Vergunningsaanvraag"),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Genereer en download het werkplan als Word-bestand."""
    order = fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)

    docx_bytes = generate_werkplan(
        order=order,
        boring=boring,
        auteur=auteur.strip(),
        hoofdaannemer=hoofdaannemer.strip(),
        opdrachtgever_naam=opdrachtgever_naam.strip(),
        inleiding_tekst=inleiding_tekst.strip(),
        kwel_gebied=kwel_gebied == "on",
        revisie=int(revisie) if revisie.strip() else 0,
        revisie_omschrijving=revisie_omschrijving.strip(),
        gebruik_ai=gebruik_ai == "on",
    )

    locatie = order.locatie or "locatie"
    boring_naam = boring.naam or f"HDD{boring.volgnummer}"
    filename = f"{order.ordernummer} {boring_naam} Werkplan - {locatie}.docx"

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
