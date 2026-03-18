"""Tests voor Backlog 10 — AHN5 maaiveld op order-niveau + PDOK URL + Waterschap.

Deel A: AHN5 route op order/boring-niveau (TC-b10-A t/m F)
Deel B: PDOK URL auto-generatie (TC-b10-G t/m I)
Deel C: Waterschap bepaling + URL (TC-b10-J t/m O)
"""
import pytest
from unittest.mock import patch, MagicMock

from tests.conftest import AUTH

# ── Testdata ──────────────────────────────────────────────────────────────────
HDD11_INTREE  = (103896.9, 489289.5)
HDD11_UITTREE = (104118.8, 489243.7)


def _maak_boring_met_trace(db, order_id="order-b10", boring_id="boring-b10",
                            ordernummer="B10-TEST", volgnr=1):
    """Helper: maak order + boring + intree/uittree tracepunten."""
    from app.order.models import Order, Boring, TracePunt

    order = Order(id=order_id, workspace_id="gbt-workspace-001", ordernummer=ordernummer)
    db.add(order)
    boring = Boring(id=boring_id, order_id=order_id, volgnummer=volgnr, type="B",
                    aangemaakt_door="martien")
    db.add(boring)
    db.add(TracePunt(boring_id=boring_id, volgorde=0, type="intree",
                     RD_x=HDD11_INTREE[0], RD_y=HDD11_INTREE[1], label="A"))
    db.add(TracePunt(boring_id=boring_id, volgorde=1, type="uittree",
                     RD_x=HDD11_UITTREE[0], RD_y=HDD11_UITTREE[1], label="B"))
    db.commit()
    return order, boring


# ═══════════════════════════════════════════════════════════════════════════════
# DEEL A: AHN5 route op order/boring-niveau
# ═══════════════════════════════════════════════════════════════════════════════

def test_tc_b10_a_ahn5_route_succes(client, workspace, db):
    """TC-b10-A: AHN5 route haalt beide waarden op en slaat correct op."""
    _maak_boring_met_trace(db, "order-a", "boring-a", "B10-A")

    with patch("app.order.router.haal_maaiveld_op", side_effect=[1.01, 1.27]):
        resp = client.post("/orders/order-a/boringen/1/maaiveld/ahn5", auth=AUTH)

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["MVin_NAP_m"] == pytest.approx(1.01)
    assert data["MVuit_NAP_m"] == pytest.approx(1.27)
    assert data["MVin_bron"] == "ahn5"
    assert data["MVuit_bron"] == "ahn5"

    # Controleer database
    from app.order.models import MaaiveldOverride
    mv = db.query(MaaiveldOverride).filter_by(boring_id="boring-a").first()
    assert mv is not None
    assert mv.MVin_NAP_m == pytest.approx(1.01)
    assert mv.MVuit_NAP_m == pytest.approx(1.27)
    assert mv.MVin_ahn5_m == pytest.approx(1.01)
    assert mv.MVuit_ahn5_m == pytest.approx(1.27)
    assert mv.bron == "ahn5"


def test_tc_b10_b_ahn5_route_partial(client, workspace, db):
    """TC-b10-B: AHN5 partial — intree OK, uittree niet beschikbaar."""
    _maak_boring_met_trace(db, "order-b", "boring-b", "B10-B")

    with patch("app.order.router.haal_maaiveld_op", side_effect=[1.01, None]):
        resp = client.post("/orders/order-b/boringen/1/maaiveld/ahn5", auth=AUTH)

    data = resp.json()
    assert data["status"] == "partial"
    assert data["MVin_NAP_m"] == pytest.approx(1.01)
    assert data["MVuit_NAP_m"] is None
    assert data["MVin_bron"] == "ahn5"
    assert data["MVuit_bron"] == "niet_beschikbaar"
    assert "uittree" in data["melding"]


def test_tc_b10_c_ahn5_route_geen_trace(client, workspace, db):
    """TC-b10-C: AHN5 zonder tracepunten → foutmelding."""
    from app.order.models import Order, Boring
    db.add(Order(id="order-c", workspace_id="gbt-workspace-001", ordernummer="B10-C"))
    db.add(Boring(id="boring-c", order_id="order-c", volgnummer=1, type="B"))
    db.commit()

    resp = client.post("/orders/order-c/boringen/1/maaiveld/ahn5", auth=AUTH)
    data = resp.json()
    assert data["status"] == "fout"
    assert "tracé" in data["melding"].lower() or "intree" in data["melding"].lower()


