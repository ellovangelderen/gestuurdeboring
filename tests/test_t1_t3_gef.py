"""Tests voor T1 (CSV export), T2 (AutoCAD script), T3 (bocht check), 16 (GEF parser)."""
import pytest
from tests.conftest import AUTH


def _maak_boring(db, order_id="order-t", boring_id="boring-t", ordernummer="T-TEST"):
    from app.order.models import Order, Boring, TracePunt
    db.add(Order(id=order_id, workspace_id="gbt-workspace-001", ordernummer=ordernummer))
    boring = Boring(id=boring_id, order_id=order_id, volgnummer=1, type="B",
                    naam="HDD1", aangemaakt_door="martien")
    db.add(boring)
    db.add(TracePunt(boring_id=boring_id, volgorde=0, type="intree",
                     RD_x=103900.0, RD_y=489290.0, label="A", variant=0))
    db.add(TracePunt(boring_id=boring_id, volgorde=1, type="tussenpunt",
                     RD_x=104000.0, RD_y=489280.0, label="Th1", variant=0, Rh_m=150.0))
    db.add(TracePunt(boring_id=boring_id, volgorde=2, type="uittree",
                     RD_x=104100.0, RD_y=489270.0, label="B", variant=0))
    db.commit()


# ── T1: CSV GPS export ──

def test_t1_csv_download(client, workspace, db):
    _maak_boring(db, "order-t1", "boring-t1", "T1")
    resp = client.get("/orders/order-t1/boringen/1/csv", auth=AUTH)
    assert resp.status_code == 200
    assert ".csv" in resp.headers.get("Content-Disposition", "")
    content = resp.text
    assert "SENSORPUNTEN" in content
    assert "BOORLIJN" in content
    assert "103900" in content


def test_t1_csv_interval(client, workspace, db):
    _maak_boring(db, "order-t1b", "boring-t1b", "T1B")
    resp = client.get("/orders/order-t1b/boringen/1/csv?interval=5", auth=AUTH)
    lines = resp.text.strip().split("\n")
    # Meer dan alleen sensorpunten
    assert len(lines) > 10


# ── T2: AutoCAD script ──

def test_t2_scr_download(client, workspace, db):
    _maak_boring(db, "order-t2", "boring-t2", "T2")
    resp = client.get("/orders/order-t2/boringen/1/scr", auth=AUTH)
    assert resp.status_code == 200
    assert ".scr" in resp.headers.get("Content-Disposition", "")
    content = resp.text
    assert "_PLINE" in content
    assert "_LAYER" in content
    assert "BOORLIJN" in content
    assert "103900" in content


def test_t2_scr_bevat_labels(client, workspace, db):
    _maak_boring(db, "order-t2b", "boring-t2b", "T2B")
    resp = client.get("/orders/order-t2b/boringen/1/scr", auth=AUTH)
    assert "_TEXT" in resp.text
    assert "Aboorgat" in resp.text  # INSERT intree symbool


# ── T3: Horizontale bocht check ──

def test_t3_rechte_lijn_geen_waarschuwing():
    from app.geo.bocht_check import check_bochten
    coords = [(0, 0), (100, 0), (200, 0)]  # recht
    result = check_bochten(coords, [None, None, None])
    assert len(result) == 0


def test_t3_scherpe_bocht_waarschuwing():
    from app.geo.bocht_check import check_bochten
    coords = [(0, 0), (100, 0), (100, 100)]  # 90° bocht
    result = check_bochten(coords, [None, None, None])
    assert len(result) >= 1
    assert result[0]["afbuiging_gr"] == pytest.approx(90.0, abs=1)


def test_t3_bocht_met_rh_te_klein():
    from app.geo.bocht_check import check_bochten
    coords = [(0, 0), (100, 0), (150, 50)]  # ~45° bocht
    result = check_bochten(coords, [None, 50.0, None], Rv_min=100.0)
    assert len(result) >= 1
    assert result[0].get("te_scherp") is True


# ── 16: GEF parser ──

def test_gef_parse_minimal():
    from app.geo.gef_parser import parse_gef
    gef = """#TESTID= CPT-001
#STARTDATE= 2025, 1, 15
#XYID= 28992, 103900.0, 489290.0
#ZID= 31000, 1.50
#COLUMNINFO= 1, m, sondeerlengte, 1
#COLUMNINFO= 2, MPa, conusweerstand, 2
#COLUMNINFO= 3, kPa, kleefweerstand, 3
#EOH=
0.10 2.5 25.0
0.20 3.0 30.0
0.30 5.0 20.0
1.00 8.0 40.0
2.00 12.0 60.0
"""
    result = parse_gef(gef)
    assert result.naam == "CPT-001"
    assert result.rd_x == pytest.approx(103900.0)
    assert result.z_nap == pytest.approx(1.50)
    assert len(result.meetpunten) == 5
    assert result.meetpunten[0].diepte_m == pytest.approx(0.10)
    assert result.meetpunten[0].qc_MPa == pytest.approx(2.5)
    assert result.max_diepte == pytest.approx(2.0)


def test_gef_parse_leeg():
    from app.geo.gef_parser import parse_gef
    result = parse_gef("")
    assert result.naam == ""
    assert len(result.meetpunten) == 0
