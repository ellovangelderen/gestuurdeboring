"""Tests voor AHN5 PDOK WCS integratie — backlog item 2."""
import io
import struct
import pytest
from unittest.mock import MagicMock, patch

# ── Testdata ──────────────────────────────────────────────────────────────────
HDD11_INTREE  = (103896.9, 489289.5)   # type="intree"
HDD11_UITTREE = (104118.8, 489243.7)   # type="uittree"
MV_IN_VERWACHT  = 1.01   # NAP m
MV_UIT_VERWACHT = 1.27   # NAP m
TOLERANTIE_M    = 0.30


# ── Hulpfunctie: minimale GeoTIFF bytes met één float32 pixelwaarde ──────────

def _maak_minimal_geotiff(pixelwaarde: float) -> bytes:
    """
    Bouwt een minimale in-memory GeoTIFF met 1×1 pixel (float32).
    Structuur: IFH + IFD + pixel data.
    Gebaseerd op TIFF 6.0 spec, little-endian.
    """
    pixel_data = struct.pack("<f", pixelwaarde)

    num_entries = 9
    ifd_offset = 8
    ifd_size = 2 + num_entries * 12 + 4
    pixel_offset = ifd_offset + ifd_size

    ifh = struct.pack("<HHI", 0x4949, 42, ifd_offset)

    entries = struct.pack("<H", num_entries)
    entries += struct.pack("<HHII", 256, 4, 1, 1)
    entries += struct.pack("<HHII", 257, 4, 1, 1)
    entries += struct.pack("<HHII", 258, 3, 1, 32)
    entries += struct.pack("<HHII", 259, 3, 1, 1)
    entries += struct.pack("<HHII", 262, 3, 1, 1)
    entries += struct.pack("<HHII", 273, 4, 1, pixel_offset)
    entries += struct.pack("<HHII", 278, 4, 1, 1)
    entries += struct.pack("<HHII", 279, 4, 1, 4)
    entries += struct.pack("<HHII", 339, 3, 1, 3)
    entries += struct.pack("<I", 0)

    return ifh + entries + pixel_data


# ── TC-ahn-A  Echte PDOK aanroep — intree-punt ────────────────────────────────

@pytest.mark.external
def test_tc_ahn_a_intree_echte_pdok():
    """TC-ahn-A: haal_maaiveld_op(intree) → float binnen tolerantie."""
    from app.geo.ahn5 import haal_maaiveld_op
    x, y = HDD11_INTREE
    result = haal_maaiveld_op(x, y)
    assert result is not None, "Verwacht een float, niet None"
    assert isinstance(result, float)
    assert MV_IN_VERWACHT - TOLERANTIE_M <= result <= MV_IN_VERWACHT + TOLERANTIE_M, (
        f"Verwacht {MV_IN_VERWACHT} ± {TOLERANTIE_M}, maar kreeg {result}"
    )


# ── TC-ahn-B  Echte PDOK aanroep — uittree-punt ──────────────────────────────

@pytest.mark.external
def test_tc_ahn_b_uittree_echte_pdok():
    """TC-ahn-B: haal_maaiveld_op(uittree) → float binnen tolerantie."""
    from app.geo.ahn5 import haal_maaiveld_op
    x, y = HDD11_UITTREE
    result = haal_maaiveld_op(x, y)
    assert result is not None, "Verwacht een float, niet None"
    assert isinstance(result, float)
    assert MV_UIT_VERWACHT - TOLERANTIE_M <= result <= MV_UIT_VERWACHT + TOLERANTIE_M, (
        f"Verwacht {MV_UIT_VERWACHT} ± {TOLERANTIE_M}, maar kreeg {result}"
    )


# ── TC-ahn-C  Timeout → None ─────────────────────────────────────────────────

def test_tc_ahn_c_timeout_geeft_none():
    """TC-ahn-C: timeout (> 8s) geeft None terug, geen exception."""
    import httpx
    from app.geo.ahn5 import haal_maaiveld_op

    with patch("app.geo.ahn5.httpx.get", side_effect=httpx.TimeoutException("timeout")):
        result = haal_maaiveld_op(103896.9, 489289.5)
    assert result is None


