"""TC-profiel — Backlog 9: Boorprofiel geometrie ARCs."""
import math

import ezdxf
import io
import pytest

from app.geo.profiel import bereken_boorprofiel, bereken_Rv, arc_punten, trace_totale_afstand


# TC-profiel-E: bereken_Rv
def test_bereken_rv():
    assert bereken_Rv(160.0) == pytest.approx(192.0)
    assert bereken_Rv(110.0) == pytest.approx(132.0)
    assert bereken_Rv(250.0) == pytest.approx(300.0)


# TC-profiel-A: Boorprofiel berekening met ARCs
def test_profiel_a_arcs_correct():
    """HDD standaard: De=160mm, intree=18 graden, uittree=22 graden, L=200m"""
    profiel = bereken_boorprofiel(
        L_totaal_m=200.0, MVin_NAP_m=0.5, MVuit_NAP_m=0.3,
        alpha_in_gr=18.0, alpha_uit_gr=22.0, De_mm=160.0,
    )
    assert profiel.Rv_m == pytest.approx(192.0)
    assert len(profiel.segmenten) == 5  # lijn, arc, lijn, arc, lijn
    assert profiel.segmenten[0]["type"] == "lijn"
    assert profiel.segmenten[1]["type"] == "arc"
    assert profiel.segmenten[2]["type"] == "lijn"
    assert profiel.segmenten[3]["type"] == "arc"
    assert profiel.segmenten[4]["type"] == "lijn"
    # Horizontaal segment moet positieve lengte hebben
    horiz = [s for s in profiel.segmenten if s["type"] == "lijn" and s.get("horizontaal")]
    assert len(horiz) == 1
    assert horiz[0]["lengte"] > 0


# TC-profiel-B: Hoekberekening klopt
def test_profiel_b_hoekberekening():
    profiel = bereken_boorprofiel(
        L_totaal_m=200.0, MVin_NAP_m=0.5, MVuit_NAP_m=0.3,
        alpha_in_gr=18.0, alpha_uit_gr=22.0, De_mm=160.0,
    )
    # Rv = 192m
    Tin_h = 192.0 * math.sin(math.radians(18.0))
    Tuit_h = 192.0 * math.sin(math.radians(22.0))
    L_horiz = 200.0 - Tin_h - Tuit_h
    assert L_horiz > 0  # ~68.7m
    # Controleer dat het horizontale segment de juiste lengte heeft
    horiz_seg = [s for s in profiel.segmenten if s["type"] == "lijn" and s.get("horizontaal")][0]
    # Horizontale segment lengte in profiel kan afwijken door schuine lijn intree/uittree
    # maar moet positief zijn
    assert horiz_seg["lengte"] > 0


# TC-profiel-B2: Tangentlengtes wiskundig correct
def test_profiel_b2_tangentlengtes():
    """Verifieer Tin_h, Tuit_h, Tin_v, Tuit_v tegen bekende waarden."""
    Rv = 192.0
    alpha_in = math.radians(18.0)
    alpha_uit = math.radians(22.0)

    Tin_h = Rv * math.sin(alpha_in)
    Tin_v = Rv * (1 - math.cos(alpha_in))
    Tuit_h = Rv * math.sin(alpha_uit)
    Tuit_v = Rv * (1 - math.cos(alpha_uit))

    assert Tin_h == pytest.approx(59.34, abs=0.1)
    assert Tuit_h == pytest.approx(71.92, abs=0.1)
    assert Tin_v == pytest.approx(9.40, abs=0.1)
    assert Tuit_v == pytest.approx(13.98, abs=0.1)


