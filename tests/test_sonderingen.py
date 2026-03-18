"""Tests voor Backlog 15 — Dinoloket sonderingen."""
from tests.conftest import AUTH


def _maak_boring(db, order_id, boring_id, ordernummer):
    from app.order.models import Order, Boring, TracePunt
    db.add(Order(id=order_id, workspace_id="gbt-workspace-001", ordernummer=ordernummer))
    db.add(Boring(id=boring_id, order_id=order_id, volgnummer=1, type="B"))
    db.add(TracePunt(boring_id=boring_id, volgorde=0, type="intree",
                     RD_x=103896.9, RD_y=489289.5, label="A", variant=0))
    db.add(TracePunt(boring_id=boring_id, volgorde=1, type="uittree",
                     RD_x=104118.8, RD_y=489243.7, label="B", variant=0))
    db.commit()


def test_pagina_laadt(client, workspace, db):
    _maak_boring(db, "order-so-a", "boring-so-a", "SOA")
    resp = client.get("/orders/order-so-a/boringen/1/sonderingen", auth=AUTH)
    assert resp.status_code == 200
    assert "Sonderingen" in resp.text


def test_dinoloket_link(client, workspace, db):
    _maak_boring(db, "order-so-b", "boring-so-b", "SOB")
    resp = client.get("/orders/order-so-b/boringen/1/sonderingen", auth=AUTH)
    assert "dinoloket.nl" in resp.text


def test_werkwijze_aanwezig(client, workspace, db):
    _maak_boring(db, "order-so-c", "boring-so-c", "SOC")
    resp = client.get("/orders/order-so-c/boringen/1/sonderingen", auth=AUTH)
    assert "Werkwijze" in resp.text


def test_link_in_brondata(client, workspace, db):
    _maak_boring(db, "order-so-d", "boring-so-d", "SOD")
    resp = client.get("/orders/order-so-d/boringen/1/brondata", auth=AUTH)
    assert "sonderingen" in resp.text.lower()
