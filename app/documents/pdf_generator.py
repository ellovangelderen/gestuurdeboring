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


def _generate_lengteprofiel_svg(boring: Boring) -> str:
    """Genereer SVG string voor het lengteprofiel van een boring.

    Returns lege string als data ontbreekt (geen trace, geen maaiveld).
    """
    from app.geo.profiel import bereken_boorprofiel, trace_totale_afstand, arc_punten

    punten = boring.trace_punten
    if len(punten) < 2:
        return ""
    mv = boring.maaiveld_override
    if mv is None or mv.MVin_NAP_m is None or mv.MVuit_NAP_m is None:
        return ""

    coords = [(p.RD_x, p.RD_y) for p in punten]
    L_totaal = trace_totale_afstand(coords)
    if L_totaal < 1.0:
        return ""

    try:
        profiel = bereken_boorprofiel(
            L_totaal_m=L_totaal,
            MVin_NAP_m=mv.MVin_NAP_m,
            MVuit_NAP_m=mv.MVuit_NAP_m,
            alpha_in_gr=boring.intreehoek_gr or 18.0,
            alpha_uit_gr=boring.uittreehoek_gr or 22.0,
            De_mm=boring.De_mm or 160.0,
        )
    except Exception:
        return ""

    # SVG viewBox
    margin = 20
    z_min = profiel.diepte_NAP_m - 5
    z_max = max(mv.MVin_NAP_m, mv.MVuit_NAP_m) + 5
    svg_width = 600
    svg_height = 300

    # Scale factors
    x_range = L_totaal if L_totaal > 0 else 1.0
    z_range = z_max - z_min if (z_max - z_min) > 0 else 1.0
    sx = (svg_width - 2 * margin) / x_range
    sz = (svg_height - 2 * margin) / z_range

    def tx(x: float) -> float:
        return margin + x * sx

    def tz(z: float) -> float:
        # SVG y-as is omgekeerd (naar beneden)
        return margin + (z_max - z) * sz

    paths = []

    # Maaiveldlijn (bruin/groen)
    paths.append(
        f'<line x1="{tx(0):.1f}" y1="{tz(mv.MVin_NAP_m):.1f}" '
        f'x2="{tx(L_totaal):.1f}" y2="{tz(mv.MVuit_NAP_m):.1f}" '
        f'stroke="#5a8a3c" stroke-width="2" stroke-dasharray="6,3"/>'
    )

    # Boorlijn segmenten
    boorlijn_parts = []
    for seg in profiel.segmenten:
        if seg["type"] == "lijn":
            if seg.get("lengte", 0) < 0.001:
                continue
            boorlijn_parts.append(
                f'<line x1="{tx(seg["x_start"]):.1f}" y1="{tz(seg["z_start"]):.1f}" '
                f'x2="{tx(seg["x_end"]):.1f}" y2="{tz(seg["z_end"]):.1f}" '
                f'stroke="#cc0000" stroke-width="1.5"/>'
            )
        elif seg["type"] == "arc":
            # Discretiseer boog naar SVG polyline
            pts = arc_punten(
                seg["cx"], seg["cz"], seg["radius"],
                seg["start_hoek_rad"], seg["eind_hoek_rad"], n=40,
            )
            svg_pts = " ".join(f"{tx(x):.1f},{tz(z):.1f}" for x, z in pts)
            boorlijn_parts.append(
                f'<polyline points="{svg_pts}" fill="none" stroke="#cc0000" stroke-width="1.5"/>'
            )

    paths.extend(boorlijn_parts)

    # Labels
    labels = []
    labels.append(
        f'<text x="{tx(0) - 2:.1f}" y="{tz(mv.MVin_NAP_m) - 4:.1f}" '
        f'font-size="7" text-anchor="end" fill="#333">MV {mv.MVin_NAP_m:+.2f}</text>'
    )
    labels.append(
        f'<text x="{tx(L_totaal) + 2:.1f}" y="{tz(mv.MVuit_NAP_m) - 4:.1f}" '
        f'font-size="7" text-anchor="start" fill="#333">MV {mv.MVuit_NAP_m:+.2f}</text>'
    )
    labels.append(
        f'<text x="{tx(L_totaal / 2):.1f}" y="{tz(profiel.diepte_NAP_m) + 14:.1f}" '
        f'font-size="7" text-anchor="middle" fill="#333">'
        f'Diepte {profiel.diepte_NAP_m:+.2f} NAP | Rv={profiel.Rv_m:.0f}m</text>'
    )
    labels.append(
        f'<text x="{tx(L_totaal / 2):.1f}" y="{tz(z_max) + 12:.1f}" '
        f'font-size="8" text-anchor="middle" fill="#000" font-weight="bold">'
        f'L = {L_totaal:.1f} m</text>'
    )

    # NAP schaal (links)
    # Teken een paar referentielijnen
    nap_lines = []
    import math as _m
    step = max(1, int(_m.ceil(z_range / 5)))
    z_start_nap = int(_m.floor(z_min))
    z_end_nap = int(_m.ceil(z_max))
    for nap in range(z_start_nap, z_end_nap + 1, step):
        y_pos = tz(nap)
        nap_lines.append(
            f'<line x1="{margin - 5:.1f}" y1="{y_pos:.1f}" '
            f'x2="{svg_width - margin:.1f}" y2="{y_pos:.1f}" '
            f'stroke="#ddd" stroke-width="0.5"/>'
        )
        nap_lines.append(
            f'<text x="{margin - 7:.1f}" y="{y_pos + 3:.1f}" '
            f'font-size="6" text-anchor="end" fill="#999">{nap:+d}</text>'
        )

    svg = (
        f'<svg width="{svg_width}" height="{svg_height}" '
        f'viewBox="0 0 {svg_width} {svg_height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="background:#fafafa; border:0.5pt solid #ccc;">\n'
    )
    svg += "\n".join(nap_lines) + "\n"
    svg += "\n".join(paths) + "\n"
    svg += "\n".join(labels) + "\n"
    svg += "</svg>"
    return svg


