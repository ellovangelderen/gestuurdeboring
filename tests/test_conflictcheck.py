"""Tests voor Backlog 7 — Conflictcheck K&L 3D.

TC-cc-A t/m J: geometrie, projectie, afstand, route, UI.
"""
import math
import pytest

from tests.conftest import AUTH


# ── Testdata ──────────────────────────────────────────────────────────────────

def _maak_boring_met_klic(db, order_id="order-cc", boring_id="boring-cc",
                           ordernummer="CC-TEST", leidingen=None):
    """Helper: maak order + boring + trace + maaiveld + KLIC upload + leidingen."""
    from app.order.models import (
        Order, Boring, TracePunt, MaaiveldOverride, KLICUpload, KLICLeiding,
    )
    from datetime import datetime, timezone

    order = Order(id=order_id, workspace_id="gbt-workspace-001", ordernummer=ordernummer)
    db.add(order)
    boring = Boring(
        id=boring_id, order_id=order_id, volgnummer=1, type="B",
        De_mm=160.0, intreehoek_gr=18.0, uittreehoek_gr=22.0,
        aangemaakt_door="martien",
    )
    db.add(boring)
    # Trace: 200m horizontaal
    db.add(TracePunt(boring_id=boring_id, volgorde=0, type="intree",
                     RD_x=103900.0, RD_y=489290.0, label="A"))
    db.add(TracePunt(boring_id=boring_id, volgorde=1, type="uittree",
                     RD_x=104100.0, RD_y=489290.0, label="B"))
    # Maaiveld
    db.add(MaaiveldOverride(
        boring_id=boring_id, MVin_NAP_m=1.0, MVuit_NAP_m=1.0,
        bron="handmatig", MVin_bron="handmatig", MVuit_bron="handmatig",
    ))
    # KLIC upload
    upload = KLICUpload(
        id="upload-cc", order_id=order_id, bestandsnaam="test.zip",
        bestandspad="/tmp/test.zip", verwerkt=True,
        verwerkt_op=datetime.now(timezone.utc),
        aantal_leidingen=len(leidingen or []),
        aantal_beheerders=1,
    )
    db.add(upload)

    # Leidingen
    for i, l in enumerate(leidingen or []):
        db.add(KLICLeiding(
            id=f"leiding-cc-{i}",
            klic_upload_id="upload-cc",
            beheerder=l.get("beheerder", "TestBeheerder"),
            leidingtype=l.get("leidingtype", "Kabel"),
            geometrie_wkt=l["geometrie_wkt"],
            diepte_m=l.get("diepte_m"),
            dxf_laag=l.get("dxf_laag", "LAAGSPANNING"),
        ))
    db.commit()
    return order, boring


# ═══════════════════════════════════════════════════════════════════════════════
# GEOMETRIE UNIT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_tc_cc_a_boor_z_op_x_horizontaal():
    """TC-cc-A: _boor_z_op_x op het horizontale segment geeft diepte_NAP."""
    from app.geo.profiel import bereken_boorprofiel
    from app.geo.conflictcheck import _boor_z_op_x

    profiel = bereken_boorprofiel(
        L_totaal_m=200.0, MVin_NAP_m=1.0, MVuit_NAP_m=1.0,
        alpha_in_gr=18.0, alpha_uit_gr=22.0, De_mm=160.0,
    )
    # Midden van het profiel → horizontaal segment
    z = _boor_z_op_x(profiel, 100.0)
    assert z is not None
    assert z == pytest.approx(profiel.diepte_NAP_m, abs=0.1)


def test_tc_cc_b_boor_z_op_x_intree():
    """TC-cc-B: _boor_z_op_x bij x=0 geeft maaiveld intree."""
    from app.geo.profiel import bereken_boorprofiel
    from app.geo.conflictcheck import _boor_z_op_x

    profiel = bereken_boorprofiel(
        L_totaal_m=200.0, MVin_NAP_m=1.0, MVuit_NAP_m=1.0,
        alpha_in_gr=18.0, alpha_uit_gr=22.0, De_mm=160.0,
    )
    z = _boor_z_op_x(profiel, 0.0)
    assert z is not None
    assert z == pytest.approx(1.0, abs=0.1)


