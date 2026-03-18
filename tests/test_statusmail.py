"""Tests voor Backlog 4 — Statusmail concepten (kopieerbaar).

TC-sm-A t/m H: generatie, groepering, mailtekst, pagina.
"""
import pytest
from tests.conftest import AUTH


def _maak_orders(db):
    """Helper: maak orders met verschillende statussen en klanten."""
    from app.order.models import Order, Boring

    orders = [
        Order(id="order-sm-1", workspace_id="gbt-workspace-001", ordernummer="3D25V700",
              klantcode="3D", opdrachtgever="3D-Drilling BV", locatie="Haarlem",
              status="waiting_for_approval"),
        Order(id="order-sm-2", workspace_id="gbt-workspace-001", ordernummer="3D25V701",
              klantcode="3D", opdrachtgever="3D-Drilling BV", locatie="Amsterdam",
              status="delivered"),
        Order(id="order-sm-3", workspace_id="gbt-workspace-001", ordernummer="RD25V100",
              klantcode="RD", opdrachtgever="R&D Drilling", locatie="Utrecht",
              status="waiting_for_approval"),
        Order(id="order-sm-4", workspace_id="gbt-workspace-001", ordernummer="3D25V702",
              klantcode="3D", opdrachtgever="3D-Drilling BV", locatie="Leiden",
              status="done"),  # afgerond — niet in statusmail
        Order(id="order-sm-5", workspace_id="gbt-workspace-001", ordernummer="IE25V200",
              klantcode="IE", opdrachtgever="Infra Elite", locatie="Den Haag",
              status="in_progress"),  # in uitvoering — niet in statusmail
    ]
    for o in orders:
        db.add(o)
        db.add(Boring(order_id=o.id, volgnummer=1, type="B"))
    db.commit()
    return orders


def test_tc_sm_a_pagina_laadt(client, workspace, db):
    """TC-sm-A: Statusmail pagina laadt zonder errors."""
    resp = client.get("/orders/statusmail", auth=AUTH)
    assert resp.status_code == 200
    assert "Statusmail" in resp.text


def test_tc_sm_b_groepering_per_klant(client, workspace, db):
    """TC-sm-B: Orders worden gegroepeerd per klantcode."""
    _maak_orders(db)
    resp = client.get("/orders/statusmail", auth=AUTH)
    assert resp.status_code == 200
    # 3D, RD en IE moeten verschijnen (alle actieve statussen)
    assert "3D-Drilling" in resp.text
    assert "R&amp;D Drilling" in resp.text or "R&D Drilling" in resp.text
    assert "Infra Elite" in resp.text


def test_tc_sm_c_alle_actieve_statussen(workspace, db):
    """TC-sm-C: Alle actieve orders zitten in concepten, maar niet done/cancelled."""
    from app.order.router import _genereer_statusmail_concepten
    orders = _maak_orders(db)
    concepten = _genereer_statusmail_concepten(orders)

    alle_orders_in_concepten = []
    for c in concepten:
        alle_orders_in_concepten.extend(c["wacht_akkoord"])
        alle_orders_in_concepten.extend(c["geleverd"])
        alle_orders_in_concepten.extend(c["in_uitvoering"])
        alle_orders_in_concepten.extend(c["ontvangen"])

    statussen = {o.status for o in alle_orders_in_concepten}
    # Actieve statussen mogen erin
    assert statussen <= {"order_received", "in_progress", "waiting_for_approval", "delivered"}
    # 'done' mag er niet in zitten
    assert "done" not in statussen


def test_tc_sm_d_mailtekst_bevat_ordernummers(workspace, db):
    """TC-sm-D: Mailtekst bevat ordernummers van openstaande orders."""
    from app.order.router import _genereer_statusmail_concepten
    orders = _maak_orders(db)
    concepten = _genereer_statusmail_concepten(orders)

    concept_3d = next(c for c in concepten if c["klantcode"] == "3D")
    assert "3D25V700" in concept_3d["mailtekst"]  # wacht akkoord
    assert "3D25V701" in concept_3d["mailtekst"]  # geleverd
    assert "3D25V702" not in concept_3d["mailtekst"]  # done, niet mee


def test_tc_sm_e_mailtekst_toon(workspace, db):
    """TC-sm-E: Mailtekst heeft zakelijke toon met aanhef en afsluiting."""
    from app.order.router import _genereer_statusmail_concepten
    orders = _maak_orders(db)
    concepten = _genereer_statusmail_concepten(orders)

    concept_3d = next(c for c in concepten if c["klantcode"] == "3D")
    tekst = concept_3d["mailtekst"]
    assert "Hallo Michel Visser" in tekst
    assert "Hierbij" in tekst
    assert "Met vriendelijke groet" in tekst
    assert "Martien Luijben" in tekst
    # Heeft een onderwerpregel
    assert "onderwerp" in concept_3d
    assert "Statusoverzicht" in concept_3d["onderwerp"]


def test_tc_sm_f_contact_uit_klantcodes(workspace, db):
    """TC-sm-F: Contactpersoon komt uit klantcodes lookup."""
    from app.order.router import _genereer_statusmail_concepten
    orders = _maak_orders(db)
    concepten = _genereer_statusmail_concepten(orders)

    concept_rd = next(c for c in concepten if c["klantcode"] == "RD")
    assert concept_rd["contact"] == "Marcel van Hoolwerff"
    assert "Hallo Marcel van Hoolwerff" in concept_rd["mailtekst"]


def test_tc_sm_g_geen_openstaande_orders(client, workspace, db):
    """TC-sm-G: Geen relevante orders → melding op pagina."""
    # Alleen een afgeronde order
    from app.order.models import Order, Boring
    db.add(Order(id="order-sm-done", workspace_id="gbt-workspace-001",
                 ordernummer="DONE-001", status="done"))
    db.add(Boring(order_id="order-sm-done", volgnummer=1, type="B"))
    db.commit()

    resp = client.get("/orders/statusmail", auth=AUTH)
    assert resp.status_code == 200
    assert "Geen openstaande" in resp.text


def test_tc_sm_h_locatie_in_mailtekst(workspace, db):
    """TC-sm-H: Locatie wordt vermeld bij orders in de mailtekst."""
    from app.order.router import _genereer_statusmail_concepten
    orders = _maak_orders(db)
    concepten = _genereer_statusmail_concepten(orders)

    concept_3d = next(c for c in concepten if c["klantcode"] == "3D")
    assert "Haarlem" in concept_3d["mailtekst"]
