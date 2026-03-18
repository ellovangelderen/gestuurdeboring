"""Tests voor Backlog 13 — Facturatie concept (SnelStart voorbereiding).

TC-fac-A t/m E: concept-factuur, regels, kopiëren.
"""
from tests.conftest import AUTH


def _maak_order_met_boringen(db, order_id="order-fac", ordernummer="FAC-TEST"):
    from app.order.models import Order, Boring, TracePunt
    order = Order(id=order_id, workspace_id="gbt-workspace-001",
                  ordernummer=ordernummer, locatie="Haarlem", klantcode="3D",
                  opdrachtgever="3D-Drilling BV")
    db.add(order)
    b1 = Boring(id=f"{order_id}-b1", order_id=order_id, volgnummer=1, type="B")
    b2 = Boring(id=f"{order_id}-b2", order_id=order_id, volgnummer=2, type="N")
    db.add(b1)
    db.add(b2)
    db.add(TracePunt(boring_id=b1.id, volgorde=0, type="intree",
                     RD_x=103900.0, RD_y=489290.0, label="A", variant=0))
    db.add(TracePunt(boring_id=b1.id, volgorde=1, type="uittree",
                     RD_x=104100.0, RD_y=489290.0, label="B", variant=0))
    db.commit()
    return order


def test_tc_fac_a_pagina_laadt(client, workspace, db):
    """TC-fac-A: Factuur concept pagina laadt."""
    _maak_order_met_boringen(db, "order-fa", "FA-TEST")
    resp = client.get("/orders/order-fa/factuur", auth=AUTH)
    assert resp.status_code == 200
    assert "Factuur" in resp.text


def test_tc_fac_b_klantgegevens(client, workspace, db):
    """TC-fac-B: Klantgegevens correct op factuur."""
    _maak_order_met_boringen(db, "order-fb", "FB-TEST")
    resp = client.get("/orders/order-fb/factuur", auth=AUTH)
    assert "3D-Drilling" in resp.text
    assert "FB-TEST" in resp.text


def test_tc_fac_c_factuurregels_per_boring(client, workspace, db):
    """TC-fac-C: Elke boring is een factuurregel."""
    _maak_order_met_boringen(db, "order-fc", "FC-TEST")
    resp = client.get("/orders/order-fc/factuur", auth=AUTH)
    assert "Gestuurde boring FC-TEST-01" in resp.text
    assert "Nano boring FC-TEST-02" in resp.text


def test_tc_fac_d_werkplan_regel(client, workspace, db):
    """TC-fac-D: Werkplan als apart factuuritem als er type B boringen zijn."""
    _maak_order_met_boringen(db, "order-fd", "FD-TEST")
    resp = client.get("/orders/order-fd/factuur", auth=AUTH)
    assert "Werkplan" in resp.text


def test_tc_fac_e_link_in_order_detail(client, workspace, db):
    """TC-fac-E: Order detail bevat link naar factuur."""
    _maak_order_met_boringen(db, "order-fe", "FE-TEST")
    resp = client.get("/orders/order-fe", auth=AUTH)
    assert "factuur" in resp.text.lower()
