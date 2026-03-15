from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.documents.dxf_generator import generate_dxf
from app.documents.pdf_generator import generate_pdf
from app.project.models import Project

router = APIRouter()


def _get_project(project_id: str, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project niet gevonden")
    return project


@router.get("/projecten/{project_id}/dxf")
def download_dxf(
    project_id: str,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project(project_id, db)
    dxf_bytes = generate_dxf(project)
    ordernr = project.ordernummer or project.id[:8]
    filename = f"{ordernr}-rev.1.dxf"
    return Response(
        content=dxf_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/projecten/{project_id}/pdf")
def download_pdf(
    project_id: str,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project(project_id, db)
    pdf_bytes = generate_pdf(project)
    ordernr = project.ordernummer or project.id[:8]
    filename = f"{ordernr}-rev.1.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
