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


def _generate_doorsnede_svg(boring) -> str:
    """Genereer SVG van doorsnede boorgat (2 concentrische cirkels + labels)."""
    Dg = boring.Dg_mm or 240
    De = boring.De_mm or 160
    svg_size = 200
    cx, cy = 100, 85
    r_max = 70  # buitenste cirkel (ruimer)
    r_buis = int(r_max * De / Dg)

    svg = (
        f'<svg width="{svg_size}" height="{svg_size}" viewBox="0 0 {svg_size} {svg_size}" '
        f'xmlns="http://www.w3.org/2000/svg">\n'
        # Ruimer cirkel (buitenste, gestreept)
        f'<circle cx="{cx}" cy="{cy}" r="{r_max}" fill="none" stroke="#444" stroke-width="2" stroke-dasharray="5,3"/>\n'
        # Buis cirkel (binnenste, gevuld)
        f'<circle cx="{cx}" cy="{cy}" r="{r_buis}" fill="#e8f4ff" stroke="#0055aa" stroke-width="2"/>\n'
        # Maatlijnen
        f'<line x1="{cx}" y1="{cy - r_max - 8}" x2="{cx}" y2="{cy - r_max + 3}" stroke="#333" stroke-width="1"/>\n'
        f'<line x1="{cx}" y1="{cy + r_max - 3}" x2="{cx}" y2="{cy + r_max + 8}" stroke="#333" stroke-width="1"/>\n'
        # Labels
        f'<text x="{cx}" y="{cy + r_max + 18}" text-anchor="middle" font-size="9" fill="#333">Dg={Dg}mm</text>\n'
        f'<text x="{cx}" y="{cy + r_max + 28}" text-anchor="middle" font-size="9" fill="#333">De={De}mm</text>\n'
        # Titel labels
        f'<text x="{cx}" y="{svg_size - 2}" text-anchor="middle" font-size="8" fill="#333">'
        f'Pilotboring Ø{De}mm</text>\n'
        f'<text x="{cx}" y="12" text-anchor="middle" font-size="8" fill="#333">'
        f'Ruimer Ø{Dg}mm · {boring.materiaal} SDR{boring.SDR}</text>\n'
        f'</svg>'
    )
    return svg


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
    margin_left = 45   # ruimte voor NAP labels
    margin_right = 15
    margin_top = 30
    margin_bot = 35    # ruimte voor afstandslabels
    svg_width = 1200
    svg_height = 500

    # z-bereik: van diepste punt tot net boven maaiveld (NIET boog-toppen)
    # Bogen worden geclipt op maaiveld — zoals in Martien's referentie
    mv_max = max(mv.MVin_NAP_m, mv.MVuit_NAP_m)
    z_max = mv_max + 2.0
    z_min = profiel.diepte_NAP_m - 1.5
    if boring.doorsneden:
        z_min = min(z_min, min(d.NAP_m for d in boring.doorsneden) - 0.5)
    x_range = L_totaal if L_totaal > 0 else 1.0
    z_range = z_max - z_min if (z_max - z_min) > 0 else 1.0

    # Horizontale schaal: x in pixels
    sx = (svg_width - margin_left - margin_right) / x_range

    # Verticale schaal: OVERDREVEN zodat bogen zichtbaar zijn
    # Martien gebruikt ~10-15x verticale overdrijving
    sz = sx * 15  # 15x overdrijving t.o.v. horizontaal

    # Pas SVG hoogte aan op basis van werkelijke benodigde ruimte
    svg_height = int(margin_top + margin_bot + z_range * sz)
    svg_height = max(svg_height, 300)  # minimaal 300px
    svg_height = min(svg_height, 800)  # maximaal 800px

    # Als het niet past, schaal terug
    if z_range * sz > (svg_height - margin_top - margin_bot):
        sz = (svg_height - margin_top - margin_bot) / z_range

    def tx(x: float) -> float:
        return margin_left + x * sx

    def tz(z: float) -> float:
        return margin_top + (z_max - z) * sz

    svg_parts = []

    # ── NAP grid (per 1m) ──
    import math as _m
    z_start_nap = int(_m.floor(z_min))
    z_end_nap = int(_m.ceil(z_max))
    for nap in range(z_start_nap, z_end_nap + 1):
        y_pos = tz(nap)
        is_zero = nap == 0
        svg_parts.append(
            f'<line x1="{margin_left:.0f}" y1="{y_pos:.1f}" '
            f'x2="{svg_width - margin_right:.0f}" y2="{y_pos:.1f}" '
            f'stroke="{"#999" if is_zero else "#e0e0e0"}" stroke-width="{"1" if is_zero else "0.5"}"/>'
        )
        svg_parts.append(
            f'<text x="{margin_left - 4:.0f}" y="{y_pos + 4:.1f}" '
            f'font-size="10" text-anchor="end" fill="#666" font-weight="{"bold" if is_zero else "normal"}">{nap:+d}</text>'
        )
    # NAP label
    svg_parts.append(
        f'<text x="8" y="{margin_top + 10}" font-size="9" fill="#999" '
        f'transform="rotate(-90, 8, {margin_top + 10})">m NAP</text>'
    )

    # ── Maaiveldlijn (groen, gestreept) ──
    svg_parts.append(
        f'<line x1="{tx(0):.1f}" y1="{tz(mv.MVin_NAP_m):.1f}" '
        f'x2="{tx(L_totaal):.1f}" y2="{tz(mv.MVuit_NAP_m):.1f}" '
        f'stroke="#5a8a3c" stroke-width="2.5" stroke-dasharray="8,4"/>'
    )

    # ── Boorlijn (rood, dik) ──
    # Visuele benadering: vloeiende curve van maaiveld naar diepte
    # Bij grote Rv steken de geometrische bogen boven maaiveld uit.
    # We tekenen de boorlijn als: maaiveld → schuine lijn → boog → horizontaal → boog → schuine lijn → maaiveld
    # met de bogen begrensd op maaiveld.
    import math as _math

    diepte = profiel.diepte_NAP_m
    alpha_in = _math.radians(boring.intreehoek_gr or 18.0)
    alpha_uit = _math.radians(boring.uittreehoek_gr or 22.0)

    # Horizontale afstand van de schuine lijnen (van maaiveld tot diepte)
    dz_in = mv.MVin_NAP_m - diepte
    dz_uit = mv.MVuit_NAP_m - diepte
    x_intree_end = dz_in / _math.tan(alpha_in) if alpha_in > 0.01 else 20.0
    x_uittree_start = L_totaal - (dz_uit / _math.tan(alpha_uit) if alpha_uit > 0.01 else 20.0)

    # Beperk zodat er een horizontaal segment overblijft
    x_intree_end = min(x_intree_end, L_totaal * 0.4)
    x_uittree_start = max(x_uittree_start, L_totaal * 0.6)

    # Bouw punten: maaiveld → curve intree → horizontaal → curve uittree → maaiveld
    n_curve = 30
    boorlijn_punten = []

    # Intree: van (0, MV_in) naar (x_intree_end, diepte) als vloeiende curve
    for i in range(n_curve + 1):
        t = i / n_curve
        x = x_intree_end * t
        # Sinusoïdale interpolatie voor vloeiende S-curve
        s = (1 - _math.cos(t * _math.pi)) / 2  # 0→1 smooth
        z = mv.MVin_NAP_m + s * (diepte - mv.MVin_NAP_m)
        boorlijn_punten.append((x, z))

    # Horizontaal segment
    boorlijn_punten.append((x_uittree_start, diepte))

    # Uittree: van (x_uittree_start, diepte) naar (L_totaal, MV_uit) als vloeiende curve
    for i in range(n_curve + 1):
        t = i / n_curve
        x = x_uittree_start + (L_totaal - x_uittree_start) * t
        s = (1 - _math.cos(t * _math.pi)) / 2
        z = diepte + s * (mv.MVuit_NAP_m - diepte)
        boorlijn_punten.append((x, z))

    svg_pts = " ".join(f"{tx(x):.1f},{tz(z):.1f}" for x, z in boorlijn_punten)
    svg_parts.append(
        f'<polyline points="{svg_pts}" fill="none" stroke="#cc0000" stroke-width="3.5"/>'
    )

    # ── Sensorpunt labels langs de boorlijn ──
    # Bereken positie per sensorpunt op het profiel (projectie op x-as)
    from app.geo.profiel import trace_totale_afstand as _tta
    trace_coords = [(p.RD_x, p.RD_y) for p in punten]
    cumul_dist = [0.0]
    for i in range(1, len(trace_coords)):
        d = _m.sqrt((trace_coords[i][0] - trace_coords[i-1][0])**2 +
                     (trace_coords[i][1] - trace_coords[i-1][1])**2)
        cumul_dist.append(cumul_dist[-1] + d)

    for i, p in enumerate(punten):
        x_pos = cumul_dist[i] if i < len(cumul_dist) else 0
        # Bereken z op de boorlijn via lineaire interpolatie van maaiveld
        # (sensorpunten zitten op maaiveld, niet op de boorlijn)
        t = x_pos / L_totaal if L_totaal > 0 else 0
        z_mv = mv.MVin_NAP_m + t * (mv.MVuit_NAP_m - mv.MVin_NAP_m)

        px = tx(x_pos)
        py_mv = tz(z_mv)

        # Verticale lijn van maaiveld naar beneden (sensorpunt marker)
        svg_parts.append(
            f'<line x1="{px:.1f}" y1="{py_mv:.1f}" x2="{px:.1f}" y2="{py_mv + 8:.1f}" '
            f'stroke="#333" stroke-width="1"/>'
        )
        # Label boven maaiveld
        if p.label:
            svg_parts.append(
                f'<text x="{px:.1f}" y="{py_mv - 6:.1f}" '
                f'font-size="10" text-anchor="middle" fill="#cc0000" font-weight="bold">{p.label}</text>'
            )

    # ── Afstandslabels onder het profiel ──
    afstand_y = svg_height - 8
    for i, p in enumerate(punten):
        x_pos = cumul_dist[i] if i < len(cumul_dist) else 0
        px = tx(x_pos)
        if p.label:
            svg_parts.append(
                f'<text x="{px:.1f}" y="{afstand_y:.1f}" '
                f'font-size="8" text-anchor="middle" fill="#666">{x_pos:.0f}m</text>'
            )

    # ── Doorsnede-nummers ──
    for d in boring.doorsneden:
        dx = tx(d.afstand_m)
        dz = tz(d.NAP_m)
        # Cirkel met nummer
        svg_parts.append(
            f'<circle cx="{dx:.1f}" cy="{dz:.1f}" r="8" fill="#fff" stroke="#333" stroke-width="1"/>'
        )
        svg_parts.append(
            f'<text x="{dx:.1f}" y="{dz + 3.5:.1f}" font-size="9" text-anchor="middle" '
            f'fill="#333" font-weight="bold">{d.volgorde + 1}</text>'
        )

    # ── MV labels links en rechts ──
    svg_parts.append(
        f'<text x="{tx(0) - 2:.0f}" y="{tz(mv.MVin_NAP_m) + 4:.1f}" '
        f'font-size="11" text-anchor="end" fill="#5a8a3c" font-weight="bold">MV {mv.MVin_NAP_m:+.2f}</text>'
    )
    svg_parts.append(
        f'<text x="{tx(L_totaal) + 2:.0f}" y="{tz(mv.MVuit_NAP_m) + 4:.1f}" '
        f'font-size="11" text-anchor="start" fill="#5a8a3c" font-weight="bold">MV {mv.MVuit_NAP_m:+.2f}</text>'
    )

    # ── Hoeklabels bij intree en uittree ──
    if not (boring.type == "Z" and boring.booghoek_gr):
        svg_parts.append(
            f'<text x="{tx(15):.0f}" y="{tz(mv.MVin_NAP_m) + 20:.1f}" '
            f'font-size="10" fill="#333">{boring.intreehoek_gr or 18}° intree</text>'
        )
        svg_parts.append(
            f'<text x="{tx(L_totaal - 15):.0f}" y="{tz(mv.MVuit_NAP_m) + 20:.1f}" '
            f'font-size="10" text-anchor="end" fill="#333">{boring.uittreehoek_gr or 22}° uittree</text>'
        )

    # ── Diepte + Rv label ──
    if boring.type == "Z" and boring.booghoek_gr:
        booglengte_str = ""
        for seg in profiel.segmenten:
            if seg["type"] == "arc" and "booglengte" in seg:
                booglengte_str = f" | Booglengte={seg['booglengte']:.1f}m"
                break
        diepte_label = f"Diepte {profiel.diepte_NAP_m:+.2f} NAP | Booghoek={boring.booghoek_gr:.1f}°{booglengte_str}"
    else:
        diepte_label = f"Diepte {profiel.diepte_NAP_m:+.2f} NAP | Rv={profiel.Rv_m:.0f}m"

    svg_parts.append(
        f'<text x="{tx(L_totaal / 2):.0f}" y="{tz(profiel.diepte_NAP_m) + 16:.1f}" '
        f'font-size="11" text-anchor="middle" fill="#333">{diepte_label}</text>'
    )

    # ── L totaal label bovenaan ──
    svg_parts.append(
        f'<text x="{tx(L_totaal / 2):.0f}" y="{margin_top - 6:.0f}" '
        f'font-size="13" text-anchor="middle" fill="#000" font-weight="bold">L = {L_totaal:.1f} m</text>'
    )

    # ── A INTREDE / B UITTREDE labels ──
    svg_parts.append(
        f'<text x="{tx(0):.0f}" y="{margin_top - 6:.0f}" '
        f'font-size="9" text-anchor="middle" fill="#333">A INTREDE</text>'
    )
    svg_parts.append(
        f'<text x="{tx(L_totaal):.0f}" y="{margin_top - 6:.0f}" '
        f'font-size="9" text-anchor="middle" fill="#333">B UITTREDE</text>'
    )

    svg = (
        f'<svg width="{svg_width}" height="{svg_height}" '
        f'viewBox="0 0 {svg_width} {svg_height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="background:#fff;">\n'
    )
    svg += "\n".join(svg_parts) + "\n"
    svg += "</svg>"
    return svg


