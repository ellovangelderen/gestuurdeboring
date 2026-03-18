"""Tests voor Backlog 8 — Boogzinker profiel (type Z).

TC-bz-A t/m J: geometrie, DXF, PDF, UI.
"""
import io
import math

import ezdxf
import pytest

from tests.conftest import AUTH


# ── Testdata ──────────────────────────────────────────────────────────────────
BZ_BOOGHOEK = 10.0    # graden
BZ_STAND = 5
BZ_L_TOTAAL = 50.0    # meter horizontale afstand
BZ_MV_IN = 0.5        # NAP
BZ_MV_UIT = 0.3       # NAP
BZ_DE_MM = 110.0


def _maak_boogzinker_boring(db, order_id="order-bz", boring_id="boring-bz",
                             ordernummer="BZ-TEST", volgnr=1):
    """Helper: maak order + type Z boring + trace + maaiveld."""
    from app.order.models import Order, Boring, TracePunt, MaaiveldOverride

    order = Order(id=order_id, workspace_id="gbt-workspace-001", ordernummer=ordernummer)
    db.add(order)
    boring = Boring(
        id=boring_id, order_id=order_id, volgnummer=volgnr, type="Z",
        booghoek_gr=BZ_BOOGHOEK, stand=BZ_STAND, De_mm=BZ_DE_MM,
        aangemaakt_door="martien",
    )
    db.add(boring)
    # Tracepunten (50m uit elkaar)
    db.add(TracePunt(boring_id=boring_id, volgorde=0, type="intree",
                     RD_x=103900.0, RD_y=489290.0, label="A"))
    db.add(TracePunt(boring_id=boring_id, volgorde=1, type="uittree",
                     RD_x=103950.0, RD_y=489290.0, label="B"))
    # Maaiveld
    db.add(MaaiveldOverride(
        boring_id=boring_id, MVin_NAP_m=BZ_MV_IN, MVuit_NAP_m=BZ_MV_UIT,
        bron="handmatig", MVin_bron="handmatig", MVuit_bron="handmatig",
    ))
    db.commit()
    return order, boring


# ═══════════════════════════════════════════════════════════════════════════════
# GEOMETRIE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_tc_bz_a_profiel_1_arc():
    """TC-bz-A: Type Z profiel heeft exact 1 ARC segment, geen lijnen."""
    from app.geo.profiel import bereken_boorprofiel_z
    profiel = bereken_boorprofiel_z(
        L_totaal_m=BZ_L_TOTAAL, MVin_NAP_m=BZ_MV_IN, MVuit_NAP_m=BZ_MV_UIT,
        booghoek_gr=BZ_BOOGHOEK, De_mm=BZ_DE_MM,
    )
    assert len(profiel.segmenten) == 1
    assert profiel.segmenten[0]["type"] == "arc"


def test_tc_bz_b_booglengte_berekend():
    """TC-bz-B: Booglengte is automatisch berekend (R * theta)."""
    from app.geo.profiel import bereken_boorprofiel_z
    profiel = bereken_boorprofiel_z(
        L_totaal_m=BZ_L_TOTAAL, MVin_NAP_m=BZ_MV_IN, MVuit_NAP_m=BZ_MV_UIT,
        booghoek_gr=BZ_BOOGHOEK, De_mm=BZ_DE_MM,
    )
    seg = profiel.segmenten[0]
    assert "booglengte" in seg
    # Booglengte = R * booghoek_rad
    verwachte_R = BZ_L_TOTAAL / (2 * math.sin(math.radians(BZ_BOOGHOEK / 2)))
    verwachte_booglengte = verwachte_R * math.radians(BZ_BOOGHOEK)
    assert seg["booglengte"] == pytest.approx(verwachte_booglengte, rel=0.01)
    # Booglengte moet > L_totaal (boog is langer dan koorde)
    assert seg["booglengte"] > BZ_L_TOTAAL


def test_tc_bz_c_radius_uit_koorde():
    """TC-bz-C: Radius volgt uit chord = 2*R*sin(theta/2)."""
    from app.geo.profiel import bereken_boorprofiel_z
    profiel = bereken_boorprofiel_z(
        L_totaal_m=BZ_L_TOTAAL, MVin_NAP_m=BZ_MV_IN, MVuit_NAP_m=BZ_MV_UIT,
        booghoek_gr=BZ_BOOGHOEK, De_mm=BZ_DE_MM,
    )
    verwachte_R = BZ_L_TOTAAL / (2 * math.sin(math.radians(BZ_BOOGHOEK / 2)))
    assert profiel.Rv_m == pytest.approx(verwachte_R, rel=0.01)


def test_tc_bz_d_diepte_onder_maaiveld():
    """TC-bz-D: Diepste punt van boog ligt onder het laagste maaiveld."""
    from app.geo.profiel import bereken_boorprofiel_z
    profiel = bereken_boorprofiel_z(
        L_totaal_m=BZ_L_TOTAAL, MVin_NAP_m=BZ_MV_IN, MVuit_NAP_m=BZ_MV_UIT,
        booghoek_gr=BZ_BOOGHOEK, De_mm=BZ_DE_MM,
    )
    # Diepte moet minimaal 3m onder laagste maaiveld liggen
    assert profiel.diepte_NAP_m <= min(BZ_MV_IN, BZ_MV_UIT) - 3.0


