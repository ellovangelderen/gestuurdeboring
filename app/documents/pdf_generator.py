"""PDF generator — WeasyPrint + Jinja2."""
import math
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from app.project.models import Project


_template_dir = Path(__file__).parent.parent / "templates" / "documents"
_env = Environment(loader=FileSystemLoader(str(_template_dir)))


def _hoek_pct(graden: float) -> float:
    return round(math.tan(math.radians(graden)) * 100, 1)


def generate_pdf(project: Project) -> bytes:
    """Genereer PDF als bytes voor een project."""
    from datetime import date

    punten = []
    for p in project.trace_punten:
        punten.append({"label": p.label, "RD_x": f"{p.RD_x:.1f}", "RD_y": f"{p.RD_y:.1f}"})

    doorsneden = []
    for d in project.doorsneden:
        doorsneden.append({
            "afstand_m": d.afstand_m,
            "NAP_m": d.NAP_m,
            "grondtype": d.grondtype,
        })

    context = {
        "project": project,
        "datum": date.today().strftime("%d-%m-%Y"),
        "punten": punten,
        "doorsneden": doorsneden,
        "r_boorgat_mm": project.Dg_mm / 2,
        "r_buis_mm": project.De_mm / 2,
        "intreehoek_pct": _hoek_pct(project.intreehoek_gr),
        "uittreehoek_pct": _hoek_pct(project.uittreehoek_gr),
    }

    template = _env.get_template("tekening.html")
    html_str = template.render(**context)
    pdf_bytes = HTML(string=html_str, base_url=str(_template_dir)).write_pdf()
    return pdf_bytes
