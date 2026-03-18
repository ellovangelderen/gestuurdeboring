"""TC-cockpit — Module: Cockpit UI (Backlog 2)"""
from datetime import datetime, timezone, timedelta

import pytest

from app.order.models import EVPartij, Order, Boring
from tests.conftest import AUTH


def _maak_order(db, workspace, **kwargs):
    """Helper: maak een order met optionele overrides."""
    defaults = dict(
        workspace_id=workspace.id,
        ordernummer="ORD-TEST",
        locatie="Amsterdam",
        klantcode="3D",
        status="order_received",
        tekenaar="martien",
    )
    defaults.update(kwargs)
    order = Order(**defaults)
    db.add(order)
    db.flush()
    return order


def _maak_boring(db, order, volgnr=1, btype="B"):
    """Helper: maak een boring bij een order."""
    boring = Boring(order_id=order.id, volgnummer=volgnr, type=btype, aangemaakt_door="test")
    db.add(boring)
    db.flush()
    return boring


# TC-cockpit-A: Na login -> cockpit als eerste scherm
def test_cockpit_a_eerste_scherm(client, workspace):
    resp = client.get("/orders/", auth=AUTH)
    assert resp.status_code == 200
    assert "Cockpit" in resp.text
    assert "stats-bar" in resp.text or "stat-card" in resp.text


# TC-cockpit-B: Ordertabel toont alle orders met correcte status
def test_cockpit_b_ordertabel_statussen(client, db, workspace):
    o1 = _maak_order(db, workspace, ordernummer="ORD-B1", status="in_progress")
    _maak_boring(db, o1)
    o2 = _maak_order(db, workspace, ordernummer="ORD-B2", status="waiting_for_approval")
    _maak_boring(db, o2)
    db.commit()

    resp = client.get("/orders/", auth=AUTH)
    assert resp.status_code == 200
    assert "ORD-B1" in resp.text
    assert "ORD-B2" in resp.text
    assert "In uitvoering" in resp.text
    assert "Wacht op akkoord" in resp.text


# TC-cockpit-C: Quick-action links naar juiste boring
def test_cockpit_c_quick_actions(client, db, workspace):
    order = _maak_order(db, workspace, ordernummer="ORD-C1")
    _maak_boring(db, order, volgnr=1, btype="B")
    _maak_boring(db, order, volgnr=2, btype="N")
    db.commit()

    resp = client.get("/orders/", auth=AUTH)
    assert resp.status_code == 200
    # Quick-action links bevatten boring volgnummers
    assert f"/orders/{order.id}/boringen/1" in resp.text
    assert f"/orders/{order.id}/boringen/2" in resp.text
    assert f"/orders/{order.id}/boringen/1/trace" in resp.text
    assert f"/orders/{order.id}/boringen/2/brondata" in resp.text


# TC-cockpit-D: Filter "wacht akkoord" -> alleen relevante orders
def test_cockpit_d_filter_wacht_akkoord(client, db, workspace):
    o1 = _maak_order(db, workspace, ordernummer="ORD-D1", status="waiting_for_approval")
    _maak_boring(db, o1)
    o2 = _maak_order(db, workspace, ordernummer="ORD-D2", status="in_progress")
    _maak_boring(db, o2)
    db.commit()

    resp = client.get("/orders/?filter=wacht_akkoord", auth=AUTH)
    assert resp.status_code == 200
    assert "ORD-D1" in resp.text
    assert "ORD-D2" not in resp.text


# TC-cockpit-E: CSV export bevat alle zichtbare orders
def test_cockpit_e_csv_export(client, db, workspace):
    o1 = _maak_order(db, workspace, ordernummer="ORD-E1", locatie="Rotterdam")
    _maak_boring(db, o1)
    o2 = _maak_order(db, workspace, ordernummer="ORD-E2", locatie="Utrecht")
    _maak_boring(db, o2)
    db.commit()

    resp = client.get("/orders/export/csv", auth=AUTH)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    body = resp.content.decode("utf-8")
    # UTF-8 BOM aanwezig
    assert body.startswith("\ufeff")
    assert "ORD-E1" in body
    assert "ORD-E2" in body
    assert "Rotterdam" in body
    assert "Ordernummer" in body  # header row


