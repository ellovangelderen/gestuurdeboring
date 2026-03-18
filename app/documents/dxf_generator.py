"""DXF generator. Laagnamen exact conform HDD28 Velsen-Noord."""
import io
from typing import Optional

import ezdxf
from ezdxf.enums import TextEntityAlignment
from sqlalchemy.orm import Session

from app.order.models import Boring, Order


NLCS_LINETYPES: dict[str, str] = {
    "KL-LS-N":     "ELECTRA LAAGSPANNING VOLGENS NLCS",
    "KL-MS-N":     "ELECTRA MIDDENSPANNING VOLGENS NLCS",
    "KL-HS-N":     "ELECTRA HOOGSPANNING VOLGENS NLCS",
    "KL-GAS-LD-N": "GAS LAGEDRUK VOLGENS NLCS",
    "KL-WATER-N":  "WATERLEIDING VOLGENS NLCS",
    "RI-OVERIG":   "OVERIGE LEIDINGEN",
    "RI-PERS":     "PERSLEIDING",
    "KG-PERCEEL":  "KADASTRALE PERCEELGRENS",
}

LAYERS: dict[str, dict] = {
    "BOORLIJN":          {"color": 1,   "linetype": "Continuous"},
    "BOORGAT":           {"color": 5,   "linetype": "DASHDOT"},
    "MAAIVELD":          {"color": 122, "linetype": "Continuous"},
    "MAATVOERING":       {"color": 170, "linetype": "Continuous"},
    "MAATVOERING-GRIJS": {"color": 251, "linetype": "Continuous"},
    "ATTRIBUTEN":        {"color": 252, "linetype": "Continuous"},
    "TITELBLOK_TEKST":   {"color": 7,   "linetype": "Continuous"},
    "LAAGSPANNING":      {"color": 190, "linetype": "KL-LS-N"},
    "MIDDENSPANNING":    {"color": 130, "linetype": "KL-MS-N"},
    "HOOGSPANNING":      {"color": 10,  "linetype": "KL-HS-N"},
    "LD-GAS":            {"color": 50,  "linetype": "KL-GAS-LD-N"},
    "WATERLEIDING":      {"color": 170, "linetype": "KL-WATER-N"},
    "RIOOL-VRIJVERVAL":  {"color": 210, "linetype": "RI-OVERIG"},
    "PERSRIOOL":         {"color": 210, "linetype": "RI-PERS"},
    "KADASTER":          {"color": 150, "linetype": "KG-PERCEEL"},
    "WEGDEK":            {"color": 252, "linetype": "Continuous"},
    "EV-ZONE":           {"color": 1,   "linetype": "Continuous"},
    # Lengteprofiel lagen
    "LP-MAAIVELD":       {"color": 3,   "linetype": "Continuous"},
    "LP-BOORLIJN":       {"color": 1,   "linetype": "Continuous"},
    "LP-MAATVOERING":    {"color": 7,   "linetype": "Continuous"},
    "LP-KADER":          {"color": 7,   "linetype": "Continuous"},
}


def _setup_layers(doc: ezdxf.document.Drawing) -> None:
    """Maak NLCS lijntype-definities en lagen aan."""
    # Lijntypen registreren — pattern vereist minimaal één element in ezdxf
    # Waarden: positief=streep, negatief=ruimte, 0.0=punt
    NLCS_PATTERNS = {
        "KL-LS-N":     [0.5, -0.25, 0.0, -0.25],
        "KL-MS-N":     [0.75, -0.25, 0.0, -0.25],
        "KL-HS-N":     [1.0, -0.25, 0.0, -0.25],
        "KL-GAS-LD-N": [0.5, -0.25],
        "KL-WATER-N":  [0.75, -0.25, 0.25, -0.25],
        "RI-OVERIG":   [0.5, -0.25, 0.25, -0.25],
        "RI-PERS":     [0.75, -0.25],
        "KG-PERCEEL":  [0.5, -0.125],
    }
    # DASHDOT voor BOORGAT laag
    if "DASHDOT" not in doc.linetypes:
        doc.linetypes.new("DASHDOT", dxfattribs={"description": "Dash dot", "pattern": [0.5, -0.25, 0.0, -0.25]})

    for lt_name, description in NLCS_LINETYPES.items():
        if lt_name not in doc.linetypes:
            doc.linetypes.new(
                lt_name,
                dxfattribs={"description": description, "pattern": NLCS_PATTERNS[lt_name]},
            )

    # Lagen aanmaken
    for layer_name, props in LAYERS.items():
        if layer_name not in doc.layers:
            doc.layers.new(
                layer_name,
                dxfattribs={"color": props["color"], "linetype": props["linetype"]},
            )