def _generate_bovenaanzicht_svg(boring: Boring) -> str:
    """Genereer simpele SVG van trace bovenaanzicht."""
    punten = boring.trace_punten
    if len(punten) < 2:
        return ""

    xs = [p.RD_x for p in punten]
    ys = [p.RD_y for p in punten]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    # Voeg marge toe
    dx = max(x_max - x_min, 1.0)
    dy = max(y_max - y_min, 1.0)
    margin = max(dx, dy) * 0.1

    svg_w, svg_h = 300, 200
    sx = (svg_w - 40) / (dx + 2 * margin)
    sy = (svg_h - 40) / (dy + 2 * margin)
    s = min(sx, sy)

    def tx(x: float) -> float:
        return 20 + (x - x_min + margin) * s

    def ty(y: float) -> float:
        # RD y naar boven, SVG y naar beneden
        return svg_h - 20 - (y - y_min + margin) * s

    pts_str = " ".join(f"{tx(p.RD_x):.1f},{ty(p.RD_y):.1f}" for p in punten)

    svg = (
        f'<svg width="{svg_w}" height="{svg_h}" '
        f'viewBox="0 0 {svg_w} {svg_h}" '
        f'xmlns="http://www.w3.org/2000/svg" style="background:#fafafa; border:0.5pt solid #ccc;">\n'
        f'<polyline points="{pts_str}" fill="none" stroke="#cc0000" stroke-width="2"/>\n'
    )
    # Labels bij intree en uittree
    for p in punten:
        if p.type in ("intree", "uittree") and p.label:
            svg += (
                f'<circle cx="{tx(p.RD_x):.1f}" cy="{ty(p.RD_y):.1f}" r="3" fill="#cc0000"/>\n'
                f'<text x="{tx(p.RD_x) + 5:.1f}" y="{ty(p.RD_y) - 5:.1f}" '
                f'font-size="8" fill="#333">{p.label}</text>\n'
            )
    svg += "</svg>"
    return svg


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

    # Lengteprofiel en bovenaanzicht SVG
    lengteprofiel_svg = _generate_lengteprofiel_svg(boring)
    bovenaanzicht_svg = _generate_bovenaanzicht_svg(boring)

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
        "lengteprofiel_svg": lengteprofiel_svg,
        "bovenaanzicht_svg": bovenaanzicht_svg,
    }

    template = _env.get_template("tekening.html")
    html_str = template.render(**context)
    pdf_bytes = HTML(string=html_str, base_url=str(_template_dir)).write_pdf()
    return pdf_bytes