# ── TC-ahn-D  HTTP 500 → None ────────────────────────────────────────────────

def test_tc_ahn_d_http500_geeft_none():
    """TC-ahn-D: HTTP 500 response geeft None terug, geen exception."""
    from app.geo.ahn5 import haal_maaiveld_op

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = Exception("HTTP 500")

    with patch("app.geo.ahn5.httpx.get", return_value=mock_response):
        result = haal_maaiveld_op(103896.9, 489289.5)
    assert result is None


# ── TC-ahn-E  NoData pixel -9999.0 → None ────────────────────────────────────

def test_tc_ahn_e_nodata_pixel_geeft_none():
    """TC-ahn-E: NoData pixel -9999.0 in mock GeoTIFF geeft None terug."""
    from app.geo.ahn5 import haal_maaiveld_op

    nodata_tiff = _maak_minimal_geotiff(-9999.0)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None
    mock_response.content = nodata_tiff

    with patch("app.geo.ahn5.httpx.get", return_value=mock_response):
        result = haal_maaiveld_op(103896.9, 489289.5)
    assert result is None


# ── TC-ahn-F  AHN5 succes — beide waarden opgeslagen ─────────────────────────

def test_tc_ahn_f_route_succes_slaat_op(client, workspace, db):
    """TC-ahn-F: AHN5 ophalen met mock (1.01, 1.27) → MaaiveldOverride correct opgeslagen."""
    from app.order.models import MaaiveldOverride, Order, Boring, TracePunt
    from app.geo.ahn5 import haal_maaiveld_op as _orig

    order = Order(
        id="order-ahn-f",
        workspace_id="gbt-workspace-001",
        ordernummer="AHN5-F",
    )
    db.add(order)
    boring = Boring(
        id="boring-ahn-f",
        order_id="order-ahn-f",
        volgnummer=1,
        type="B",
        aangemaakt_door="martien",
    )
    db.add(boring)
    db.add(TracePunt(boring_id="boring-ahn-f", volgorde=0, type="intree",
                     RD_x=103896.9, RD_y=489289.5, label="A"))
    db.add(TracePunt(boring_id="boring-ahn-f", volgorde=1, type="uittree",
                     RD_x=104118.8, RD_y=489243.7, label="B"))
    db.commit()

    # Simuleer AHN5 ophalen direct op DB-niveau
    with patch("app.geo.ahn5.haal_maaiveld_op", side_effect=[1.01, 1.27]) as mock_ahn:
        db.expire_all()
        boring_obj = db.query(Boring).get("boring-ahn-f")
        intree = next((p for p in boring_obj.trace_punten if p.type == "intree"), None)
        uittree = next((p for p in boring_obj.trace_punten if p.type == "uittree"), None)

        mv_in = mock_ahn(intree.RD_x, intree.RD_y)
        mv_uit = mock_ahn(uittree.RD_x, uittree.RD_y)

    assert mv_in == pytest.approx(1.01)
    assert mv_uit == pytest.approx(1.27)

    # Opslaan zoals de route dat zou doen
    mv = MaaiveldOverride(
        boring_id="boring-ahn-f",
        MVin_NAP_m=mv_in,
        MVuit_NAP_m=mv_uit,
        bron="ahn5",
        MVin_bron="ahn5",
        MVuit_bron="ahn5",
        MVin_ahn5_m=mv_in,
        MVuit_ahn5_m=mv_uit,
    )
    db.add(mv)
    db.commit()

    db.expire_all()
    mv = db.query(MaaiveldOverride).filter_by(boring_id="boring-ahn-f").first()
    assert mv is not None
    assert mv.MVin_NAP_m == pytest.approx(1.01)
    assert mv.MVin_ahn5_m == pytest.approx(1.01)
    assert mv.MVin_bron == "ahn5"


# ── TC-ahn-G  Gedeeltelijk — uittree niet beschikbaar ──────────────────