def test_tc_bz_e_standaard_booghoeken():
    """TC-bz-E: Standaard booghoeken (5, 7.5, 10) produceren geldig profiel."""
    from app.geo.profiel import bereken_boorprofiel_z
    for hoek in [5.0, 7.5, 10.0]:
        profiel = bereken_boorprofiel_z(
            L_totaal_m=BZ_L_TOTAAL, MVin_NAP_m=BZ_MV_IN, MVuit_NAP_m=BZ_MV_UIT,
            booghoek_gr=hoek, De_mm=BZ_DE_MM,
        )
        assert len(profiel.segmenten) == 1
        assert profiel.segmenten[0]["type"] == "arc"
        assert profiel.Rv_m > 0


def test_tc_bz_f_arc_start_end_correct():
    """TC-bz-F: ARC start bij x=0, eindigt bij x=L_totaal."""
    from app.geo.profiel import bereken_boorprofiel_z
    profiel = bereken_boorprofiel_z(
        L_totaal_m=BZ_L_TOTAAL, MVin_NAP_m=BZ_MV_IN, MVuit_NAP_m=BZ_MV_UIT,
        booghoek_gr=BZ_BOOGHOEK, De_mm=BZ_DE_MM,
    )
    seg = profiel.segmenten[0]
    assert seg["x_start"] == pytest.approx(0.0)
    assert seg["x_end"] == pytest.approx(BZ_L_TOTAAL)
    # Start en eind z moeten gelijk zijn (symmetrische boog)
    assert seg["z_start"] == pytest.approx(seg["z_end"])


# ═══════════════════════════════════════════════════════════════════════════════
# DXF TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_tc_bz_g_dxf_1_arc_geen_horizontaal(client, workspace, db):
    """TC-bz-G: DXF type Z → 1 ARC op LP-BOORLIJN, geen horizontaal segment."""
    _maak_boogzinker_boring(db, "order-bz-g", "boring-bz-g", "BZ-G")

    resp = client.get("/orders/order-bz-g/boringen/1/dxf", auth=AUTH)
    assert resp.status_code == 200

    doc = ezdxf.read(io.StringIO(resp.text))
    msp = doc.modelspace()

    # Tel ARCs op LP-BOORLIJN
    arcs = [e for e in msp if e.dxftype() == "ARC" and e.dxf.layer == "LP-BOORLIJN"]
    assert len(arcs) == 1, f"Verwacht 1 ARC, maar {len(arcs)} gevonden"

    # Geen horizontale lijnen op LP-BOORLIJN (type Z heeft geen horizontaal segment)
    lines = [e for e in msp if e.dxftype() == "LINE" and e.dxf.layer == "LP-BOORLIJN"]
    # Type Z mag geen lijnen hebben op BOORLIJN (alleen de ARC)
    assert len(lines) == 0, f"Verwacht 0 lijnen op LP-BOORLIJN voor type Z, maar {len(lines)} gevonden"


def test_tc_bz_h_dxf_booghoek_label(client, workspace, db):
    """TC-bz-H: DXF bevat 'Booghoek' label in maatvoering."""
    _maak_boogzinker_boring(db, "order-bz-h", "boring-bz-h", "BZ-H")

    resp = client.get("/orders/order-bz-h/boringen/1/dxf", auth=AUTH)
    doc = ezdxf.read(io.StringIO(resp.text))
    msp = doc.modelspace()

    texts = [e for e in msp if e.dxftype() == "TEXT" and e.dxf.layer == "LP-MAATVOERING"]
    text_values = [e.dxf.text for e in texts]

    assert any("Booghoek" in t for t in text_values), f"'Booghoek' label niet gevonden in: {text_values}"
    assert any("Booglengte" in t for t in text_values), f"'Booglengte' label niet gevonden in: {text_values}"
    # Geen intree/uittree hoek labels
    assert not any("Intree" in t for t in text_values), "Type Z mag geen 'Intree' hoek label hebben"
    assert not any("Uittree" in t for t in text_values), "Type Z mag geen 'Uittree' hoek label hebben"


# ═══════════════════════════════════════════════════════════════════════════════
# PDF TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_tc_bz_i_pdf_genereert(client, workspace, db):
    """TC-bz-I: PDF voor type Z boring genereert zonder errors."""
    _maak_boogzinker_boring(db, "order-bz-i", "boring-bz-i", "BZ-I")

    resp = client.get("/orders/order-bz-i/boringen/1/pdf", auth=AUTH)
    assert resp.status_code == 200
    assert resp.content[:4] == b"%PDF"
    assert len(resp.content) > 1000


# ═══════════════════════════════════════════════════════════════════════════════
# UI TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_tc_bz_j_ui_boogzinker_velden(client, workspace, db):
    """TC-bz-J: Type Z boring detail toont booghoek + stand velden."""
    _maak_boogzinker_boring(db, "order-bz-j", "boring-bz-j", "BZ-J")

    resp = client.get("/orders/order-bz-j/boringen/1", auth=AUTH)
    assert resp.status_code == 200
    html = resp.text
    assert "booghoek_gr" in html
    assert "stand" in html
    assert "Boogzinker" in html
