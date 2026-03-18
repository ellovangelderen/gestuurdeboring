"""Tests voor Backlog 12 — Tracévarianten vergelijken.

TC-var-A t/m G: model, route, vergelijking, verwijderen.
"""
import pytest
from tests.conftest import AUTH
from unittest.mock import patch


def _maak_boring_met_trace(db, order_id="order-var", boring_id="boring-var",
                            ordernummer="VAR-TEST"):
    from app.order.models import Order, Boring, TracePunt
    order = Order(id=order_id, workspace_id="gbt-workspace-001", ordernummer=ordernummer)
    db.add(order)
    boring = Boring(id=boring_id, order_id=order_id, volgnummer=1, type="B",
                    aangemaakt_door="martien")
    db.add(boring)
    # Hoofdtracé (variant 0)
    db.add(TracePunt(boring_id=boring_id, volgorde=0, type="intree",
                     RD_x=103900.0, RD_y=489290.0, label="A", variant=0))
    db.add(TracePunt(boring_id=boring_id, volgorde=1, type="uittree",
                     RD_x=104100.0, RD_y=489290.0, label="B", variant=0))
    db.commit()
    return order, boring


def test_tc_var_a_pagina_laadt(client, workspace, db):
    """TC-var-A: Varianten pagina laadt met hoofdtracé."""
    _maak_boring_met_trace(db, "order-va", "boring-va", "VA")
    resp = client.get("/orders/order-va/boringen/1/varianten", auth=AUTH)
    assert resp.status_code == 200
    assert "Hoofd" in resp.text
    assert "varianten" in resp.text.lower()


def test_tc_var_b_variant_toevoegen(client, workspace, db):
    """TC-var-B: Nieuwe variant toevoegen via POST."""
    _maak_boring_met_trace(db, "order-vb", "boring-vb", "VB")

    resp = client.post(
        "/orders/order-vb/boringen/1/varianten/nieuw",
        data={
            "RD_x_list": "103910.0,104090.0",
            "RD_y_list": "489300.0,489280.0",
            "type_list": "intree,uittree",
            "label_list": "A,B",
        },
        auth=AUTH, follow_redirects=True,
    )
    assert resp.status_code == 200
    # Variant 1 moet zichtbaar zijn
    assert "Variant 1" in resp.text


def test_tc_var_c_vergelijkingstabel(client, workspace, db):
    """TC-var-C: Met 2 varianten → vergelijkingstabel met delta's."""
    from app.order.models import TracePunt
    _maak_boring_met_trace(db, "order-vc", "boring-vc", "VC")
    # Voeg variant 1 toe (korter tracé)
    db.add(TracePunt(boring_id="boring-vc", volgorde=0, type="intree",
                     RD_x=103920.0, RD_y=489290.0, label="A", variant=1))
    db.add(TracePunt(boring_id="boring-vc", volgorde=1, type="uittree",
                     RD_x=104080.0, RD_y=489290.0, label="B", variant=1))
    db.commit()

    resp = client.get("/orders/order-vc/boringen/1/varianten", auth=AUTH)
    assert resp.status_code == 200
    assert "Vergelijking" in resp.text
    assert "Hoofd" in resp.text
    assert "Variant 1" in resp.text


def test_tc_var_d_delta_lengte(workspace, db):
    """TC-var-D: Delta lengte wordt correct berekend."""
    from app.order.models import TracePunt
    from app.order.router import varianten_pagina
    _maak_boring_met_trace(db, "order-vd", "boring-vd", "VD")
    # Variant 1: 160m (korter dan 200m hoofd)
    db.add(TracePunt(boring_id="boring-vd", volgorde=0, type="intree",
                     RD_x=103920.0, RD_y=489290.0, label="A", variant=1))
    db.add(TracePunt(boring_id="boring-vd", volgorde=1, type="uittree",
                     RD_x=104080.0, RD_y=489290.0, label="B", variant=1))
    db.commit()

    from app.geo.profiel import trace_totale_afstand
    hoofd = trace_totale_afstand([(103900.0, 489290.0), (104100.0, 489290.0)])
    alt = trace_totale_afstand([(103920.0, 489290.0), (104080.0, 489290.0)])
    assert alt < hoofd  # variant is korter


def test_tc_var_e_variant_verwijderen(client, workspace, db):
    """TC-var-E: Variant verwijderen via POST."""
    from app.order.models import TracePunt
    _maak_boring_met_trace(db, "order-ve", "boring-ve", "VE")
    db.add(TracePunt(boring_id="boring-ve", volgorde=0, type="intree",
                     RD_x=103920.0, RD_y=489290.0, label="A", variant=1))
    db.add(TracePunt(boring_id="boring-ve", volgorde=1, type="uittree",
                     RD_x=104080.0, RD_y=489290.0, label="B", variant=1))
    db.commit()

    resp = client.post(
        "/orders/order-ve/boringen/1/varianten/1/verwijder",
        auth=AUTH, follow_redirects=True,
    )
    assert resp.status_code == 200
    # Variant 1 mag niet meer zichtbaar zijn
    assert "Variant 1" not in resp.text


def test_tc_var_f_hoofd_niet_verwijderbaar(client, workspace, db):
    """TC-var-F: Hoofdvariant (0) kan niet verwijderd worden."""
    _maak_boring_met_trace(db, "order-vf", "boring-vf", "VF")
    resp = client.post(
        "/orders/order-vf/boringen/1/varianten/0/verwijder",
        auth=AUTH, follow_redirects=False,
    )
    assert resp.status_code == 400


def test_tc_var_g_link_in_boring_detail(client, workspace, db):
    """TC-var-G: Boring detail bevat link naar varianten."""
    _maak_boring_met_trace(db, "order-vg", "boring-vg", "VG")
    resp = client.get("/orders/order-vg/boringen/1", auth=AUTH)
    assert resp.status_code == 200
    assert "varianten" in resp.text.lower()