def _draw_boorlijn(msp, boring: Boring) -> None:
    """Tekent rechte boorlijn A→B (skeleton — geen booggeometrie)."""
    punten = boring.trace_punten
    if len(punten) < 2:
        return
    coords = [(p.RD_x, p.RD_y) for p in punten]
    msp.add_lwpolyline(coords, dxfattribs={"layer": "BOORLIJN"})


def _draw_boorgat(msp, boring: Boring) -> None:
    """Boorgat als 2 cirkels op intredepunt: r_ruimer en r_buis."""
    intree = next((p for p in boring.trace_punten if p.type == "intree"), None)
    if not intree:
        return
    center = (intree.RD_x, intree.RD_y)
    r_boorgat = (boring.Dg_mm / 2) / 1000   # mm → m (schaal 1:1 in RD)
    r_buis = (boring.De_mm / 2) / 1000
    msp.add_circle(center, radius=r_boorgat, dxfattribs={"layer": "BOORGAT"})
    msp.add_circle(center, radius=r_buis, dxfattribs={"layer": "BOORGAT"})


def _draw_sensorpunten(msp, boring: Boring) -> None:
    """Sensorpunt labels als TEXT op laag ATTRIBUTEN."""
    for punt in boring.trace_punten:
        if punt.label:
            msp.add_text(
                punt.label,
                dxfattribs={
                    "layer": "ATTRIBUTEN",
                    "height": 2.0,
                    "insert": (punt.RD_x, punt.RD_y),
                },
            )


def _draw_titelblok(msp, boring: Boring, order: Order) -> None:
    """Titelblok tekst op laag TITELBLOK_TEKST."""
    from datetime import date

    regels = [
        f"{order.ordernummer or ''} - {order.locatie or ''}",
        f"Boring {boring.volgnummer:02d} ({boring.type}) {boring.naam or ''}",
        f"Opdrachtgever: {order.opdrachtgever or ''}",
        f"Datum: {date.today().strftime('%d-%m-%Y')}",
        "Getekend: M.Luijben",
        f"Akkoord: {order.akkoord_contact or ''}",
    ]
    # Plaatst tekst links-onder van oorsprong (modelspace 0,0)
    for i, regel in enumerate(regels):
        msp.add_text(
            regel,
            dxfattribs={
                "layer": "TITELBLOK_TEKST",
                "height": 3.0,
                "insert": (0, -(i * 5)),
            },
        )


def _draw_klic_leidingen(msp, order: Order, db: Session) -> None:
    """Tekent KLIC leidingen als LWPolyline op de juiste NLCS-laag."""
    from shapely import from_wkt
    from shapely.geometry import LineString, MultiLineString, Polygon
    from app.order.models import KLICLeiding, KLICUpload

    # Gebruik meest recente verwerkte upload
    upload = (
        db.query(KLICUpload)
        .filter_by(order_id=order.id, verwerkt=True)
        .order_by(KLICUpload.upload_datum.desc())
        .first()
    )
    if not upload:
        return

    leidingen = db.query(KLICLeiding).filter_by(klic_upload_id=upload.id).all()
    for leiding in leidingen:
        if not leiding.geometrie_wkt or not leiding.dxf_laag:
            continue
        try:
            geom = from_wkt(leiding.geometrie_wkt)
        except Exception:
            continue

        if geom is None or geom.is_empty:
            continue

        layer = leiding.dxf_laag
        if isinstance(geom, LineString):
            coords = list(geom.coords)
            if len(coords) >= 2:
                msp.add_lwpolyline(coords, dxfattribs={"layer": layer})
        elif isinstance(geom, MultiLineString):
            for part in geom.geoms:
                coords = list(part.coords)
                if len(coords) >= 2:
                    msp.add_lwpolyline(coords, dxfattribs={"layer": layer})
        elif isinstance(geom, Polygon):
            coords = list(geom.exterior.coords)
            if len(coords) >= 2:
                msp.add_lwpolyline(coords, dxfattribs={"layer": layer, "closed": True})


