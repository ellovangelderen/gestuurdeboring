"""Tests voor Backlog 5 — GWSW riool BOB + gemeente-mail.

TC-gwsw-A t/m I: API client, route, gemeente-mail, UI.
"""
import pytest
from unittest.mock import patch, MagicMock

from tests.conftest import AUTH


def _maak_boring_met_trace(db, order_id="order-gw", boring_id="boring-gw",
                            ordernummer="GW-TEST"):
    from app.order.models import Order, Boring, TracePunt
    order = Order(id=order_id, workspace_id="gbt-workspace-001",
                  ordernummer=ordernummer, locatie="Haarlem Kennemerplein")
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


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT TESTS — GWSW client
# ═══════════════════════════════════════════════════════════════════════════════

def test_tc_gwsw_a_parse_rioolleiding():
    """TC-gwsw-A: RioolLeiding dataclass werkt correct."""
    from app.geo.gwsw import RioolLeiding
    l = RioolLeiding(
        naam="R001", bob_begin=8.55, bob_eind=8.50,
        materiaal="PVC", stelseltype="GemengdRiool",
        hoogte_mm=300.0, dataset="https://apps.gwsw.nl/item_config?dataset=Haarlem",
        geometrie_wkt=None,
    )
    assert l.heeft_bob is True
    assert l.gemeente == "Haarlem"


def test_tc_gwsw_b_zonder_bob():
    """TC-gwsw-B: RioolLeiding zonder BOB → heeft_bob is False."""
    from app.geo.gwsw import RioolLeiding
    l = RioolLeiding(
        naam="R002", bob_begin=None, bob_eind=None,
        materiaal="", stelseltype="", hoogte_mm=None,
        dataset="https://apps.gwsw.nl/item_config?dataset=Amsterdam",
        geometrie_wkt=None,
    )
    assert l.heeft_bob is False
    assert l.gemeente == "Amsterdam"


def test_tc_gwsw_c_mock_api_succes():
    """TC-gwsw-C: haal_riooldata_op met gemockte PDOK response."""
    from app.geo.gwsw import haal_riooldata_op

    mock_json = {
        "type": "FeatureCollection",
        "numberReturned": 1,
        "features": [{
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[4.63, 52.38], [4.631, 52.38]]},
            "properties": {
                "naam": "R100",
                "bob_beginpunt_leiding": 0.55,
                "bob_eindpunt_leiding": 0.50,
                "materiaal_leiding": "http://data.gwsw.nl/1.6/totaal/PVC",
                "stelseltype": "http://data.gwsw.nl/1.6/totaal/GemengdRiool",
                "hoogte_leiding": 300,
                "dataset": "https://apps.gwsw.nl/item_config?dataset=TestGemeente",
            },
        }],
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = mock_json

    with patch("app.geo.gwsw.httpx.get", return_value=mock_resp):
        result = haal_riooldata_op(103896.9, 489289.5)

    assert len(result) == 1
    assert result[0].naam == "R100"
    assert result[0].bob_begin == 0.55
    assert result[0].materiaal == "PVC"
    assert result[0].gemeente == "TestGemeente"


def test_tc_gwsw_d_api_timeout():
    """TC-gwsw-D: haal_riooldata_op timeout → lege lijst, geen crash."""
    import httpx
    from app.geo.gwsw import haal_riooldata_op

    with patch("app.geo.gwsw.httpx.get", side_effect=httpx.TimeoutException("timeout")):
        result = haal_riooldata_op(103896.9, 489289.5)
    assert result == []


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTE + UI TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_tc_gwsw_e_pagina_zonder_trace(client, workspace, db):
    """TC-gwsw-E: GWSW pagina zonder trace → melding."""
    from app.order.models import Order, Boring
    db.add(Order(id="order-gw-e", workspace_id="gbt-workspace-001", ordernummer="GW-E"))
    db.add(Boring(id="boring-gw-e", order_id="order-gw-e", volgnummer=1, type="B"))
    db.commit()

    resp = client.get("/orders/order-gw-e/boringen/1/gwsw", auth=AUTH)
    assert resp.status_code == 200
    assert "intree" in resp.text.lower() or "trac" in resp.text.lower()


def test_tc_gwsw_f_pagina_geen_data(client, workspace, db):
    """TC-gwsw-F: GWSW pagina met trace maar geen riooldata → gemeente-mail."""
    _maak_boring_met_trace(db, "order-gw-f", "boring-gw-f", "GW-F")

    with patch("app.geo.gwsw.haal_riooldata_op", return_value=[]):
        resp = client.get("/orders/order-gw-f/boringen/1/gwsw", auth=AUTH)

    assert resp.status_code == 200
    assert "Geen riooldata" in resp.text or "gemeente" in resp.text.lower()
    # Gemeente-mail moet verschijnen
    assert "BOB-gegevens" in resp.text


def test_tc_gwsw_g_pagina_met_bob(client, workspace, db):
    """TC-gwsw-G: GWSW pagina met BOB data → tabel met waarden."""
    from app.geo.gwsw import RioolLeiding
    _maak_boring_met_trace(db, "order-gw-g", "boring-gw-g", "GW-G")

    mock_data = [
        RioolLeiding(naam="R200", bob_begin=0.55, bob_eind=0.50, materiaal="PVC",
                     stelseltype="GemengdRiool", hoogte_mm=300, dataset="dataset=Haarlem",
                     geometrie_wkt=None),
    ]

    with patch("app.geo.gwsw.haal_riooldata_op", return_value=mock_data):
        resp = client.get("/orders/order-gw-g/boringen/1/gwsw", auth=AUTH)

    assert resp.status_code == 200
    assert "0.55" in resp.text
    assert "PVC" in resp.text


def test_tc_gwsw_h_gemeente_mail_bevat_coordinaten(client, workspace, db):
    """TC-gwsw-H: Gemeente-mail bevat RD-coördinaten en locatie."""
    _maak_boring_met_trace(db, "order-gw-h", "boring-gw-h", "GW-H")

    with patch("app.geo.gwsw.haal_riooldata_op", return_value=[]):
        resp = client.get("/orders/order-gw-h/boringen/1/gwsw", auth=AUTH)

    assert "103896" in resp.text  # RD X
    assert "489289" in resp.text  # RD Y
    assert "Martien Luijben" in resp.text


def test_tc_gwsw_i_link_in_brondata(client, workspace, db):
    """TC-gwsw-I: Brondata pagina bevat link naar GWSW."""
    _maak_boring_met_trace(db, "order-gw-i", "boring-gw-i", "GW-I")
    resp = client.get("/orders/order-gw-i/boringen/1/brondata", auth=AUTH)
    assert "gwsw" in resp.text.lower()


@pytest.mark.external
def test_tc_gwsw_ext_a_pdok_api_bereikbaar():
    """TC-gwsw-ext-A: PDOK GWSW OGC API is bereikbaar."""
    import httpx
    resp = httpx.get(
        "https://api.pdok.nl/rioned/beheer-stedelijk-watersystemen-gwsw/ogc/v1/collections?f=json",
        timeout=10,
    )
    assert resp.status_code == 200
    data = resp.json()
    collections = [c["id"] for c in data.get("collections", [])]
    assert "beheerleiding" in collections