def test_tc_b10_d_ahn5_service_onbereikbaar(client, workspace, db):
    """TC-b10-D: AHN5 service onbereikbaar (beide None) → foutmelding."""
    _maak_boring_met_trace(db, "order-d", "boring-d", "B10-D")

    with patch("app.order.router.haal_maaiveld_op", return_value=None):
        resp = client.post("/orders/order-d/boringen/1/maaiveld/ahn5", auth=AUTH)

    data = resp.json()
    assert data["status"] == "fout"
    assert "handmatig" in data["melding"].lower() or "bereikbaar" in data["melding"].lower()


def test_tc_b10_e_handmatig_na_ahn5_bewaart_ref(client, workspace, db):
    """TC-b10-E: Handmatige override na AHN5 → bron='handmatig', AHN5 ref bewaard."""
    _maak_boring_met_trace(db, "order-e", "boring-e", "B10-E")

    # Eerst AHN5
    with patch("app.order.router.haal_maaiveld_op", side_effect=[1.01, 1.27]):
        client.post("/orders/order-e/boringen/1/maaiveld/ahn5", auth=AUTH)

    # Dan handmatig
    resp = client.post(
        "/orders/order-e/boringen/1/maaiveld",
        data={"MVin_NAP_m": "0.85", "MVuit_NAP_m": "0.95"},
        auth=AUTH, follow_redirects=True,
    )
    assert resp.status_code in (200, 303)

    from app.order.models import MaaiveldOverride
    db.expire_all()
    mv = db.query(MaaiveldOverride).filter_by(boring_id="boring-e").first()
    assert mv.MVin_bron == "handmatig"
    assert mv.MVuit_bron == "handmatig"
    assert mv.MVin_NAP_m == pytest.approx(0.85)
    # AHN5 referentiewaarden ongewijzigd
    assert mv.MVin_ahn5_m == pytest.approx(1.01)
    assert mv.MVuit_ahn5_m == pytest.approx(1.27)


def test_tc_b10_f_ahn5_gebruikt_rd_coordinaten(client, workspace, db):
    """TC-b10-F: AHN5 route geeft RD-coördinaten door, niet WGS84."""
    _maak_boring_met_trace(db, "order-f", "boring-f", "B10-F")

    calls = []

    def mock_ahn(x, y):
        calls.append((x, y))
        return 1.0

    with patch("app.order.router.haal_maaiveld_op", side_effect=mock_ahn):
        client.post("/orders/order-f/boringen/1/maaiveld/ahn5", auth=AUTH)

    assert len(calls) == 2
    # Intree moet RD zijn (>100000), niet WGS84 (< 90)
    assert calls[0][0] == pytest.approx(HDD11_INTREE[0])
    assert calls[0][1] == pytest.approx(HDD11_INTREE[1])
    assert calls[1][0] == pytest.approx(HDD11_UITTREE[0])
    assert calls[1][1] == pytest.approx(HDD11_UITTREE[1])


# ═══════════════════════════════════════════════════════════════════════════════
# DEEL B: PDOK URL auto-generatie
# ═══════════════════════════════════════════════════════════════════════════════

def test_tc_b10_g_pdok_url_formaat():
    """TC-b10-G: genereer_pdok_url geeft correct geformatteerde URL."""
    from app.geo.pdok_urls import genereer_pdok_url
    url = genereer_pdok_url(103896.9, 489289.5)
    assert "app.pdok.nl/viewer" in url
    assert "x=103896.90" in url
    assert "y=489289.50" in url
    assert "z=12" in url


def test_tc_b10_h_pdok_url_custom_zoom():
    """TC-b10-H: genereer_pdok_url met custom zoomniveau."""
    from app.geo.pdok_urls import genereer_pdok_url
    url = genereer_pdok_url(103896.9, 489289.5, zoom=15)
    assert "z=15" in url


def test_tc_b10_i_trace_opslaan_genereert_pdok_url(client, workspace, db):
    """TC-b10-I: tracé opslaan vult automatisch pdok_url in op de order."""
    from app.order.models import Order, Boring
    db.add(Order(id="order-i", workspace_id="gbt-workspace-001", ordernummer="B10-I"))
    db.add(Boring(id="boring-i", order_id="order-i", volgnummer=1, type="B"))
    db.commit()

    with patch("app.order.router.bepaal_waterschap", return_value=None):
        resp = client.post(
            "/orders/order-i/boringen/1/trace",
            data={
                "RD_x_list": "103896.90,104118.80",
                "RD_y_list": "489289.50,489243.70",
                "type_list": "intree,uittree",
                "label_list": "A,B",
                "Rh_list": ",",
            },
            auth=AUTH, follow_redirects=True,
        )

    assert resp.status_code in (200, 303)
    db.expire_all()
    order = db.query(Order).get("order-i")
    assert order.pdok_url is not None
    assert "103896.90" in order.pdok_url
    assert "app.pdok.nl" in order.pdok_url