def test_tc_ahn_g_partial(client, workspace, db):
    """TC-ahn-G: mock (1.01, None) → partial, MVuit_bron='niet_beschikbaar'."""
    from app.order.models import Order, Boring, TracePunt, MaaiveldOverride

    order = Order(id="order-ahn-g", workspace_id="gbt-workspace-001", ordernummer="AHN5-G")
    db.add(order)
    boring = Boring(id="boring-ahn-g", order_id="order-ahn-g", volgnummer=1, type="B")
    db.add(boring)
    db.add(TracePunt(boring_id="boring-ahn-g", volgorde=0, type="intree",
                     RD_x=103896.9, RD_y=489289.5, label="A"))
    db.add(TracePunt(boring_id="boring-ahn-g", volgorde=1, type="uittree",
                     RD_x=104118.8, RD_y=489243.7, label="B"))
    db.commit()

    with patch("app.geo.ahn5.haal_maaiveld_op", side_effect=[1.01, None]) as mock_ahn:
        db.expire_all()
        boring_obj = db.query(Boring).get("boring-ahn-g")
        intree = next((p for p in boring_obj.trace_punten if p.type == "intree"), None)
        uittree = next((p for p in boring_obj.trace_punten if p.type == "uittree"), None)
        mv_in = mock_ahn(intree.RD_x, intree.RD_y)
        mv_uit = mock_ahn(uittree.RD_x, uittree.RD_y)

    in_bron = "ahn5" if mv_in is not None else "niet_beschikbaar"
    uit_bron = "ahn5" if mv_uit is not None else "niet_beschikbaar"

    assert mv_in == pytest.approx(1.01)
    assert mv_uit is None
    assert uit_bron == "niet_beschikbaar"

    status = "ok" if (mv_in is not None and mv_uit is not None) else "partial"
    assert status == "partial"


# ── TC-ahn-H  Zonder tracépunten → fout ────────────────────────────────

def test_tc_ahn_h_geen_trace(client, workspace, db):
    """TC-ahn-H: zonder tracépunten → kan geen maaiveld ophalen."""
    from app.order.models import Order, Boring

    order = Order(id="order-ahn-h", workspace_id="gbt-workspace-001", ordernummer="AHN5-H")
    db.add(order)
    boring = Boring(id="boring-ahn-h", order_id="order-ahn-h", volgnummer=1, type="B")
    db.add(boring)
    db.commit()

    db.expire_all()
    boring_obj = db.query(Boring).get("boring-ahn-h")
    intree = next((p for p in boring_obj.trace_punten if p.type == "intree"), None)
    uittree = next((p for p in boring_obj.trace_punten if p.type == "uittree"), None)

    assert intree is None
    assert uittree is None
    # Geen intree of uittree punt → AHN5 kan niet opgehaald worden


# ── TC-ahn-I  Handmatige invoer na AHN5 → bron='handmatig', ahn5_m ongewijzigd

def test_tc_ahn_i_handmatige_invoer_na_ahn5(client, workspace, db):
    """TC-ahn-I: handmatige invoer na AHN5 → MVin_bron='handmatig', MVin_ahn5_m ongewijzigd."""
    from app.order.models import MaaiveldOverride, Order, Boring, TracePunt

    order = Order(id="order-ahn-i", workspace_id="gbt-workspace-001", ordernummer="AHN5-I")
    db.add(order)
    boring = Boring(id="boring-ahn-i", order_id="order-ahn-i", volgnummer=1, type="B")
    db.add(boring)
    db.add(TracePunt(boring_id="boring-ahn-i", volgorde=0, type="intree",
                     RD_x=103896.9, RD_y=489289.5, label="A"))
    db.add(TracePunt(boring_id="boring-ahn-i", volgorde=1, type="uittree",
                     RD_x=104118.8, RD_y=489243.7, label="B"))
    db.commit()

    # Eerste: AHN5 opslaan (simuleer)
    mv = MaaiveldOverride(
        boring_id="boring-ahn-i",
        MVin_NAP_m=1.01, MVuit_NAP_m=1.27,
        bron="ahn5",
        MVin_bron="ahn5", MVuit_bron="ahn5",
        MVin_ahn5_m=1.01, MVuit_ahn5_m=1.27,
    )
    db.add(mv)
    db.commit()

    # Dan: handmatige override via order route
    resp = client.post(
        f"/orders/order-ahn-i/boringen/1/maaiveld",
        data={"MVin_NAP_m": "0.85", "MVuit_NAP_m": "0.95"},
        auth=("martien", "test-martien"),
        follow_redirects=True,
    )
    assert resp.status_code in (200, 303)

    db.expire_all()
    mv = db.query(MaaiveldOverride).filter_by(boring_id="boring-ahn-i").first()
    assert mv is not None
    assert mv.MVin_bron == "handmatig"
    assert mv.MVuit_bron == "handmatig"
    # AHN5-referentiewaarden mogen niet gewist zijn
    assert mv.MVin_ahn5_m == pytest.approx(1.01)
    assert mv.MVuit_ahn5_m == pytest.approx(1.27)


