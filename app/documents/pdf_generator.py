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
    from app.geo.profiel import bereken_boorprofiel, bereken_boorprofiel_z, trace_totale_afstand, arc_punten

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
        if boring.type == "Z" and boring.booghoek_gr:
            profiel = bereken_boorprofiel_z(
                L_totaal_m=L_totaal,
                MVin_NAP_m=mv.MVin_NAP_m,
                MVuit_NAP_m=mv.MVuit_NAP_m,
                booghoek_gr=boring.booghoek_gr,
                De_mm=boring.De_mm or 160.0,
            )
        else:
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
    # Diepte label met boog-specifieke info
    if boring.type == "Z" and boring.booghoek_gr:
        booglengte_str = ""
        for seg in profiel.segmenten:
            if seg["type"] == "arc" and "booglengte" in seg:
                booglengte_str = f" | Booglengte={seg['booglengte']:.1f}m"
                break
        labels.append(
            f'<text x="{tx(L_totaal / 2):.1f}" y="{tz(profiel.diepte_NAP_m) + 14:.1f}" '
            f'font-size="7" text-anchor="middle" fill="#333">'
            f'Diepte {profiel.diepte_NAP_m:+.2f} NAP | Booghoek={boring.booghoek_gr:.1f}{booglengte_str}</text>'
        )
    else:
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


def _fetch_map_image_b64(lat_min: float, lon_min: float, lat_max: float, lon_max: float,
                          width: int = 600, height: int = 400) -> str | None:
    """Haal een statische kaartafbeelding op als base64 PNG via OSM static map."""
    import base64
    import httpx
    import logging
    logger = logging.getLogger(__name__)

    # Gebruik OpenStreetMap static map via bbox
    # Bereken center en zoom
    lat_center = (lat_min + lat_max) / 2
    lon_center = (lon_min + lon_max) / 2

    # Bereken geschikt zoomniveau
    lat_span = lat_max - lat_min
    lon_span = lon_max - lon_min
    # Hoe kleiner de span, hoe hoger de zoom
    span = max(lat_span, lon_span)
    if span < 0.002:
        zoom = 17
    elif span < 0.005:
        zoom = 16
    elif span < 0.01:
        zoom = 15
    elif span < 0.02:
        zoom = 14
    elif span < 0.05:
        zoom = 13
    else:
        zoom = 12

    # Gebruik PDOK luchtfoto WMTS als statische kaart (Web Mercator)
    # Alternatief: OSM tile stitching. We gebruiken een eenvoudige aanpak:
    # Haal 1 WMS GetMap request op
    try:
        from app.geo.coords import rd_to_wgs84, wgs84_to_rd
        # Converteer bbox naar RD voor PDOK
        rd_min_x, rd_min_y = wgs84_to_rd(lat_min, lon_min)
        rd_max_x, rd_max_y = wgs84_to_rd(lat_max, lon_max)

        # PDOK luchtfoto WMS
        url = (
            f"https://service.pdok.nl/hwh/luchtfotorgb/wms/v1_0"
            f"?service=WMS&version=1.3.0&request=GetMap"
            f"&layers=Actueel_orthoHR"
            f"&crs=EPSG:28992"
            f"&bbox={rd_min_x},{rd_min_y},{rd_max_x},{rd_max_y}"
            f"&width={width}&height={height}"
            f"&format=image/png"
        )
        resp = httpx.get(url, timeout=10)
        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image"):
            return base64.b64encode(resp.content).decode("ascii")
    except Exception as exc:
        logger.warning("Kaart ophalen mislukt: %s", exc)

    return None


