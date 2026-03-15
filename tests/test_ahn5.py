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
    # Pixel data: 1 float32 waarde
    pixel_data = struct.pack("<f", pixelwaarde)

    # TIFF tags die we nodig hebben:
    # 256 ImageWidth = 1
    # 257 ImageLength = 1
    # 258 BitsPerSample = 32
    # 259 Compression = 1 (geen)
    # 262 PhotometricInterpretation = 1 (BlackIsZero)
    # 273 StripOffsets = offset naar pixel data
    # 278 RowsPerStrip = 1
    # 279 StripByteCounts = 4
    # 339 SampleFormat = 3 (float)

    # IFH (Image File Header): 8 bytes
    # offset 0: byte order (II = little endian)
    # offset 2: magic number 42
    # offset 4: offset naar eerste IFD

    num_entries = 9
    ifd_offset = 8  # direct na IFH
    # IFD: 2 bytes (num_entries) + num_entries * 12 bytes + 4 bytes (next IFD = 0)
    ifd_size = 2 + num_entries * 12 + 4
    pixel_offset = ifd_offset + ifd_size

    # IFH
    ifh = struct.pack("<HHI", 0x4949, 42, ifd_offset)

    # IFD entries: tag (H), type (H), count (I), value_or_offset (I)
    # type 3 = SHORT, type 4 = LONG, type 11 = FLOAT
    entries = struct.pack("<H", num_entries)
    entries += struct.pack("<HHII", 256, 4, 1, 1)    # ImageWidth = 1
    entries += struct.pack("<HHII", 257, 4, 1, 1)    # ImageLength = 1
    entries += struct.pack("<HHII", 258, 3, 1, 32)   # BitsPerSample = 32
    entries += struct.pack("<HHII", 259, 3, 1, 1)    # Compression = no
    entries += struct.pack("<HHII", 262, 3, 1, 1)    # PhotometricInterpretation
    entries += struct.pack("<HHII", 273, 4, 1, pixel_offset)  # StripOffsets
    entries += struct.pack("<HHII", 278, 4, 1, 1)    # RowsPerStrip = 1
    entries += struct.pack("<HHII", 279, 4, 1, 4)    # StripByteCounts = 4 bytes
    entries += struct.pack("<HHII", 339, 3, 1, 3)    # SampleFormat = float
    entries += struct.pack("<I", 0)  # next IFD = 0

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


# ── TC-ahn-F  Route succes — beide waarden opgeslagen ─────────────────────────

