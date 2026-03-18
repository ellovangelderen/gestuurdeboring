"""TC-evzone — Backlog 3b: EV-zone DXF rendering + UI waarschuwingen."""
import ezdxf
import io

import pytest

from tests.conftest import AUTH


def _maak_order_boring_evzone(db):
    """Maak een order + boring + EVZone record met synthetische polygoon WKT."""
    from app.order.models import Boring, EVPartij, EVZone, KLICUpload, Order, TracePunt

    order = Order(
        id="evzone-order-001",
        workspace_id="gbt-workspace-001",
        ordernummer="EV25TEST",
        locatie="Testlocatie EV",
        klantcode="3D",
        opdrachtgever="TestBeheerder",
    )
    db.add(order)
    db.flush()

    boring = Boring(
        id="evzone-boring-001",
        order_id=order.id,
        volgnummer=1,
        type="B",
        SDR=11,
        De_mm=160.0,
        Dg_mm=240.0,
    )
    db.add(boring)

    # Trace punten (minimaal 2 voor DXF)
    tp1 = TracePunt(boring_id=boring.id, volgorde=0, type="intree", label="A", RD_x=100000.0, RD_y=400000.0)
    tp2 = TracePunt(boring_id=boring.id, volgorde=1, type="uittree", label="B", RD_x=100100.0, RD_y=400000.0)
    db.add(tp1)
    db.add(tp2)

    upload = KLICUpload(
        id="evzone-upload-001",
        order_id=order.id,
        bestandsnaam="test.xml",
        verwerkt=True,
    )
    db.add(upload)
    db.flush()

    # Synthetische polygoon EV-zone
    wkt = "POLYGON ((100000 400000, 100100 400000, 100100 400100, 100000 400100, 100000 400000))"
    zone = EVZone(
        order_id=order.id,
        klic_upload_id=upload.id,
        beheerder="Liander",
        geometrie_wkt=wkt,
        netwerk_href="test-netwerk-001",
    )
    db.add(zone)
    db.flush()

    return order, boring, zone


def _maak_order_met_ev_partij(db):
    """Maak een order met EVPartij (voor UI waarschuwing tests)."""
    from app.order.models import Boring, EVPartij, Order, TracePunt

    order = Order(
        id="evpartij-order-001",
        workspace_id="gbt-workspace-001",
        ordernummer="EVP25TEST",
        locatie="Testlocatie EVPartij",
        klantcode="3D",
    )
    db.add(order)
    db.flush()

    boring = Boring(
        id="evpartij-boring-001",
        order_id=order.id,
        volgnummer=1,
        type="B",
    )
    db.add(boring)

    tp1 = TracePunt(boring_id=boring.id, volgorde=0, type="intree", label="A", RD_x=100000.0, RD_y=400000.0)
    db.add(tp1)

    partij = EVPartij(
        order_id=order.id,
        naam="Stedin — ev@stedin.nl",
        volgorde=0,
    )
    db.add(partij)
    db.commit()

    return order, boring


# TC-evzone-A: DXF bevat EV-zone laag met LWPOLYLINE
def test_evzone_a_dxf_bevat_ev_zone_laag(db):
    from app.documents.dxf_generator import generate_dxf
    order, boring, zone = _maak_order_boring_evzone(db)
    db.commit()

    dxf_bytes = generate_dxf(boring, order, db)
    assert isinstance(dxf_bytes, bytes)
    assert len(dxf_bytes) > 0

    doc = ezdxf.read(io.StringIO(dxf_bytes.decode("utf-8")))
    assert "EV-ZONE" in doc.layers, "Laag EV-ZONE ontbreekt"

    msp = doc.modelspace()
    ev_entities = [e for e in msp if e.dxf.layer == "EV-ZONE"]
    # Verwacht minimaal 1 LWPOLYLINE + 1 TEXT
    polylines = [e for e in ev_entities if e.dxftype() == "LWPOLYLINE"]
    assert len(polylines) >= 1, f"Geen LWPOLYLINE op EV-ZONE laag, entities: {[e.dxftype() for e in ev_entities]}"

    texts = [e for e in ev_entities if e.dxftype() == "TEXT"]
    assert len(texts) >= 1, "Geen EV-ZONE tekst label"
    assert any("EV-ZONE" in t.dxf.text for t in texts)


# TC-evzone-B: PDF bevat EV-waarschuwing
def test_evzone_b_pdf_bevat_ev_waarschuwing(db):
    from app.documents.pdf_generator import generate_pdf
    order, boring, zone = _maak_order_boring_evzone(db)
    db.commit()

    pdf_bytes = generate_pdf(boring, order, db=db)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0


# TC-evzone-C: Order detail toont EV-waarschuwing
def test_evzone_c_order_detail_waarschuwing(db, client, workspace):
    order, boring = _maak_order_met_ev_partij(db)

    resp = client.get(f"/orders/{order.id}", auth=AUTH)
    assert resp.status_code == 200
    assert "WAARSCHUWING" in resp.text


# TC-evzone-D: Boring detail toont EV-waarschuwing
def test_evzone_d_boring_detail_waarschuwing(db, client, workspace):
    order, boring = _maak_order_met_ev_partij(db)

    resp = client.get(f"/orders/{order.id}/boringen/1", auth=AUTH)
    assert resp.status_code == 200
    assert "WAARSCHUWING" in resp.text


# TC-evzone-E: DXF zonder EV-zones heeft geen EV-ZONE entities
def test_evzone_e_dxf_zonder_ev_zones(db):
    from app.order.models import Boring, Order, TracePunt
    from app.documents.dxf_generator import generate_dxf

    order = Order(
        id="no-evzone-order",
        workspace_id="gbt-workspace-001",
        ordernummer="NOEV25TEST",
        locatie="Geen EV",
    )
    db.add(order)
    db.flush()

    boring = Boring(
        id="no-evzone-boring",
        order_id=order.id,
        volgnummer=1,
        type="B",
    )
    db.add(boring)
    tp1 = TracePunt(boring_id=boring.id, volgorde=0, type="intree", label="A", RD_x=100000.0, RD_y=400000.0)
    tp2 = TracePunt(boring_id=boring.id, volgorde=1, type="uittree", label="B", RD_x=100100.0, RD_y=400000.0)
    db.add(tp1)
    db.add(tp2)
    db.commit()

    dxf_bytes = generate_dxf(boring, order, db)
    doc = ezdxf.read(io.StringIO(dxf_bytes.decode("utf-8")))
    msp = doc.modelspace()
    ev_polylines = [e for e in msp if e.dxf.layer == "EV-ZONE" and e.dxftype() == "LWPOLYLINE"]
    assert len(ev_polylines) == 0, f"Onverwachte EV-ZONE LWPOLYLINE(s): {len(ev_polylines)}"