def _draw_lengteprofiel(msp, boring: Boring, order: Order, db: Optional[Session] = None) -> None:
    """Teken lengteprofiel (verticaal vlak) onder het bovenaanzicht."""
    from app.geo.profiel import bereken_boorprofiel, trace_totale_afstand, arc_punten

    # Benodigde data beschikbaar?
    punten = boring.trace_punten
    if len(punten) < 2:
        return
    mv = boring.maaiveld_override
    if mv is None or mv.MVin_NAP_m is None or mv.MVuit_NAP_m is None:
        return

    # Totale trace afstand
    coords = [(p.RD_x, p.RD_y) for p in punten]
    L_totaal = trace_totale_afstand(coords)
    if L_totaal < 1.0:
        return

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
        return

    # Y-offset: teken lengteprofiel 500m onder bovenaanzicht oorsprong
    y_offset = -500.0

    # Maaiveldlijn (groen)
    msp.add_line(
        (0, mv.MVin_NAP_m + y_offset),
        (L_totaal, mv.MVuit_NAP_m + y_offset),
        dxfattribs={"layer": "LP-MAAIVELD"},
    )

    # Boorlijn segmenten
    for seg in profiel.segmenten:
        if seg["type"] == "lijn":
            if seg.get("lengte", 0) < 0.001:
                continue
            msp.add_line(
                (seg["x_start"], seg["z_start"] + y_offset),
                (seg["x_end"], seg["z_end"] + y_offset),
                dxfattribs={"layer": "LP-BOORLIJN"},
            )
        elif seg["type"] == "arc":
            # ezdxf add_arc verwacht center, radius, start_angle, end_angle in degrees
            # In ezdxf: hoeken in graden, CCW vanuit positieve x-as
            # Onze boog gaat van seg start naar seg end.
            # We discretiseren naar punten en tekenen als LWPOLYLINE voor betrouwbaarheid,
            # plus een echte ARC entity.
            cx = seg["cx"]
            cz = seg["cz"] + y_offset
            radius = seg["radius"]

            # Bereken start/eind hoek in ezdxf conventie
            # Van center naar startpunt
            import math
            dx_s = seg["x_start"] - seg["cx"]
            dz_s = seg["z_start"] - seg["cz"]
            start_deg = math.degrees(math.atan2(dz_s, dx_s))

            dx_e = seg["x_end"] - seg["cx"]
            dz_e = seg["z_end"] - seg["cz"]
            end_deg = math.degrees(math.atan2(dz_e, dx_e))

            msp.add_arc(
                center=(cx, cz),
                radius=radius,
                start_angle=start_deg,
                end_angle=end_deg,
                dxfattribs={"layer": "LP-BOORLIJN"},
            )

    # Maatvoering: NAP labels
    text_h = 2.0
    # Intree maaiveld label
    msp.add_text(
        f"MV {mv.MVin_NAP_m:+.2f} NAP",
        dxfattribs={"layer": "LP-MAATVOERING", "height": text_h, "insert": (0, mv.MVin_NAP_m + y_offset + 2)},
    )
    # Uittree maaiveld label
    msp.add_text(
        f"MV {mv.MVuit_NAP_m:+.2f} NAP",
        dxfattribs={"layer": "LP-MAATVOERING", "height": text_h, "insert": (L_totaal, mv.MVuit_NAP_m + y_offset + 2)},
    )
    # Diepte label
    msp.add_text(
        f"Diepte {profiel.diepte_NAP_m:+.2f} NAP",
        dxfattribs={"layer": "LP-MAATVOERING", "height": text_h,
                    "insert": (L_totaal / 2, profiel.diepte_NAP_m + y_offset - 3)},
    )
    # Hoek labels
    msp.add_text(
        f"Intree {boring.intreehoek_gr or 18.0:.0f} graden",
        dxfattribs={"layer": "LP-MAATVOERING", "height": text_h, "insert": (5, mv.MVin_NAP_m + y_offset - 5)},
    )
    msp.add_text(
        f"Uittree {boring.uittreehoek_gr or 22.0:.0f} graden",
        dxfattribs={"layer": "LP-MAATVOERING", "height": text_h, "insert": (L_totaal - 30, mv.MVuit_NAP_m + y_offset - 5)},
    )
    # Afstand label
    msp.add_text(
        f"L = {L_totaal:.1f} m",
        dxfattribs={"layer": "LP-MAATVOERING", "height": text_h,
                    "insert": (L_totaal / 2, mv.MVin_NAP_m + y_offset + 5)},
    )
    # Rv label
    msp.add_text(
        f"Rv = {profiel.Rv_m:.0f} m",
        dxfattribs={"layer": "LP-MAATVOERING", "height": text_h,
                    "insert": (L_totaal / 2, profiel.diepte_NAP_m + y_offset - 6)},
    )

    # Kader rond lengteprofiel
    z_min = profiel.diepte_NAP_m - 10
    z_max = max(mv.MVin_NAP_m, mv.MVuit_NAP_m) + 10
    msp.add_lwpolyline(
        [(-10, z_min + y_offset), (L_totaal + 10, z_min + y_offset),
         (L_totaal + 10, z_max + y_offset), (-10, z_max + y_offset)],
        dxfattribs={"layer": "LP-KADER"},
        close=True,
    )