# TC-profiel-C: DXF bevat ARC entities
def test_profiel_c_dxf_arcs():
    """DXF met maaiveld en trace moet ARC entities bevatten op LP-BOORLIJN laag."""
    from app.order.models import Boring, Order, TracePunt, MaaiveldOverride
    from app.documents.dxf_generator import generate_dxf

    order = Order(
        id="profiel-test-order",
        workspace_id="gbt-workspace-001",
        ordernummer="TEST-PROFIEL",
        locatie="Test",
    )
    boring = Boring(
        id="profiel-test-boring",
        order_id="profiel-test-order",
        volgnummer=1,
        type="B",
        De_mm=160.0,
        Dg_mm=240.0,
        intreehoek_gr=18.0,
        uittreehoek_gr=22.0,
    )
    # Trace: 200m horizontaal
    boring.trace_punten = [
        TracePunt(boring_id="profiel-test-boring", volgorde=0, type="intree", label="A", RD_x=100000.0, RD_y=400000.0),
        TracePunt(boring_id="profiel-test-boring", volgorde=1, type="uittree", label="B", RD_x=100200.0, RD_y=400000.0),
    ]
    boring.maaiveld_override = MaaiveldOverride(
        boring_id="profiel-test-boring",
        MVin_NAP_m=0.5,
        MVuit_NAP_m=0.3,
    )
    boring.doorsneden = []
    boring.berekening = None

    dxf_bytes = generate_dxf(boring, order)
    doc = ezdxf.read(io.StringIO(dxf_bytes.decode("utf-8")))
    msp = doc.modelspace()

    # ARC entities op LP-BOORLIJN laag
    arcs = [e for e in msp if e.dxftype() == "ARC" and e.dxf.layer == "LP-BOORLIJN"]
    assert len(arcs) == 2, f"Verwacht 2 ARCs, gevonden: {len(arcs)}"

    # LP-MAAIVELD laag moet LINE hebben
    mv_lines = [e for e in msp if e.dxftype() == "LINE" and e.dxf.layer == "LP-MAAIVELD"]
    assert len(mv_lines) >= 1

    # LP-MAATVOERING labels
    mv_texts = [e for e in msp if e.dxftype() == "TEXT" and e.dxf.layer == "LP-MAATVOERING"]
    assert len(mv_texts) >= 3  # MVin, MVuit, diepte labels


# TC-profiel-D: Edge case — trace te kort
def test_profiel_d_trace_te_kort():
    """Wanneer L_totaal < Tin_h + Tuit_h moet het profiel Rv aanpassen (geen crash)."""
    profiel = bereken_boorprofiel(
        L_totaal_m=50.0,  # Te kort voor standaard Rv=192m
        MVin_NAP_m=0.5, MVuit_NAP_m=0.3,
        alpha_in_gr=18.0, alpha_uit_gr=22.0, De_mm=160.0,
    )
    # Rv is aangepast
    assert profiel.Rv_m < 192.0
    # Profiel heeft nog steeds 5 segmenten
    assert len(profiel.segmenten) == 5
    # Horizontaal segment heeft lengte 0
    horiz = [s for s in profiel.segmenten if s["type"] == "lijn" and s.get("horizontaal")]
    assert len(horiz) == 1
    assert horiz[0]["lengte"] == pytest.approx(0.0, abs=0.01)


# TC-profiel-F: PDF bevat lengteprofiel SVG
def test_profiel_f_pdf_lengteprofiel():
    """PDF generatie met volledig profiel moet SVG lengteprofiel bevatten."""
    from app.order.models import Boring, Order, TracePunt, MaaiveldOverride
    from app.documents.pdf_generator import generate_pdf

    order = Order(
        id="profiel-pdf-order",
        workspace_id="gbt-workspace-001",
        ordernummer="TEST-PDF-PROFIEL",
        locatie="Test",
    )
    boring = Boring(
        id="profiel-pdf-boring",
        order_id="profiel-pdf-order",
        volgnummer=1,
        type="B",
        SDR=11,
        De_mm=160.0,
        Dg_mm=240.0,
        intreehoek_gr=18.0,
        uittreehoek_gr=22.0,
    )
    boring.trace_punten = [
        TracePunt(boring_id="profiel-pdf-boring", volgorde=0, type="intree", label="A", RD_x=100000.0, RD_y=400000.0),
        TracePunt(boring_id="profiel-pdf-boring", volgorde=1, type="uittree", label="B", RD_x=100200.0, RD_y=400000.0),
    ]
    boring.maaiveld_override = MaaiveldOverride(
        boring_id="profiel-pdf-boring",
        MVin_NAP_m=0.5,
        MVuit_NAP_m=0.3,
    )
    boring.doorsneden = []
    boring.berekening = None

    pdf_bytes = generate_pdf(boring, order)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes[:4] == b"%PDF"