def test_tc_ahn_f_route_succes_slaat_op(client, workspace, db):
    """TC-ahn-F: route met mock (1.01, 1.27) → MaaiveldOverride correct opgeslagen."""
    from app.project.models import MaaiveldOverride, Project, TracePunt

    # Maak project aan
    project = Project(
        id="proj-ahn-f",
        workspace_id="gbt-workspace-001",
        naam="AHN5 Test F",
        aangemaakt_door="martien",
    )
    db.add(project)

    # Voeg intree- en uittree-punt toe
    db.add(TracePunt(project_id="proj-ahn-f", volgorde=0, type="intree",
                     RD_x=103896.9, RD_y=489289.5, label="A"))
    db.add(TracePunt(project_id="proj-ahn-f", volgorde=1, type="uittree",
                     RD_x=104118.8, RD_y=489243.7, label="B"))
    db.commit()

    with patch("app.project.router.haal_maaiveld_op", side_effect=[1.01, 1.27]):
        resp = client.post(
            "/api/v1/projecten/proj-ahn-f/maaiveld/ahn5",
            auth=("martien", "test-martien"),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["MVin_NAP_m"] == pytest.approx(1.01)
    assert data["MVuit_NAP_m"] == pytest.approx(1.27)
    assert data["MVin_bron"] == "ahn5"
    assert data["MVuit_bron"] == "ahn5"

    db.expire_all()
    mv = db.query(MaaiveldOverride).filter_by(project_id="proj-ahn-f").first()
    assert mv is not None
    assert mv.MVin_NAP_m == pytest.approx(1.01)
    assert mv.MVin_ahn5_m == pytest.approx(1.01)
    assert mv.MVin_bron == "ahn5"


# ── TC-ahn-G  Route gedeeltelijk — uittree niet beschikbaar ──────────────────

def test_tc_ahn_g_route_partial(client, workspace, db):
    """TC-ahn-G: mock (1.01, None) → status='partial', MVuit_bron='niet_beschikbaar'."""
    from app.project.models import Project, TracePunt

    project = Project(
        id="proj-ahn-g",
        workspace_id="gbt-workspace-001",
        naam="AHN5 Test G",
        aangemaakt_door="martien",
    )
    db.add(project)
    db.add(TracePunt(project_id="proj-ahn-g", volgorde=0, type="intree",
                     RD_x=103896.9, RD_y=489289.5, label="A"))
    db.add(TracePunt(project_id="proj-ahn-g", volgorde=1, type="uittree",
                     RD_x=104118.8, RD_y=489243.7, label="B"))
    db.commit()

    with patch("app.project.router.haal_maaiveld_op", side_effect=[1.01, None]):
        resp = client.post(
            "/api/v1/projecten/proj-ahn-g/maaiveld/ahn5",
            auth=("martien", "test-martien"),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "partial"
    assert data["MVin_NAP_m"] == pytest.approx(1.01)
    assert data["MVuit_NAP_m"] is None
    assert data["MVuit_bron"] == "niet_beschikbaar"


# ── TC-ahn-H  Route zonder tracépunten → fout ────────────────────────────────

def test_tc_ahn_h_route_geen_trace(client, workspace, db):
    """TC-ahn-H: route zonder tracépunten → status='fout', melding bevat 'intree'."""
    from app.project.models import Project

    project = Project(
        id="proj-ahn-h",
        workspace_id="gbt-workspace-001",
        naam="AHN5 Test H",
        aangemaakt_door="martien",
    )
    db.add(project)
    db.commit()

    resp = client.post(
        "/api/v1/projecten/proj-ahn-h/maaiveld/ahn5",
        auth=("martien", "test-martien"),
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "fout"
    assert "intree" in data["melding"]


# ── TC-ahn-I  Handmatige invoer na AHN5 → bron='handmatig', ahn5_m ongewijzigd

def test_tc_ahn_i_handmatige_invoer_na_ahn5(client, workspace, db):
    """TC-ahn-I: handmatige invoer na AHN5 → MVin_bron='handmatig', MVin_ahn5_m ongewijzigd."""
    from app.project.models import MaaiveldOverride, Project, TracePunt

    project = Project(
        id="proj-ahn-i",
        workspace_id="gbt-workspace-001",
        naam="AHN5 Test I",
        aangemaakt_door="martien",
    )
    db.add(project)
    db.add(TracePunt(project_id="proj-ahn-i", volgorde=0, type="intree",
                     RD_x=103896.9, RD_y=489289.5, label="A"))
    db.add(TracePunt(project_id="proj-ahn-i", volgorde=1, type="uittree",
                     RD_x=104118.8, RD_y=489243.7, label="B"))
    db.commit()

    # Eerste: AHN5 ophalen
    with patch("app.project.router.haal_maaiveld_op", side_effect=[1.01, 1.27]):
        client.post(
            "/api/v1/projecten/proj-ahn-i/maaiveld/ahn5",
            auth=("martien", "test-martien"),
        )

    # Dan: handmatige override
    resp = client.post(
        "/api/v1/projecten/proj-ahn-i/maaiveld",
        data={"MVin_NAP_m": "0.85", "MVuit_NAP_m": "0.95"},
        auth=("martien", "test-martien"),
    )
    # Redirect verwacht
    assert resp.status_code in (200, 303)

    db.expire_all()
    mv = db.query(MaaiveldOverride).filter_by(project_id="proj-ahn-i").first()
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


# ── TC-ahn-K  Route gebruikt RD-coördinaten (niet WGS84) ─────────────────────

def test_tc_ahn_k_route_gebruikt_rd_coordinaten(client, workspace, db):
    """TC-ahn-K: AHN5-route roept haal_maaiveld_op aan met RD-coördinaten."""
    from app.project.models import Project, TracePunt

    rd_x_intree  = 103896.9
    rd_y_intree  = 489289.5
    rd_x_uittree = 104118.8
    rd_y_uittree = 489243.7

    project = Project(
        id="proj-ahn-k",
        workspace_id="gbt-workspace-001",
        naam="AHN5 Test K",
        aangemaakt_door="martien",
    )
    db.add(project)
    db.add(TracePunt(project_id="proj-ahn-k", volgorde=0, type="intree",
                     RD_x=rd_x_intree, RD_y=rd_y_intree, label="A"))
    db.add(TracePunt(project_id="proj-ahn-k", volgorde=1, type="uittree",
                     RD_x=rd_x_uittree, RD_y=rd_y_uittree, label="B"))
    db.commit()

    calls = []

    def mock_haal(x, y):
        calls.append((x, y))
        return 1.01

    with patch("app.project.router.haal_maaiveld_op", side_effect=mock_haal):
        client.post(
            "/api/v1/projecten/proj-ahn-k/maaiveld/ahn5",
            auth=("martien", "test-martien"),
        )

    assert len(calls) == 2
    # Intree — RD waarden verwacht (niet WGS84: lat ≈ 52, lon ≈ 4)
    intree_x, intree_y = calls[0]
    assert intree_x == pytest.approx(rd_x_intree), "Intree X moet RD zijn (geen WGS84)"
    assert intree_y == pytest.approx(rd_y_intree), "Intree Y moet RD zijn (geen WGS84)"
    uittree_x, uittree_y = calls[1]
    assert uittree_x == pytest.approx(rd_x_uittree), "Uittree X moet RD zijn (geen WGS84)"
    assert uittree_y == pytest.approx(rd_y_uittree), "Uittree Y moet RD zijn (geen WGS84)"