def test_tc_cc_c_check_conflicts_leiding_op_trace():
    """TC-cc-C: Leiding direct op het tracé wordt gedetecteerd."""
    from app.geo.profiel import bereken_boorprofiel
    from app.geo.conflictcheck import check_conflicts
    from unittest.mock import MagicMock

    profiel = bereken_boorprofiel(
        L_totaal_m=200.0, MVin_NAP_m=1.0, MVuit_NAP_m=1.0,
        alpha_in_gr=18.0, alpha_uit_gr=22.0, De_mm=160.0,
    )
    trace = [(103900.0, 489290.0), (104100.0, 489290.0)]

    # Leiding die het tracé kruist op x=100m, diepte 2m
    leiding = MagicMock()
    leiding.id = "l1"
    leiding.beheerder = "Liander"
    leiding.leidingtype = "Laagspanning"
    leiding.geometrie_wkt = "LINESTRING(104000 489280, 104000 489300)"
    leiding.diepte_m = 2.0
    leiding.dxf_laag = "LAAGSPANNING"

    conflicts = check_conflicts(trace, profiel, [leiding])
    assert len(conflicts) >= 1
    assert conflicts[0].beheerder == "Liander"


def test_tc_cc_d_leiding_ver_weg_geen_conflict():
    """TC-cc-D: Leiding >25m van tracé → niet in resultaat."""
    from app.geo.profiel import bereken_boorprofiel
    from app.geo.conflictcheck import check_conflicts
    from unittest.mock import MagicMock

    profiel = bereken_boorprofiel(
        L_totaal_m=200.0, MVin_NAP_m=1.0, MVuit_NAP_m=1.0,
        alpha_in_gr=18.0, alpha_uit_gr=22.0, De_mm=160.0,
    )
    trace = [(103900.0, 489290.0), (104100.0, 489290.0)]

    # Leiding 50m weg
    leiding = MagicMock()
    leiding.id = "l2"
    leiding.beheerder = "Ver Weg"
    leiding.leidingtype = "Kabel"
    leiding.geometrie_wkt = "LINESTRING(104000 489340, 104000 489350)"
    leiding.diepte_m = 1.0
    leiding.dxf_laag = "LAAGSPANNING"

    conflicts = check_conflicts(trace, profiel, [leiding])
    assert len(conflicts) == 0


def test_tc_cc_e_diepte_onbekend_altijd_conflict():
    """TC-cc-E: Leiding zonder diepte → altijd als conflict gemeld."""
    from app.geo.profiel import bereken_boorprofiel
    from app.geo.conflictcheck import check_conflicts
    from unittest.mock import MagicMock

    profiel = bereken_boorprofiel(
        L_totaal_m=200.0, MVin_NAP_m=1.0, MVuit_NAP_m=1.0,
        alpha_in_gr=18.0, alpha_uit_gr=22.0, De_mm=160.0,
    )
    trace = [(103900.0, 489290.0), (104100.0, 489290.0)]

    leiding = MagicMock()
    leiding.id = "l3"
    leiding.beheerder = "PWN"
    leiding.leidingtype = "Waterleiding"
    leiding.geometrie_wkt = "LINESTRING(104000 489280, 104000 489300)"
    leiding.diepte_m = None  # onbekend
    leiding.dxf_laag = "WATERLEIDING"

    conflicts = check_conflicts(trace, profiel, [leiding])
    assert len(conflicts) >= 1
    assert conflicts[0].diepte_onbekend is True


