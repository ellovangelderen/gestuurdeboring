from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user  # noqa: F401 — re-exported for routers
from app.core.database import get_db  # noqa: F401 — re-exported for routers

_USER_WORKSPACE: dict[str, str] = {
    "martien": "gbt-workspace-001",
    "visser":  "gbt-workspace-001",
    "sopa":    "gbt-workspace-001",
    "lucas":   "gbt-workspace-001",
    "test":    "gbt-workspace-001",
}


def get_workspace_id(user: str) -> str:
    """Vertaalt ingelogde gebruiker naar workspace_id."""
    return _USER_WORKSPACE.get(user, "gbt-workspace-001")


def fetch_project(project_id: str, db: Session):
    """Haalt project op of geeft 404. Gedeeld door alle routers."""
    from app.project.models import Project
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project niet gevonden")
    return project


def fetch_order(order_id: str, db: Session):
    """Haalt order op of geeft 404."""
    from app.order.models import Order
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order niet gevonden")
    return order


def fetch_boring(order_id: str, volgnummer: int, db: Session):
    """Haalt boring op via order_id + volgnummer, of geeft 404."""
    from app.order.models import Boring
    boring = db.query(Boring).filter_by(order_id=order_id, volgnummer=volgnummer).first()
    if not boring:
        raise HTTPException(status_code=404, detail="Boring niet gevonden")
    return boring