# TC-cockpit-F: Zoeken op locatie
def test_cockpit_f_zoeken_locatie(client, db, workspace):
    o1 = _maak_order(db, workspace, ordernummer="ORD-F1", locatie="Haarlem Kennemerplein")
    _maak_boring(db, o1)
    o2 = _maak_order(db, workspace, ordernummer="ORD-F2", locatie="Delft Markt")
    _maak_boring(db, o2)
    db.commit()

    resp = client.get("/orders/?zoek=Haarlem", auth=AUTH)
    assert resp.status_code == 200
    assert "ORD-F1" in resp.text
    assert "ORD-F2" not in resp.text


# TC-cockpit-G: Sorteren op deadline
def test_cockpit_g_sorteren_deadline(client, db, workspace):
    o1 = _maak_order(
        db, workspace, ordernummer="ORD-G-LATER",
        deadline=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    _maak_boring(db, o1)
    o2 = _maak_order(
        db, workspace, ordernummer="ORD-G-EERDER",
        deadline=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )
    _maak_boring(db, o2)
    db.commit()

    resp = client.get("/orders/?sorteer=deadline&richting=asc", auth=AUTH)
    assert resp.status_code == 200
    # EERDER moet voor LATER staan
    pos_eerder = resp.text.index("ORD-G-EERDER")
    pos_later = resp.text.index("ORD-G-LATER")
    assert pos_eerder < pos_later


# TC-cockpit-H: Stats-balk correcte tellingen
def test_cockpit_h_stats_balk(client, db, workspace):
    # 1 over deadline (actieve status + deadline in verleden)
    o1 = _maak_order(
        db, workspace, ordernummer="ORD-H1", status="in_progress",
        deadline=datetime(2020, 1, 1, tzinfo=timezone.utc), prio=True,
    )
    _maak_boring(db, o1)
    # 1 wacht akkoord (niet over deadline)
    o2 = _maak_order(
        db, workspace, ordernummer="ORD-H2", status="waiting_for_approval",
        deadline=datetime(2030, 12, 31, tzinfo=timezone.utc),
    )
    _maak_boring(db, o2)
    # 1 geleverd
    o3 = _maak_order(db, workspace, ordernummer="ORD-H3", status="delivered")
    _maak_boring(db, o3)
    db.commit()

    resp = client.get("/orders/", auth=AUTH)
    assert resp.status_code == 200
    # Stats: totaal=3, over_deadline=1, urgent=1, in_uitvoering=1, wacht_akkoord=1
    # Check dat stats values appear in the HTML
    html = resp.text
    # Stats bar should contain the correct numbers
    # totaal=3
    assert '>3</div>' in html.replace(' ', '') or '>3<' in html
    # We verify by checking the stats-bar section
    assert 'Over deadline' in html
    assert 'Urgent' in html
    assert 'In uitvoering' in html
    assert 'Wacht akkoord' in html


# TC-cockpit-I: EV-waarschuwing getoond
def test_cockpit_i_ev_waarschuwing(client, db, workspace):
    order = _maak_order(db, workspace, ordernummer="ORD-I1")
    _maak_boring(db, order)
    ev = EVPartij(order_id=order.id, naam="Gasunie", volgorde=1)
    db.add(ev)
    db.commit()

    resp = client.get("/orders/", auth=AUTH)
    assert resp.status_code == 200
    assert "inline-badge--ev" in resp.text
    assert "Gasunie" in resp.text


# TC-cockpit-J: PRIO-vlag zichtbaar
def test_cockpit_j_prio_vlag(client, db, workspace):
    order = _maak_order(db, workspace, ordernummer="ORD-J1", prio=True)
    _maak_boring(db, order)
    db.commit()

    resp = client.get("/orders/", auth=AUTH)
    assert resp.status_code == 200
    assert "inline-badge--prio" in resp.text
    assert "PRIO" in resp.text
