"""Tests voor Backlog 14 — Vergunningscheck omgevingswet."""
from tests.conftest import AUTH


def _maak_boring(db, order_id="order-vg", boring_id="boring-vg", ordernummer="VG-TEST"):
    from app.order.models import Order, Boring, TracePunt
    order = Order(id=order_id, workspace_id="gbt-workspace-001", ordernummer=ordernummer)
    db.add(order)
    boring = Boring(id=boring_id, order_id=order_id, volgnummer=1, type="B")
    db.add(boring)
    db.add(TracePunt(boring_id=boring_id, volgorde=0, type="intree",
                     RD_x=103896.9, RD_y=489289.5, label="A", variant=0))
    db.add(TracePunt(boring_id=boring_id, volgorde=1, type="uittree",
                     RD_x=104118.8, RD_y=489243.7, label="B", variant=0))
    db.commit()
    return order


def test_pagina_laadt(client, workspace, db):
    _maak_boring(db, "order-vg-a", "boring-vg-a", "VGA")
    resp = client.get("/orders/order-vg-a/boringen/1/vergunning", auth=AUTH)
    assert resp.status_code == 200
    assert "Vergunningscheck" in resp.text


def test_omgevingsloket_link(client, workspace, db):
    _maak_boring(db, "order-vg-b", "boring-vg-b", "VGB")
    resp = client.get("/orders/order-vg-b/boringen/1/vergunning", auth=AUTH)
    assert "omgevingswet.overheid.nl" in resp.text


def test_pdok_link(client, workspace, db):
    _maak_boring(db, "order-vg-c", "boring-vg-c", "VGC")
    resp = client.get("/orders/order-vg-c/boringen/1/vergunning", auth=AUTH)
    assert "app.pdok.nl" in resp.text


def test_bodemloket_link(client, workspace, db):
    _maak_boring(db, "order-vg-d", "boring-vg-d", "VGD")
    resp = client.get("/orders/order-vg-d/boringen/1/vergunning", auth=AUTH)
    assert "bodemloket" in resp.text.lower()


def test_checklist_aanwezig(client, workspace, db):
    _maak_boring(db, "order-vg-e", "boring-vg-e", "VGE")
    resp = client.get("/orders/order-vg-e/boringen/1/vergunning", auth=AUTH)
    assert "checkbox" in resp.text


def test_zonder_trace(client, workspace, db):
    from app.order.models import Order, Boring
    db.add(Order(id="order-vg-f", workspace_id="gbt-workspace-001", ordernummer="VGF"))
    db.add(Boring(id="boring-vg-f", order_id="order-vg-f", volgnummer=1, type="B"))
    db.commit()
    resp = client.get("/orders/order-vg-f/boringen/1/vergunning", auth=AUTH)
    assert resp.status_code == 200
    assert "intree" in resp.text.lower()


def test_link_in_brondata(client, workspace, db):
    _maak_boring(db, "order-vg-g", "boring-vg-g", "VGG")
    resp = client.get("/orders/order-vg-g/boringen/1/brondata", auth=AUTH)
    assert "vergunning" in resp.text.lower()
