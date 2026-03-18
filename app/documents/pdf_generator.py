"""PDF generator — WeasyPrint + Jinja2."""
import math
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session
from weasyprint import HTML

from app.order.models import Boring, Order


_template_dir = Path(__file__).parent.parent / "templates" / "documents"
_env = Environment(loader=FileSystemLoader(str(_template_dir)))


def _hoek_pct(graden: float) -> float:
    return round(math.tan(math.radians(graden)) * 100, 1)


def generate_pdf(boring: Boring, order: Order, db: Optional[Session] = None) -> bytes:
    """Genereer PDF als bytes voor een boring."""
    from datetime import date

    punten = []
    for p in boring.trace_punten:
        punten.append({"label": p.label, "RD_x": f"{p.RD_x:.1f}", "RD_y": f"{p.RD_y:.1f}"})

    doorsneden = []
    for d in boring.doorsneden:
        doorsneden.append({
            "afstand_m": d.afstand_m,
            "NAP_m": d.NAP_m,
            "grondtype": d.grondtype,
        })

    # EV-zones ophalen als db beschikbaar
    ev_zones = []
    if db is not None:
        from app.order.models import EVZone
        ev_zones = db.query(EVZone).filter_by(order_id=order.id).all()

    context = {
        "boring": boring,
        "order": order,
        "datum": date.today().strftime("%d-%m-%Y"),
        "punten": punten,
        "doorsneden": doorsneden,
        "r_boorgat_mm": boring.Dg_mm / 2,
        "r_buis_mm": boring.De_mm / 2,
        "intreehoek_pct": _hoek_pct(boring.intreehoek_gr),
        "uittreehoek_pct": _hoek_pct(boring.uittreehoek_gr),
        "ev_zones": ev_zones,
        "has_ev_zones": len(ev_zones) > 0,
    }

    template = _env.get_template("tekening.html")
    html_str = template.render(**context)
    pdf_bytes = HTML(string=html_str, base_url=str(_template_dir)).write_pdf()
    return pdf_bytes
