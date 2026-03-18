"""TC-order — Module 2: Order + Boring CRUD"""
import pytest

from tests.conftest import AUTH


# TC-order-A: Order aanmaken met boring → opgeslagen, redirect naar detail
def test_order_a_aanmaken(client, workspace):
    resp = client.post(
        "/orders/nieuw",
        data={
            "ordernummer": "3D25V700",
            "locatie": "Haarlem, Kennemerplein",
            "klantcode": "3D",
            "type_1": "B",
            "aantal_1": "1",
        },
        auth=AUTH,
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "3D25V700" in resp.text


# TC-order-B: SDR=11, De=160 → dn_berekend=14.5, Di≈131.0
def test_order_b_dn_berekening():
    from app.order.models import Boring
    b = Boring(order_id="x", volgnummer=1, type="B", SDR=11, De_mm=160.0)
    assert b.dn_berekend == 14.5
    # Di = 160 - 2 * 14.5 = 131.0
    assert b.Di_mm == 131.0


# TC-order-C: HDD11 — dn=14.6 conform BerekeningHDD11 p.5
def test_order_c_dn_handmatig_hdd11():
    from app.order.models import Boring
    b = Boring(order_id="x", volgnummer=1, type="B", SDR=11, De_mm=160.0, dn_mm=14.6)
    assert b.dn_effectief == 14.6
    assert b.Di_mm == pytest.approx(160.0 - 2 * 14.6, abs=0.01)


# TC-order-D: Verplicht veld 'ordernummer' leeg → validatiefout (400)
def test_order_d_ordernummer_verplicht(client, workspace):
    resp = client.post(
        "/orders/nieuw",
        data={"ordernummer": ""},
        auth=AUTH,
        follow_redirects=False,
    )
    assert resp.status_code in (422, 400)


# TC-order-E: Orderlijst toont alle orders van workspace
def test_order_e_lijst(client, workspace):
    # Maak 2 orders
    for nr in ["ORD-001", "ORD-002"]:
        client.post(
            "/orders/nieuw",
            data={"ordernummer": nr, "type_1": "B", "aantal_1": "1"},
            auth=AUTH,
            follow_redirects=True,
        )

    resp = client.get("/orders/", auth=AUTH)
    assert resp.status_code == 200
    assert "ORD-001" in resp.text
    assert "ORD-002" in resp.text


# TC-order-F: Meerdere boringen per order
def test_order_f_meerdere_boringen(client, db, workspace):
    resp = client.post(
        "/orders/nieuw",
        data={
            "ordernummer": "3D25V701",
            "type_1": "B",
            "aantal_1": "2",
            "type_2": "Z",
            "aantal_2": "1",
        },
        auth=AUTH,
        follow_redirects=True,
    )
    assert resp.status_code == 200

    from app.order.models import Order, Boring
    db.expire_all()
    order = db.query(Order).filter_by(ordernummer="3D25V701").first()
    assert order is not None
    boringen = db.query(Boring).filter_by(order_id=order.id).order_by(Boring.volgnummer).all()
    assert len(boringen) == 3
    assert boringen[0].type == "B"
    assert boringen[1].type == "B"
    assert boringen[2].type == "Z"