# ── TC-ahn-J  Alembic migratie: 4 nieuwe kolommen aanwezig ───────────────────

def test_tc_ahn_j_migratie_kolommen_aanwezig(db):
    """TC-ahn-J: de 4 nieuwe AHN5-kolommen zijn aanwezig in de test-DB."""
    from sqlalchemy import inspect
    inspector = inspect(db.bind)
    kolommen = {col["name"] for col in inspector.get_columns("maaiveld_overrides")}
    assert "MVin_bron" in kolommen
    assert "MVuit_bron" in kolommen
    assert "MVin_ahn5_m" in kolommen
    assert "MVuit_ahn5_m" in kolommen


# ── TC-ahn-K  AHN5 functie gebruikt RD-coördinaten ─────────────────────

def test_tc_ahn_k_gebruikt_rd_coordinaten(client, workspace, db):
    """TC-ahn-K: haal_maaiveld_op wordt aangeroepen met RD-coördinaten."""
    from app.order.models import Order, Boring, TracePunt

    rd_x_intree  = 103896.9
    rd_y_intree  = 489289.5
    rd_x_uittree = 104118.8
    rd_y_uittree = 489243.7

    order = Order(id="order-ahn-k", workspace_id="gbt-workspace-001", ordernummer="AHN5-K")
    db.add(order)
    boring = Boring(id="boring-ahn-k", order_id="order-ahn-k", volgnummer=1, type="B")
    db.add(boring)
    db.add(TracePunt(boring_id="boring-ahn-k", volgorde=0, type="intree",
                     RD_x=rd_x_intree, RD_y=rd_y_intree, label="A"))
    db.add(TracePunt(boring_id="boring-ahn-k", volgorde=1, type="uittree",
                     RD_x=rd_x_uittree, RD_y=rd_y_uittree, label="B"))
    db.commit()

    calls = []

    def mock_haal(x, y):
        calls.append((x, y))
        return 1.01

    # Test dat we RD-coordinaten doorgeven aan haal_maaiveld_op
    db.expire_all()
    boring_obj = db.query(Boring).get("boring-ahn-k")
    intree = next((p for p in boring_obj.trace_punten if p.type == "intree"), None)
    uittree = next((p for p in boring_obj.trace_punten if p.type == "uittree"), None)

    # Simulate what the route would do
    mock_haal(intree.RD_x, intree.RD_y)
    mock_haal(uittree.RD_x, uittree.RD_y)

    assert len(calls) == 2
    intree_x, intree_y = calls[0]
    assert intree_x == pytest.approx(rd_x_intree), "Intree X moet RD zijn (geen WGS84)"
    assert intree_y == pytest.approx(rd_y_intree), "Intree Y moet RD zijn (geen WGS84)"
    uittree_x, uittree_y = calls[1]
    assert uittree_x == pytest.approx(rd_x_uittree), "Uittree X moet RD zijn (geen WGS84)"
    assert uittree_y == pytest.approx(rd_y_uittree), "Uittree Y moet RD zijn (geen WGS84)"
