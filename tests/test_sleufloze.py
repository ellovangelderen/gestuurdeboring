"""Tests voor Backlog 6 — Sleufloze leidingen detectie scherm.

TC-sl-A t/m G: route, categorisatie, detectieregels, UI.
"""
import pytest
from datetime import datetime, timezone

from tests.conftest import AUTH


def _maak_boring_met_klic(db, order_id, boring_id, ordernummer, leidingen):
    """Helper: maak order + boring + KLIC upload + leidingen."""
    from app.order.models import Order, Boring, KLICUpload, KLICLeiding

    order = Order(id=order_id, workspace_id="gbt-workspace-001", ordernummer=ordernummer)
    db.add(order)
    boring = Boring(id=boring_id, order_id=order_id, volgnummer=1, type="B")
    db.add(boring)
    upload = KLICUpload(
        id=f"upload-{order_id}", order_id=order_id, bestandsnaam="test.zip",
        bestandspad="/tmp/test.zip", verwerkt=True,
        verwerkt_op=datetime.now(timezone.utc),
    )
    db.add(upload)
    for i, l in enumerate(leidingen):
        db.add(KLICLeiding(
            id=f"l-{order_id}-{i}",
            klic_upload_id=upload.id,
            beheerder=l.get("beheerder", "TestBeheerder"),
            leidingtype=l.get("leidingtype", "Kabel"),
            geometrie_wkt="LINESTRING(0 0, 1 1)",
            sleufloze_techniek=l.get("sleufloze", False),
            mogelijk_sleufloze=l.get("mogelijk", False),
            diepte_m=l.get("diepte_m"),
            diepte_bron=l.get("diepte_bron"),
            label_tekst=l.get("label_tekst"),
            dxf_laag="LAAGSPANNING",
        ))
    db.commit()


def test_tc_sl_a_pagina_zonder_klic(client, workspace, db):
    """TC-sl-A: Sleufloze pagina zonder KLIC → melding."""
    from app.order.models import Order, Boring
    db.add(Order(id="order-sl-a", workspace_id="gbt-workspace-001", ordernummer="SL-A"))
    db.add(Boring(id="boring-sl-a", order_id="order-sl-a", volgnummer=1, type="B"))
    db.commit()

    resp = client.get("/orders/order-sl-a/boringen/1/sleufloze", auth=AUTH)
    assert resp.status_code == 200
    assert "KLIC" in resp.text


def test_tc_sl_b_geen_sleufloze(client, workspace, db):
    """TC-sl-B: KLIC zonder sleufloze → groene melding."""
    _maak_boring_met_klic(db, "order-sl-b", "boring-sl-b", "SL-B", [
        {"beheerder": "Liander", "leidingtype": "LS kabel", "sleufloze": False},
    ])
    resp = client.get("/orders/order-sl-b/boringen/1/sleufloze", auth=AUTH)
    assert resp.status_code == 200
    assert "Geen sleufloze" in resp.text


def test_tc_sl_c_sleufloze_gedetecteerd(client, workspace, db):
    """TC-sl-C: Sleufloze leidingen worden getoond in rode sectie."""
    _maak_boring_met_klic(db, "order-sl-c", "boring-sl-c", "SL-C", [
        {"beheerder": "Reggefiber", "leidingtype": "Mantelbuis", "sleufloze": True,
         "label_tekst": "PE mantelbuis"},
        {"beheerder": "Liander", "leidingtype": "LS kabel", "sleufloze": False},
    ])
    resp = client.get("/orders/order-sl-c/boringen/1/sleufloze", auth=AUTH)
    assert resp.status_code == 200
    assert "Reggefiber" in resp.text
    assert "Sleufloze techniek gedetecteerd" in resp.text


def test_tc_sl_d_mogelijk_sleufloze(client, workspace, db):
    """TC-sl-D: Mogelijk sleufloze (staal) wordt in gele sectie getoond."""
    _maak_boring_met_klic(db, "order-sl-d", "boring-sl-d", "SL-D", [
        {"beheerder": "Gasunie", "leidingtype": "Hogedruk gas", "mogelijk": True,
         "label_tekst": "Staal"},
    ])
    resp = client.get("/orders/order-sl-d/boringen/1/sleufloze", auth=AUTH)
    assert resp.status_code == 200
    assert "Mogelijk sleufloze" in resp.text
    assert "Gasunie" in resp.text


def test_tc_sl_e_stats_correct(client, workspace, db):
    """TC-sl-E: Stats-balk toont correcte tellingen."""
    _maak_boring_met_klic(db, "order-sl-e", "boring-sl-e", "SL-E", [
        {"beheerder": "A", "sleufloze": True},
        {"beheerder": "B", "sleufloze": True},
        {"beheerder": "C", "mogelijk": True},
        {"beheerder": "D"},
        {"beheerder": "E"},
    ])
    resp = client.get("/orders/order-sl-e/boringen/1/sleufloze", auth=AUTH)
    html = resp.text
    # Totaal 5, sleufloze 2, mogelijk 1
    assert ">5<" in html  # totaal
    assert ">2<" in html  # sleufloze
    assert ">1<" in html  # mogelijk


def test_tc_sl_f_detectieregels_zichtbaar(client, workspace, db):
    """TC-sl-F: Detectieregels zijn zichtbaar (inklapbaar)."""
    _maak_boring_met_klic(db, "order-sl-f", "boring-sl-f", "SL-F", [])
    resp = client.get("/orders/order-sl-f/boringen/1/sleufloze", auth=AUTH)
    assert "Detectieregels" in resp.text
    assert "PE" in resp.text
    assert "Staal" in resp.text


def test_tc_sl_g_link_in_brondata(client, workspace, db):
    """TC-sl-G: Brondata pagina bevat link naar sleufloze."""
    from app.order.models import Order, Boring
    db.add(Order(id="order-sl-g", workspace_id="gbt-workspace-001", ordernummer="SL-G"))
    db.add(Boring(id="boring-sl-g", order_id="order-sl-g", volgnummer=1, type="B"))
    db.commit()
    resp = client.get("/orders/order-sl-g/boringen/1/brondata", auth=AUTH)
    assert "sleufloze" in resp.text.lower()