def test_tc_cc_f_deduplicatie_per_leiding():
    """TC-cc-F: Per leiding slechts 1 conflict (dichtstbijzijnde punt)."""
    from app.geo.profiel import bereken_boorprofiel
    from app.geo.conflictcheck import check_conflicts
    from unittest.mock import MagicMock

    profiel = bereken_boorprofiel(
        L_totaal_m=200.0, MVin_NAP_m=1.0, MVuit_NAP_m=1.0,
        alpha_in_gr=18.0, alpha_uit_gr=22.0, De_mm=160.0,
    )
    trace = [(103900.0, 489290.0), (104100.0, 489290.0)]

    # Lange leiding langs het tracé (meerdere punten dichtbij)
    leiding = MagicMock()
    leiding.id = "l4"
    leiding.beheerder = "Liander"
    leiding.leidingtype = "Kabel"
    leiding.geometrie_wkt = "LINESTRING(103950 489285, 104000 489285, 104050 489285)"
    leiding.diepte_m = 1.5
    leiding.dxf_laag = "LAAGSPANNING"

    conflicts = check_conflicts(trace, profiel, [leiding])
    # Slechts 1 resultaat per leiding (gededupliceerd)
    leiding_ids = [c.leiding_id for c in conflicts]
    assert leiding_ids.count("l4") == 1


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTE + UI TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_tc_cc_g_pagina_zonder_klic(client, workspace, db):
    """TC-cc-G: Conflictcheck pagina zonder KLIC → melding."""
    from app.order.models import Order, Boring, TracePunt, MaaiveldOverride
    db.add(Order(id="order-cc-g", workspace_id="gbt-workspace-001", ordernummer="CC-G"))
    boring = Boring(id="boring-cc-g", order_id="order-cc-g", volgnummer=1, type="B")
    db.add(boring)
    db.add(TracePunt(boring_id="boring-cc-g", volgorde=0, type="intree",
                     RD_x=103900.0, RD_y=489290.0, label="A"))
    db.add(TracePunt(boring_id="boring-cc-g", volgorde=1, type="uittree",
                     RD_x=104100.0, RD_y=489290.0, label="B"))
    db.add(MaaiveldOverride(boring_id="boring-cc-g", MVin_NAP_m=1.0, MVuit_NAP_m=1.0,
                             bron="handmatig", MVin_bron="handmatig", MVuit_bron="handmatig"))
    db.commit()

    resp = client.get("/orders/order-cc-g/boringen/1/conflictcheck", auth=AUTH)
    assert resp.status_code == 200
    assert "KLIC" in resp.text


def test_tc_cc_h_pagina_zonder_trace(client, workspace, db):
    """TC-cc-H: Conflictcheck pagina zonder trace → melding."""
    from app.order.models import Order, Boring
    db.add(Order(id="order-cc-h", workspace_id="gbt-workspace-001", ordernummer="CC-H"))
    db.add(Boring(id="boring-cc-h", order_id="order-cc-h", volgnummer=1, type="B"))
    db.commit()

    resp = client.get("/orders/order-cc-h/boringen/1/conflictcheck", auth=AUTH)
    assert resp.status_code == 200
    assert "trac" in resp.text.lower()


def test_tc_cc_i_pagina_met_leidingen(client, workspace, db):
    """TC-cc-I: Conflictcheck pagina met KLIC leidingen → toont resultaten."""
    _maak_boring_met_klic(db, "order-cc-i", "boring-cc-i", "CC-I", leidingen=[
        {"geometrie_wkt": "LINESTRING(104000 489280, 104000 489300)",
         "beheerder": "Liander", "leidingtype": "Laagspanning", "diepte_m": None},
    ])

    resp = client.get("/orders/order-cc-i/boringen/1/conflictcheck", auth=AUTH)
    assert resp.status_code == 200
    assert "Liander" in resp.text
    assert "onbekend" in resp.text.lower()


def test_tc_cc_j_link_in_brondata(client, workspace, db):
    """TC-cc-J: Brondata pagina bevat link naar conflictcheck."""
    from app.order.models import Order, Boring
    db.add(Order(id="order-cc-j", workspace_id="gbt-workspace-001", ordernummer="CC-J"))
    db.add(Boring(id="boring-cc-j", order_id="order-cc-j", volgnummer=1, type="B"))
    db.commit()

    resp = client.get("/orders/order-cc-j/boringen/1/brondata", auth=AUTH)
    assert resp.status_code == 200
    assert "conflictcheck" in resp.text.lower()