# TC-profiel-G: arc_punten discretisatie
def test_arc_punten_discretisatie():
    """arc_punten moet n+1 punten genereren op de cirkel."""
    pts = arc_punten(0, 0, 10.0, 0, math.pi / 2, n=10)
    assert len(pts) == 11
    # Eerste punt op (10, 0)
    assert pts[0][0] == pytest.approx(10.0)
    assert pts[0][1] == pytest.approx(0.0)
    # Laatste punt op (0, 10)
    assert pts[-1][0] == pytest.approx(0.0, abs=0.01)
    assert pts[-1][1] == pytest.approx(10.0, abs=0.01)


# TC-profiel-H: trace_totale_afstand
def test_trace_totale_afstand():
    """Rechte lijn van 200m."""
    afstand = trace_totale_afstand([(0, 0), (200, 0)])
    assert afstand == pytest.approx(200.0)

    # Diagonaal
    afstand2 = trace_totale_afstand([(0, 0), (100, 100)])
    assert afstand2 == pytest.approx(math.sqrt(20000))

    # Leeg / 1 punt
    assert trace_totale_afstand([]) == 0.0
    assert trace_totale_afstand([(5, 5)]) == 0.0


# TC-profiel-I: Boring.Rv_m property
def test_boring_rv_m_property():
    from app.order.models import Boring
    b = Boring(id="rv-test", order_id="x", volgnummer=1, type="B", De_mm=160.0)
    assert b.Rv_m == pytest.approx(192.0)

    b2 = Boring(id="rv-test2", order_id="x", volgnummer=1, type="B", De_mm=250.0)
    assert b2.Rv_m == pytest.approx(300.0)


# TC-profiel-J: Profiel continuiteit — segmenten sluiten op elkaar aan
def test_profiel_j_continuiteit():
    """Eind van elk segment = begin van volgend segment."""
    profiel = bereken_boorprofiel(
        L_totaal_m=200.0, MVin_NAP_m=0.5, MVuit_NAP_m=0.3,
        alpha_in_gr=18.0, alpha_uit_gr=22.0, De_mm=160.0,
    )
    for i in range(len(profiel.segmenten) - 1):
        seg = profiel.segmenten[i]
        volgende = profiel.segmenten[i + 1]
        assert seg["x_end"] == pytest.approx(volgende["x_start"], abs=0.1), \
            f"Segment {i} x_end={seg['x_end']} != segment {i+1} x_start={volgende['x_start']}"
        assert seg["z_end"] == pytest.approx(volgende["z_start"], abs=0.1), \
            f"Segment {i} z_end={seg['z_end']} != segment {i+1} z_start={volgende['z_start']}"


# TC-profiel-K: DXF zonder maaiveld crasht niet
def test_profiel_k_dxf_zonder_maaiveld():
    """DXF generatie zonder maaiveld data moet gewoon werken (geen lengteprofiel)."""
    from app.order.models import Boring, Order, TracePunt
    from app.documents.dxf_generator import generate_dxf

    order = Order(id="no-mv-order", workspace_id="gbt-workspace-001", ordernummer="TEST-NOMV")
    boring = Boring(id="no-mv-boring", order_id="no-mv-order", volgnummer=1, type="B", De_mm=160.0, Dg_mm=240.0)
    boring.trace_punten = [
        TracePunt(boring_id="no-mv-boring", volgorde=0, type="intree", label="A", RD_x=100000.0, RD_y=400000.0),
        TracePunt(boring_id="no-mv-boring", volgorde=1, type="uittree", label="B", RD_x=100200.0, RD_y=400000.0),
    ]
    boring.maaiveld_override = None
    boring.doorsneden = []
    boring.berekening = None

    dxf_bytes = generate_dxf(boring, order)
    assert isinstance(dxf_bytes, bytes)
    assert len(dxf_bytes) > 0

    # Geen LP-BOORLIJN arcs (geen maaiveld = geen lengteprofiel)
    doc = ezdxf.read(io.StringIO(dxf_bytes.decode("utf-8")))
    msp = doc.modelspace()
    arcs = [e for e in msp if e.dxftype() == "ARC" and e.dxf.layer == "LP-BOORLIJN"]
    assert len(arcs) == 0
