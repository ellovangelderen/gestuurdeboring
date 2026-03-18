"""Tests voor Backlog 11 — Topotijdreis historische kaarten.

TC-tt-A t/m F: route, kaartviewer, link-out, jaren.
"""
import pytest
from tests.conftest import AUTH


def _maak_boring_met_trace(db, order_id="order-tt", boring_id="boring-tt",
                            ordernummer="TT-TEST"):
    """Helper: maak order + boring + tracepunten."""
    from app.order.models import Order, Boring, TracePunt
    order = Order(id=order_id, workspace_id="gbt-workspace-001", ordernummer=ordernummer)
    db.add(order)
    boring = Boring(id=boring_id, order_id=order_id, volgnummer=1, type="B",
                    aangemaakt_door="martien")
    db.add(boring)
    db.add(TracePunt(boring_id=boring_id, volgorde=0, type="intree",
                     RD_x=103896.9, RD_y=489289.5, label="A"))
    db.add(TracePunt(boring_id=boring_id, volgorde=1, type="uittree",
                     RD_x=104118.8, RD_y=489243.7, label="B"))
    db.commit()
    return order, boring


def test_tc_tt_a_pagina_met_trace(client, workspace, db):
    """TC-tt-A: Topotijdreis pagina laadt met tracepunten."""
    _maak_boring_met_trace(db, "order-tt-a", "boring-tt-a", "TT-A")
    resp = client.get("/orders/order-tt-a/boringen/1/topotijdreis", auth=AUTH)
    assert resp.status_code == 200
    assert "Topotijdreis" in resp.text
    assert "jaar-slider" in resp.text


def test_tc_tt_b_pagina_zonder_trace(client, workspace, db):
    """TC-tt-B: Topotijdreis pagina zonder trace → melding."""
    from app.order.models import Order, Boring
    db.add(Order(id="order-tt-b", workspace_id="gbt-workspace-001", ordernummer="TT-B"))
    db.add(Boring(id="boring-tt-b", order_id="order-tt-b", volgnummer=1, type="B"))
    db.commit()

    resp = client.get("/orders/order-tt-b/boringen/1/topotijdreis", auth=AUTH)
    assert resp.status_code == 200
    assert "tracépunten" in resp.text.lower() or "trac" in resp.text.lower()


def test_tc_tt_c_linkout_topotijdreis(client, workspace, db):
    """TC-tt-C: Pagina bevat link naar topotijdreis.nl."""
    _maak_boring_met_trace(db, "order-tt-c", "boring-tt-c", "TT-C")
    resp = client.get("/orders/order-tt-c/boringen/1/topotijdreis", auth=AUTH)
    assert "topotijdreis.nl" in resp.text


def test_tc_tt_d_jaren_in_slider(client, workspace, db):
    """TC-tt-D: Pagina bevat historische jaren voor de slider."""
    _maak_boring_met_trace(db, "order-tt-d", "boring-tt-d", "TT-D")
    resp = client.get("/orders/order-tt-d/boringen/1/topotijdreis", auth=AUTH)
    # Moet jaren bevatten
    assert "1900" in resp.text
    assert "1950" in resp.text
    assert "2015" in resp.text


def test_tc_tt_e_arcgis_tile_url(client, workspace, db):
    """TC-tt-E: Pagina bevat ArcGIS tile URL voor historische kaarten."""
    _maak_boring_met_trace(db, "order-tt-e", "boring-tt-e", "TT-E")
    resp = client.get("/orders/order-tt-e/boringen/1/topotijdreis", auth=AUTH)
    assert "tiles.arcgis.com" in resp.text
    assert "Historische_tijdreis" in resp.text


def test_tc_tt_f_link_in_brondata(client, workspace, db):
    """TC-tt-F: Brondata pagina bevat link naar topotijdreis."""
    _maak_boring_met_trace(db, "order-tt-f", "boring-tt-f", "TT-F")
    resp = client.get("/orders/order-tt-f/boringen/1/brondata", auth=AUTH)
    assert "topotijdreis" in resp.text.lower()


def test_tc_tt_g_afspeel_knop(client, workspace, db):
    """TC-tt-G: Pagina bevat afspeel-knop voor animatie."""
    _maak_boring_met_trace(db, "order-tt-g", "boring-tt-g", "TT-G")
    resp = client.get("/orders/order-tt-g/boringen/1/topotijdreis", auth=AUTH)
    assert "Afspelen" in resp.text


@pytest.mark.external
def test_tc_tt_ext_a_arcgis_tile_bereikbaar():
    """TC-tt-ext-A: ArcGIS tile service is bereikbaar voor jaar 1900."""
    import httpx
    resp = httpx.get(
        "https://tiles.arcgis.com/tiles/nSZVuSZjHpEZZbRo/arcgis/rest/services/Historische_tijdreis_1900/MapServer?f=json",
        timeout=10,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "tileInfo" in data