def _fetch_map_image_b64(lat_center: float, lon_center: float, zoom: int = 16,
                          tiles_x: int = 3, tiles_y: int = 2) -> str | None:
    """Haal OSM kaartachtergrond op door tiles te stitchen.

    Returns: "image/png,{base64}" of None bij fout.
    """
    import base64
    import io
    import httpx
    import logging
    from PIL import Image
    logger = logging.getLogger(__name__)

    # Bereken tile indices voor center
    import math as _m
    n = 2 ** zoom
    tile_cx = int((lon_center + 180.0) / 360.0 * n)
    tile_cy = int((1.0 - _m.log(_m.tan(_m.radians(lat_center)) + 1.0 / _m.cos(_m.radians(lat_center))) / _m.pi) / 2.0 * n)

    # Grid van tiles rondom center
    half_x = tiles_x // 2
    half_y = tiles_y // 2
    tile_size = 256

    canvas = Image.new("RGB", (tiles_x * tile_size, tiles_y * tile_size))

    for dy in range(tiles_y):
        for dx in range(tiles_x):
            tx = tile_cx - half_x + dx
            ty = tile_cy - half_y + dy
            url = f"https://tile.openstreetmap.org/{zoom}/{tx}/{ty}.png"
            try:
                resp = httpx.get(url, timeout=8, headers={"User-Agent": "HDD-Platform/1.0"})
                if resp.status_code == 200:
                    tile_img = Image.open(io.BytesIO(resp.content))
                    canvas.paste(tile_img, (dx * tile_size, dy * tile_size))
            except Exception as exc:
                logger.warning("OSM tile fout %s: %s", url, exc)

    buf = io.BytesIO()
    canvas.save(buf, format="JPEG", quality=85)
    data = buf.getvalue()
    if len(data) < 5000:
        return None
    return "image/jpeg," + base64.b64encode(data).decode("ascii")


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
                f'xlink:href="data:{map_b64}" '
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
        f'<text x="{svg_w - 15}" y="18" font-size="14" font-weight="bold" fill="#333" text-anchor="middle">N</text>\n'
        f'<line x1="{svg_w - 15}" y1="22" x2="{svg_w - 15}" y2="38" stroke="#333" stroke-width="1.5"/>\n'
        f'<polygon points="{svg_w - 15},22 {svg_w - 19},28 {svg_w - 11},28" fill="#333"/>\n'
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

    # WeasyPrint rendert inline SVG niet betrouwbaar in table cells.
    # Oplossing: alle visuele elementen opslaan als tijdelijke bestanden.
    import tempfile
    import os
    tmpfiles = []

    def _svg_to_png_data_uri(svg_str: str) -> str:
        """Converteer SVG naar PNG data URI via cairosvg of fallback."""
        if not svg_str:
            return ""
        try:
            import cairosvg
            png_bytes = cairosvg.svg2png(bytestring=svg_str.encode("utf-8"), output_width=1200)
            import base64 as _b64mod
            return "data:image/png;base64," + _b64mod.b64encode(png_bytes).decode("ascii")
        except ImportError:
            pass
        # Fallback: sla SVG op als file
        try:
            f = tempfile.NamedTemporaryFile(suffix=".svg", delete=False, mode="w")
            f.write(svg_str)
            f.flush()
            tmpfiles.append(f.name)
            return f"file://{f.name}"
        except Exception:
            return ""

    def _bytes_to_tmpfile(data: bytes, suffix: str = ".jpg") -> str:
        """Sla bytes op als tijdelijk bestand, return file:// URL."""
        try:
            f = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
            f.write(data)
            f.flush()
            tmpfiles.append(f.name)
            return f"file://{f.name}"
        except Exception:
            return ""

    # Genereer SVG's
    lengteprofiel_svg = _generate_lengteprofiel_svg(boring)
    bovenaanzicht_svg = _generate_bovenaanzicht_svg(boring)

    # Doorsnede SVG
    doorsnede_svg = _generate_doorsnede_svg(boring)

    # Converteer SVG's naar PNG data URIs (of file fallback)
    lengteprofiel_url = _svg_to_png_data_uri(lengteprofiel_svg)
    doorsnede_url = _svg_to_png_data_uri(doorsnede_svg)

    # Overzichtskaart (bovenaanzicht): kleine OSM kaart op lagere zoom met tracé
    bovenaanzicht_url = ""
    if boring.trace_punten and len(boring.trace_punten) >= 2:
        try:
            import io as _io2
            import math as _m2
            import base64 as _b64_2
            from app.geo.coords import rd_to_wgs84 as _rd2wgs
            from PIL import Image as _Img, ImageDraw as _Draw

            _xs = [p.RD_x for p in boring.trace_punten]
            _ys = [p.RD_y for p in boring.trace_punten]
            _cx2 = (min(_xs) + max(_xs)) / 2
            _cy2 = (min(_ys) + max(_ys)) / 2
            _lat2, _lon2 = _rd2wgs(_cx2, _cy2)

            # Zoom 15 voor overzicht (meer uitgezoomd)
            _zm2 = 15
            _b64_ov = _fetch_map_image_b64(_lat2, _lon2, zoom=_zm2, tiles_x=3, tiles_y=3)
            if _b64_ov:
                _img_bytes2 = _b64_2.b64decode(_b64_ov.split(",", 1)[1])
                _img2 = _Img.open(_io2.BytesIO(_img_bytes2))
                _draw2 = _Draw.Draw(_img2)
                _iw2, _ih2 = _img2.size
                _mpp2 = 40075016.686 * _m2.cos(_m2.radians(_lat2)) / (256.0 * (2 ** _zm2))

                # Teken tracé
                _tpx2 = []
                for p in boring.trace_punten:
                    px = int(_iw2 / 2 + (p.RD_x - _cx2) / _mpp2)
                    py = int(_ih2 / 2 - (p.RD_y - _cy2) / _mpp2)
                    _tpx2.append((px, py))
                if len(_tpx2) >= 2:
                    _draw2.line(_tpx2, fill=(204, 0, 0), width=4)
                for px, py in _tpx2:
                    _draw2.ellipse([px-4, py-4, px+4, py+4], fill=(204, 0, 0))

                _buf2 = _io2.BytesIO()
                _img2.save(_buf2, format="JPEG", quality=85)
                bovenaanzicht_url = _bytes_to_tmpfile(_buf2.getvalue(), ".jpg")
        except Exception:
            pass
    if not bovenaanzicht_url:
        bovenaanzicht_url = _svg_to_png_data_uri(bovenaanzicht_svg)

    # Kaartachtergrond (OSM tiles)
    kaart_url = ""
    if boring.trace_punten and len(boring.trace_punten) >= 2:
        try:
            import base64 as _b64
            import io as _io
            import math as _m
            from app.geo.coords import rd_to_wgs84
            from PIL import Image, ImageDraw, ImageFont
            from shapely import from_wkt
            from shapely.geometry import LineString

            xs = [p.RD_x for p in boring.trace_punten]
            ys = [p.RD_y for p in boring.trace_punten]
            cx = (min(xs) + max(xs)) / 2
            cy = (min(ys) + max(ys)) / 2
            lat_c, lon_c = rd_to_wgs84(cx, cy)

            # Zoom hoog genoeg dat tracé ~60% van de breedte vult
            trace_span = max(max(xs) - min(xs), max(ys) - min(ys))
            zm = 19 if trace_span < 500 else 18

            b64 = _fetch_map_image_b64(lat_c, lon_c, zoom=zm, tiles_x=9, tiles_y=5)
            if b64:
                img_bytes = _b64.b64decode(b64.split(",", 1)[1])
                img = Image.open(_io.BytesIO(img_bytes))
                draw = ImageDraw.Draw(img)
                img_w, img_h = img.size

                meters_per_pixel = 40075016.686 * _m.cos(_m.radians(lat_c)) / (256.0 * (2 ** zm))

                def rd_to_px(rd_x, rd_y):
                    px = img_w / 2 + (rd_x - cx) / meters_per_pixel
                    py = img_h / 2 - (rd_y - cy) / meters_per_pixel
                    return int(px), int(py)

                # ── KLIC leidingen tekenen ──
                KLIC_KLEUREN = {
                    "LAAGSPANNING": (190, 150, 0),      # goudgeel
                    "MIDDENSPANNING": (0, 130, 60),      # groen
                    "HOOGSPANNING": (220, 0, 0),         # rood
                    "LD-GAS": (160, 80, 0),              # bruin
                    "WATERLEIDING": (0, 85, 170),        # blauw
                    "RIOOL-VRIJVERVAL": (112, 48, 160),  # paars
                    "PERSRIOOL": (112, 48, 160),         # paars
                }
                if db is not None:
                    from app.order.models import KLICLeiding, KLICUpload
                    laatste_upload = (
                        db.query(KLICUpload)
                        .filter_by(order_id=order.id, verwerkt=True)
                        .order_by(KLICUpload.upload_datum.desc())
                        .first()
                    )
                    if laatste_upload:
                        klic_leidingen = db.query(KLICLeiding).filter_by(klic_upload_id=laatste_upload.id).all()
                        for leiding in klic_leidingen:
                            if not leiding.geometrie_wkt or not leiding.dxf_laag:
                                continue
                            kleur = KLIC_KLEUREN.get(leiding.dxf_laag, (150, 150, 150))
                            try:
                                geom = from_wkt(leiding.geometrie_wkt)
                                lines = []
                                if hasattr(geom, 'coords'):
                                    lines = [list(geom.coords)]
                                elif hasattr(geom, 'geoms'):
                                    lines = [list(g.coords) for g in geom.geoms]
                                for coords in lines:
                                    if len(coords) >= 2:
                                        pixels = [rd_to_px(c[0], c[1]) for c in coords]
                                        draw.line(pixels, fill=kleur, width=2)
                            except Exception:
                                continue

                # ── Tracélijn tekenen (bovenop KLIC) ──
                trace_pixels = [rd_to_px(p.RD_x, p.RD_y) for p in boring.trace_punten]
                if len(trace_pixels) >= 2:
                    draw.line(trace_pixels, fill=(204, 0, 0), width=6)

                # ── Sensorpunt labels ──
                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
                except Exception:
                    font = ImageFont.load_default()

                for i, p in enumerate(boring.trace_punten):
                    px, py = trace_pixels[i]
                    draw.ellipse([px-6, py-6, px+6, py+6], fill=(204, 0, 0), outline=(255, 255, 255))
                    if p.label:
                        tw = len(p.label) * 13
                        draw.rectangle([px+10, py-22, px+12+tw, py], fill=(255, 255, 255))
                        draw.text((px+11, py-22), p.label, fill=(204, 0, 0), font=font)

                # ── Crop: bijsnijden rond het tracé ──
                trace_px_xs = [tp[0] for tp in trace_pixels]
                trace_px_ys = [tp[1] for tp in trace_pixels]
                margin_px = 150  # pixels marge (ruim voor labels)
                crop_left = max(0, min(trace_px_xs) - margin_px)
                crop_top = max(0, min(trace_px_ys) - margin_px)
                crop_right = min(img_w, max(trace_px_xs) + margin_px)
                crop_bottom = min(img_h, max(trace_px_ys) + margin_px)
                # Minimale crop hoogte voor goede aspect ratio
                crop_h = crop_bottom - crop_top
                crop_w = crop_right - crop_left
                if crop_h < crop_w * 0.4:
                    extra = int((crop_w * 0.4 - crop_h) / 2)
                    crop_top = max(0, crop_top - extra)
                    crop_bottom = min(img_h, crop_bottom + extra)

                img = img.crop((crop_left, crop_top, crop_right, crop_bottom))

                buf = _io.BytesIO()
                img.save(buf, format="JPEG", quality=90)
                kaart_url = _bytes_to_tmpfile(buf.getvalue(), ".jpg")
        except Exception:
            pass

    # Logo's
    _logos_dir = Path(__file__).parent.parent.parent / "static" / "logos"
    gbt_logo_url = ""
    gbt_logo_path = _logos_dir / "gbt_logo.svg"
    if gbt_logo_path.exists():
        try:
            import cairosvg as _cairo
            png_bytes = _cairo.svg2png(bytestring=gbt_logo_path.read_bytes(), output_width=400)
            gbt_logo_url = _bytes_to_tmpfile(png_bytes, ".png")
        except Exception:
            pass

    # Klant logo (boorbedrijf)
    klant_logo_url = ""
    from app.order.klantcodes import get_klant_logo
    klant_logo_file = get_klant_logo(order.klantcode or "")
    if klant_logo_file:
        klant_logo_path = _logos_dir / klant_logo_file
        if klant_logo_path.exists():
            klant_logo_url = _bytes_to_tmpfile(klant_logo_path.read_bytes(),
                                                klant_logo_path.suffix)

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
        "lengteprofiel_url": lengteprofiel_url,
        "bovenaanzicht_url": bovenaanzicht_url,
        "kaart_url": kaart_url,
        "is_boogzinker": boring.type == "Z",
        "gbt_logo_url": gbt_logo_url,
        "doorsnede_url": doorsnede_url,
        "klant_logo_url": klant_logo_url,
    }

    template = _env.get_template("tekening.html")
    html_str = template.render(**context)
    pdf_bytes = HTML(string=html_str, base_url="/").write_pdf()

    # Cleanup alle tijdelijke bestanden
    for f in tmpfiles:
        try:
            os.unlink(f)
        except OSError:
            pass

    return pdf_bytes