# ═══════════════════════════════════════════════════════════════════════════════
# DEEL C: Waterschap bepaling + URL
# ═══════════════════════════════════════════════════════════════════════════════

def test_tc_b10_j_waterschap_lookup_tabel():
    """TC-b10-J: waterschap_kaart_url vindt bekende waterschappen."""
    from app.geo.waterschap import waterschap_kaart_url
    url = waterschap_kaart_url("Hoogheemraadschap van Rijnland")
    assert url is not None
    assert "rijnland" in url.lower()


def test_tc_b10_k_waterschap_onbekend_geeft_none():
    """TC-b10-K: waterschap_kaart_url retourneert None voor onbekend waterschap."""
    from app.geo.waterschap import waterschap_kaart_url
    assert waterschap_kaart_url("Onbekend Waterschap XYZ") is None
    assert waterschap_kaart_url(None) is None


def test_tc_b10_l_bepaal_waterschap_mock_succes():
    """TC-b10-L: bepaal_waterschap met gemockte WFS-response."""
    from app.geo.waterschap import bepaal_waterschap

    mock_json = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "waterbeheerder": "Hoogheemraadschap van Rijnland",
                "naam": "Hoogheemraadschap van Rijnland (INSPIRE-grens)",
            },
            "geometry": {"type": "Polygon", "coordinates": []},
        }],
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = mock_json

    with patch("app.geo.waterschap.httpx.get", return_value=mock_resp):
        naam = bepaal_waterschap(103896.9, 489289.5)

    assert naam == "Hoogheemraadschap van Rijnland"


def test_tc_b10_m_bepaal_waterschap_timeout():
    """TC-b10-M: bepaal_waterschap timeout → None, geen exception."""
    import httpx
    from app.geo.waterschap import bepaal_waterschap

    with patch("app.geo.waterschap.httpx.get", side_effect=httpx.TimeoutException("timeout")):
        result = bepaal_waterschap(103896.9, 489289.5)
    assert result is None


def test_tc_b10_n_bepaal_waterschap_geen_features():
    """TC-b10-N: bepaal_waterschap met lege feature-lijst → None."""
    from app.geo.waterschap import bepaal_waterschap

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"type": "FeatureCollection", "features": []}

    with patch("app.geo.waterschap.httpx.get", return_value=mock_resp):
        result = bepaal_waterschap(103896.9, 489289.5)
    assert result is None


def test_tc_b10_o_trace_opslaan_vult_waterschap_url(client, workspace, db):
    """TC-b10-O: tracé opslaan met waterschap → waterkering_url ingevuld."""
    from app.order.models import Order, Boring

    db.add(Order(id="order-o", workspace_id="gbt-workspace-001", ordernummer="B10-O"))
    db.add(Boring(id="boring-o", order_id="order-o", volgnummer=1, type="B"))
    db.commit()

    with patch("app.order.router.bepaal_waterschap", return_value="Hoogheemraadschap van Rijnland"):
        resp = client.post(
            "/orders/order-o/boringen/1/trace",
            data={
                "RD_x_list": "103896.90,104118.80",
                "RD_y_list": "489289.50,489243.70",
                "type_list": "intree,uittree",
                "label_list": "A,B",
                "Rh_list": ",",
            },
            auth=AUTH, follow_redirects=True,
        )

    assert resp.status_code in (200, 303)
    db.expire_all()
    order = db.query(Order).get("order-o")
    assert order.waterkering_url is not None
    assert "rijnland" in order.waterkering_url.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# EXTERNE TESTS (echte PDOK calls, skip met SKIP_EXTERNAL_CALLS=1)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.external
def test_tc_b10_ext_a_waterschap_haarlem():
    """TC-b10-ext-A: echte PDOK WFS call voor Haarlem → Rijnland."""
    from app.geo.waterschap import bepaal_waterschap
    naam = bepaal_waterschap(103896.9, 489289.5)
    assert naam is not None
    assert "rijnland" in naam.lower()


@pytest.mark.external
def test_tc_b10_ext_b_waterschap_url_haarlem():
    """TC-b10-ext-B: echte waterschap-naam → kaart-URL beschikbaar."""
    from app.geo.waterschap import bepaal_waterschap, waterschap_kaart_url
    naam = bepaal_waterschap(103896.9, 489289.5)
    url = waterschap_kaart_url(naam)
    assert url is not None
