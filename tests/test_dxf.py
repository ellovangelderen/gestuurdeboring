"""TC-dxf — Module 6: DXF generatie"""
import ezdxf
import io

import pytest


def _maak_hdd11_boring_order():
    """Maak HDD11 boring + order objecten zonder DB (voor unit tests)."""
    from app.order.models import Boring, Order, TracePunt

    order = Order(
        id="hdd11-order",
        workspace_id="gbt-workspace-001",
        ordernummer="3D25V700",
        locatie="Haarlem, Kennemerplein",
        klantcode="3D",
        opdrachtgever="Liander",
    )

    boring = Boring(
        id="hdd11-boring",
        order_id="hdd11-order",
        volgnummer=1,
        type="B",
        SDR=11,
        De_mm=160.0,
        dn_mm=14.6,
        Dg_mm=240.0,
        Dp_mm=110.0,
        Db_mm=60.0,
        intreehoek_gr=18.0,
        uittreehoek_gr=22.0,
    )

    punten = [
        TracePunt(boring_id="hdd11-boring", volgorde=0, type="intree",     label="A",   RD_x=103896.9, RD_y=489289.5),
        TracePunt(boring_id="hdd11-boring", volgorde=1, type="tussenpunt", label="Tv1", RD_x=103916.4, RD_y=489284.1),
        TracePunt(boring_id="hdd11-boring", volgorde=2, type="tussenpunt", label="Tv2", RD_x=103934.3, RD_y=489279.1),
        TracePunt(boring_id="hdd11-boring", volgorde=3, type="tussenpunt", label="Th1", RD_x=103947.3, RD_y=489275.5),
        TracePunt(boring_id="hdd11-boring", volgorde=4, type="tussenpunt", label="Th2", RD_x=103960.8, RD_y=489272.4),
        TracePunt(boring_id="hdd11-boring", volgorde=5, type="tussenpunt", label="Tv3", RD_x=104079.7, RD_y=489250.8),
        TracePunt(boring_id="hdd11-boring", volgorde=6, type="tussenpunt", label="Tv4", RD_x=104109.2, RD_y=489245.5),
        TracePunt(boring_id="hdd11-boring", volgorde=7, type="uittree",    label="B",   RD_x=104118.8, RD_y=489243.7),
    ]
    boring.trace_punten = punten
    return boring, order


# TC-dxf-A: DXF genereren → ezdxf parse zonder errors
def test_dxf_a_parse_zonder_errors():
    from app.documents.dxf_generator import generate_dxf
    boring, order = _maak_hdd11_boring_order()
    dxf_bytes = generate_dxf(boring, order)
    assert isinstance(dxf_bytes, bytes)
    assert len(dxf_bytes) > 0

    doc = ezdxf.read(io.StringIO(dxf_bytes.decode("utf-8")))
    assert doc is not None


# TC-dxf-B: Alle 16 lagen aanwezig met juiste ACI-kleur
def test_dxf_b_alle_lagen():
    from app.documents.dxf_generator import generate_dxf, LAYERS
    boring, order = _maak_hdd11_boring_order()
    dxf_bytes = generate_dxf(boring, order)
    doc = ezdxf.read(io.StringIO(dxf_bytes.decode("utf-8")))

    for layer_naam, props in LAYERS.items():
        assert layer_naam in doc.layers, f"Laag {layer_naam} ontbreekt"
        laag = doc.layers.get(layer_naam)
        assert laag.dxf.color == props["color"], \
            f"Laag {layer_naam}: kleur {laag.dxf.color}, verwacht {props['color']}"


# TC-dxf-C: NLCS lijntype-definities aanwezig in DXF
def test_dxf_c_nlcs_lijntypes():
    from app.documents.dxf_generator import generate_dxf, NLCS_LINETYPES
    boring, order = _maak_hdd11_boring_order()
    dxf_bytes = generate_dxf(boring, order)
    doc = ezdxf.read(io.StringIO(dxf_bytes.decode("utf-8")))

    for lt_name in NLCS_LINETYPES:
        assert lt_name in doc.linetypes, f"Lijntype {lt_name} ontbreekt"


# TC-dxf-D: BOORLIJN laag heeft entiteiten
def test_dxf_d_boorlijn_heeft_entiteiten():
    from app.documents.dxf_generator import generate_dxf
    boring, order = _maak_hdd11_boring_order()
    dxf_bytes = generate_dxf(boring, order)
    doc = ezdxf.read(io.StringIO(dxf_bytes.decode("utf-8")))

    msp = doc.modelspace()
    boorlijn_entities = [e for e in msp if e.dxf.layer == "BOORLIJN"]
    assert len(boorlijn_entities) > 0


# TC-dxf-E: BOORGAT cirkels voor HDD11 (Dg=240mm → r=120mm, De=160mm → r=80mm)
def test_dxf_e_boorgat_stralen_hdd11():
    from app.documents.dxf_generator import generate_dxf
    boring, order = _maak_hdd11_boring_order()
    dxf_bytes = generate_dxf(boring, order)
    doc = ezdxf.read(io.StringIO(dxf_bytes.decode("utf-8")))

    msp = doc.modelspace()
    cirkels = [e for e in msp if e.dxftype() == "CIRCLE" and e.dxf.layer == "BOORGAT"]
    assert len(cirkels) == 2

    stralen = sorted([c.dxf.radius for c in cirkels])
    # Rmin = De/2 / 1000 = 80mm / 1000 = 0.080m
    # Rmax = Dg/2 / 1000 = 120mm / 1000 = 0.120m
    assert stralen[0] == pytest.approx(0.080, abs=0.001), f"r_buis={stralen[0]}, verwacht 0.080"
    assert stralen[1] == pytest.approx(0.120, abs=0.001), f"r_boorgat={stralen[1]}, verwacht 0.120"


# TC-dxf-F: Sensorpunt label "A" aanwezig op ATTRIBUTEN laag
def test_dxf_f_sensorpunt_label_a():
    from app.documents.dxf_generator import generate_dxf
    boring, order = _maak_hdd11_boring_order()
    dxf_bytes = generate_dxf(boring, order)
    doc = ezdxf.read(io.StringIO(dxf_bytes.decode("utf-8")))

    msp = doc.modelspace()
    labels = [e.dxf.text for e in msp if e.dxftype() == "TEXT" and e.dxf.layer == "ATTRIBUTEN"]
    assert "A" in labels, f"Label 'A' niet gevonden, wel: {labels}"


# TC-dxf-G: Bestandsversie = R2013 (AC1027)
def test_dxf_g_bestandsversie_r2013():
    from app.documents.dxf_generator import generate_dxf
    boring, order = _maak_hdd11_boring_order()
    dxf_bytes = generate_dxf(boring, order)
    doc = ezdxf.read(io.StringIO(dxf_bytes.decode("utf-8")))
    assert doc.dxfversion == "AC1027", f"Versie: {doc.dxfversion}, verwacht AC1027"