def _generate_bovenaanzicht_svg(boring: Boring) -> str:
    """Genereer SVG van trace bovenaanzicht met kaartachtergrond."""
    punten = boring.trace_punten
    if len(punten) < 2:
        return ""

    xs = [p.RD_x for p in punten]
    ys = [p.RD_y for p in punten]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    # Voeg ruime marge toe voor kaartcontext
    dx = max(x_max - x_min, 1.0)
    dy = max(y_max - y_min, 1.0)
    margin = max(dx, dy) * 0.3

    svg_w, svg_h = 500, 350
    view_x_min = x_min - margin
    view_x_max = x_max + margin
    view_y_min = y_min - margin
    view_y_max = y_max + margin
    view_dx = view_x_max - view_x_min
    view_dy = view_y_max - view_y_min

    sx = svg_w / view_dx
    sy = svg_h / view_dy
    s = min(sx, sy)

    # Centreer
    offset_x = (svg_w - view_dx * s) / 2
    offset_y = (svg_h - view_dy * s) / 2

    def tx(x: float) -> float:
        return offset_x + (x - view_x_min) * s

    def ty(y: float) -> float:
        return svg_h - offset_y - (y - view_y_min) * s

    svg = (
        f'<svg width="{svg_w}" height="{svg_h}" '
        f'viewBox="0 0 {svg_w} {svg_h}" '
        f'xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'style="border:0.5pt solid #ccc;">\n'
    )

    # Kaartachtergrond ophalen
    try:
        from app.geo.coords import rd_to_wgs84
        lat_min_wgs, lon_min_wgs = rd_to_wgs84(view_x_min, view_y_min)
        lat_max_wgs, lon_max_wgs = rd_to_wgs84(view_x_max, view_y_max)
        map_b64 = _fetch_map_image_b64(lat_min_wgs, lon_min_wgs, lat_max_wgs, lon_max_wgs,
                                        width=svg_w * 2, height=svg_h * 2)
        if map_b64:
            svg += (
                f'<image x="0" y="0" width="{svg_w}" height="{svg_h}" '
                f'href="data:image/png;base64,{map_b64}" '
                f'preserveAspectRatio="none"/>\n'
            )
        else:
            svg += f'<rect x="0" y="0" width="{svg_w}" height="{svg_h}" fill="#f0f0f0"/>\n'
    except Exception:
        svg += f'<rect x="0" y="0" width="{svg_w}" height="{svg_h}" fill="#f0f0f0"/>\n'

    # Tracé lijn
    pts_str = " ".join(f"{tx(p.RD_x):.1f},{ty(p.RD_y):.1f}" for p in punten)
    svg += f'<polyline points="{pts_str}" fill="none" stroke="#cc0000" stroke-width="3"/>\n'

    # Labels + punten
    for p in punten:
        px, py = tx(p.RD_x), ty(p.RD_y)
        svg += f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="#cc0000" stroke="#fff" stroke-width="1.5"/>\n'
        if p.label:
            svg += (
                f'<text x="{px + 7:.1f}" y="{py - 5:.1f}" '
                f'font-size="10" font-weight="bold" fill="#fff" stroke="#333" stroke-width="0.3">{p.label}</text>\n'
            )

    # Noordpijl
    svg += (
        f'<text x="{svg_w - 15}" y="20" font-size="14" font-weight="bold" fill="#333" text-anchor="middle">N</text>\n'
        f'<line x1="{svg_w - 15}" y1="22" x2="{svg_w - 15}" y2="38" stroke="#333" stroke-width="1.5" marker-start="url(#arrow)"/>\n'
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
        "intreehoek_pct": _hoek_pct(boring.intreehoek_gr) if boring.type != "Z" else 0,
        "uittreehoek_pct": _hoek_pct(boring.uittreehoek_gr) if boring.type != "Z" else 0,
        "ev_zones": ev_zones,
        "has_ev_zones": len(ev_zones) > 0,
        "lengteprofiel_svg": lengteprofiel_svg,
        "bovenaanzicht_svg": bovenaanzicht_svg,
        "is_boogzinker": boring.type == "Z",
    }

    template = _env.get_template("tekening.html")
    html_str = template.render(**context)
    pdf_bytes = HTML(string=html_str, base_url=str(_template_dir)).write_pdf()
    return pdf_bytes