def _draw_ev_zones(msp, order: Order, db: Session) -> None:
    """Tekent EV-zones als gesloten LWPOLYLINE op laag EV-ZONE."""
    from shapely import from_wkt
    from shapely.geometry import Polygon, MultiPolygon
    from app.order.models import EVZone

    zones = db.query(EVZone).filter_by(order_id=order.id).all()
    for zone in zones:
        if not zone.geometrie_wkt:
            continue
        try:
            geom = from_wkt(zone.geometrie_wkt)
        except Exception:
            continue

        if geom is None or geom.is_empty:
            continue

        polygons = []
        if isinstance(geom, Polygon):
            polygons = [geom]
        elif isinstance(geom, MultiPolygon):
            polygons = list(geom.geoms)

        for poly in polygons:
            coords = list(poly.exterior.coords)
            if len(coords) >= 3:
                msp.add_lwpolyline(
                    coords,
                    dxfattribs={"layer": "EV-ZONE", "const_width": 0.5},
                    close=True,
                )
                # Voeg tekst "EV-ZONE" bij centroid
                centroid = poly.centroid
                msp.add_text(
                    "EV-ZONE",
                    dxfattribs={
                        "layer": "EV-ZONE",
                        "height": 3.0,
                        "insert": (centroid.x, centroid.y),
                        "color": 1,
                    },
                )


def generate_dxf(boring: Boring, order: Order, db: Optional[Session] = None) -> bytes:
    """Genereer DXF R2013 bytes voor een boring."""
    doc = ezdxf.new("R2013")
    msp = doc.modelspace()

    _setup_layers(doc)
    _draw_boorlijn(msp, boring)
    _draw_boorgat(msp, boring)
    _draw_sensorpunten(msp, boring)
    _draw_titelblok(msp, boring, order)
    _draw_lengteprofiel(msp, boring, order, db)
    if db is not None:
        _draw_klic_leidingen(msp, order, db)
        _draw_ev_zones(msp, order, db)

    buf = io.StringIO()
    doc.write(buf)
    return buf.getvalue().encode("utf-8")
