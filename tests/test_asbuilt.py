"""Tests voor Backlog 18 — As-Built revisietekeningen."""
from tests.conftest import AUTH


def _maak_boring(db, order_id="order-ab", boring_id="boring-ab", ordernummer="AB-TEST"):
    from app.order.models import Order, Boring, TracePunt
    order = Order(id=order_id, workspace_id="gbt-workspace-001", ordernummer=ordernummer)
    db.add(order)
    boring = Boring(id=boring_id, order_id=order_id, volgnummer=1, type="B")
    db.add(boring)
    db.add(TracePunt(boring_id=boring_id, volgorde=0, type="intree",
                     RD_x=103900.0, RD_y=489290.0, label="A", variant=0))
    db.add(TracePunt(boring_id=boring_id, volgorde=1, type="uittree",
                     RD_x=104100.0, RD_y=489290.0, label="B", variant=0))
    db.commit()
    return order, boring


def test_pagina_laadt(client, workspace, db):
    _maak_boring(db, "order-ab-a", "boring-ab-a", "ABA")
    resp = client.get("/orders/order-ab-a/boringen/1/asbuilt", auth=AUTH)
    assert resp.status_code == 200
    assert "As-Built" in resp.text


def test_asbuilt_opslaan(client, workspace, db):
    _maak_boring(db, "order-ab-b", "boring-ab-b", "ABB")
    resp = client.post(
        "/orders/order-ab-b/boringen/1/asbuilt",
        data={"RD_x_list": "103901.0,104099.0", "RD_y_list": "489291.0,489289.0",
              "label_list": "A,B"},
        auth=AUTH, follow_redirects=True,
    )
    assert resp.status_code == 200
    from app.order.models import Boring
    db.expire_all()
    boring = db.query(Boring).get("boring-ab-b")
    assert boring.revisie == 1
    assert len(boring.asbuilt_punten) == 2


def test_revisie_ophogen(client, workspace, db):
    _maak_boring(db, "order-ab-c", "boring-ab-c", "ABC")
    # Eerste keer
    client.post("/orders/order-ab-c/boringen/1/asbuilt",
                data={"RD_x_list": "103901.0,104099.0", "RD_y_list": "489291.0,489289.0",
                      "label_list": "A,B"}, auth=AUTH, follow_redirects=True)
    # Tweede keer
    client.post("/orders/order-ab-c/boringen/1/asbuilt",
                data={"RD_x_list": "103902.0,104098.0", "RD_y_list": "489292.0,489288.0",
                      "label_list": "A,B"}, auth=AUTH, follow_redirects=True)
    from app.order.models import Boring
    db.expire_all()
    boring = db.query(Boring).get("boring-ab-c")
    assert boring.revisie == 2


def test_afwijking_berekend(client, workspace, db):
    from app.order.models import AsBuiltPunt
    _maak_boring(db, "order-ab-d", "boring-ab-d", "ABD")
    db.add(AsBuiltPunt(boring_id="boring-ab-d", volgorde=0, label="A",
                        RD_x=103901.0, RD_y=489291.0))
    db.add(AsBuiltPunt(boring_id="boring-ab-d", volgorde=1, label="B",
                        RD_x=104099.0, RD_y=489289.0))
    db.commit()

    resp = client.get("/orders/order-ab-d/boringen/1/asbuilt", auth=AUTH)
    assert resp.status_code == 200
    assert "Afwijking" in resp.text


def test_link_in_boring_detail(client, workspace, db):
    _maak_boring(db, "order-ab-e", "boring-ab-e", "ABE")
    resp = client.get("/orders/order-ab-e/boringen/1", auth=AUTH)
    assert "asbuilt" in resp.text.lower() or "As-Built" in resp.text
