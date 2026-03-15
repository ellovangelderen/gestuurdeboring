"""DXF generator. Laagnamen exact conform HDD28 Velsen-Noord."""
import io
from typing import Optional

import ezdxf
from ezdxf.enums import TextEntityAlignment
from sqlalchemy.orm import Session

from app.project.models import Project


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


def _draw_boorlijn(msp, project: Project) -> None:
    """Tekent rechte boorlijn A→B (skeleton — geen booggeometrie)."""
    punten = project.trace_punten
    if len(punten) < 2:
        return
    coords = [(p.RD_x, p.RD_y) for p in punten]
    msp.add_lwpolyline(coords, dxfattribs={"layer": "BOORLIJN"})


def _draw_boorgat(msp, project: Project) -> None:
    """Boorgat als 2 cirkels op intredepunt: r_ruimer en r_buis."""
    intree = next((p for p in project.trace_punten if p.type == "intree"), None)
    if not intree:
        return
    center = (intree.RD_x, intree.RD_y)
    r_boorgat = (project.Dg_mm / 2) / 1000   # mm → m (schaal 1:1 in RD)
    r_buis = (project.De_mm / 2) / 1000
    msp.add_circle(center, radius=r_boorgat, dxfattribs={"layer": "BOORGAT"})
    msp.add_circle(center, radius=r_buis, dxfattribs={"layer": "BOORGAT"})


def _draw_sensorpunten(msp, project: Project) -> None:
    """Sensorpunt labels als TEXT op laag ATTRIBUTEN."""
    for punt in project.trace_punten:
        if punt.label:
            msp.add_text(
                punt.label,
                dxfattribs={
                    "layer": "ATTRIBUTEN",
                    "height": 2.0,
                    "insert": (punt.RD_x, punt.RD_y),
                },
            )


def _draw_titelblok(msp, project: Project) -> None:
    """Titelblok tekst op laag TITELBLOK_TEKST."""
    from datetime import date

    regels = [
        project.naam or "",
        f"Opdrachtgever: {project.opdrachtgever or ''}",
        f"Ordernummer: {project.ordernummer or ''}",
        f"Datum: {date.today().strftime('%d-%m-%Y')}",
        "Getekend: M.Luijben",
        "Akkoord: M.Visser",
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


def _draw_klic_leidingen(msp, project: Project, db: Session) -> None:
    """Tekent KLIC leidingen als LWPolyline op de juiste NLCS-laag."""
    from shapely import from_wkt
    from shapely.geometry import LineString, MultiLineString, Polygon
    from app.project.models import KLICLeiding, KLICUpload

    # Gebruik meest recente verwerkte upload
    upload = (
        db.query(KLICUpload)
        .filter_by(project_id=project.id, verwerkt=True)
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


def generate_dxf(project: Project, db: Optional[Session] = None) -> bytes:
    """Genereer DXF R2013 bytes voor een project."""
    doc = ezdxf.new("R2013")
    msp = doc.modelspace()

    _setup_layers(doc)
    _draw_boorlijn(msp, project)
    _draw_boorgat(msp, project)
    _draw_sensorpunten(msp, project)
    _draw_titelblok(msp, project)
    if db is not None:
        _draw_klic_leidingen(msp, project, db)

    buf = io.StringIO()
    doc.write(buf)
    return buf.getvalue().encode("utf-8")
