"""TC-klic — Module 9: KLIC IMKL 2.0 GML Parser (Backlog 1 + 3)"""
import io
import os
import zipfile

import pytest
from shapely import from_wkt

from tests.conftest import AUTH

# Pad naar de echte testdata
KLIC_ZIP_PAD = "docs/input_data_14maart/Levering_25O0136974_1.zip"
IJMUIDEN_GML_PAD = "docs/test feedback 17 maart/GI_gebiedsinformatielevering_25O0063608_1_V2.xml"
IJMUIDEN_ZIP_PAD = "uploads/55993f8c-a7b8-4bf6-b9cc-fc2b068c5e03/25O0063608_1-20260317T212650Z-1-001.zip"

# Skip HDD11 tests als testdata ontbreekt
HDD11_BESCHIKBAAR = os.path.exists(KLIC_ZIP_PAD)
IJMUIDEN_GML_BESCHIKBAAR = os.path.exists(IJMUIDEN_GML_PAD)
IJMUIDEN_ZIP_BESCHIKBAAR = os.path.exists(IJMUIDEN_ZIP_PAD)

skip_hdd11 = pytest.mark.skipif(not HDD11_BESCHIKBAAR, reason="HDD11 testdata ontbreekt")
skip_ijmuiden_gml = pytest.mark.skipif(not IJMUIDEN_GML_BESCHIKBAAR, reason="IJmuiden GML testdata ontbreekt")
skip_ijmuiden_zip = pytest.mark.skipif(not IJMUIDEN_ZIP_BESCHIKBAAR, reason="IJmuiden ZIP testdata ontbreekt")


def _maak_order(client, naam="klic-test"):
    """Maak een order aan en geef het order_id terug."""
    resp = client.post(
        "/orders/nieuw",
        data={
            "ordernummer": naam,
            "locatie": "test",
            "klantcode": "",
            "opdrachtgever": "",
            "vergunning": "-",
            "tekenaar": "martien",
            "akkoord_contact": "",
            "deadline": "",
            "type_1": "B",
            "aantal_1": "1",
            "type_2": "",
            "aantal_2": "0",
        },
        auth=AUTH,
        follow_redirects=False,
    )
    # Redirect naar /orders/{order_id}
    assert resp.status_code == 303
    location = resp.headers["location"]
    order_id = location.split("/orders/")[1].rstrip("/")
    return order_id


def _upload_klic_file(client, order_id, file_path, filename=None):
    """Upload een KLIC bestand (ZIP of GML) via de order upload-route."""
    if filename is None:
        filename = os.path.basename(file_path)
    with open(file_path, "rb") as f:
        content_type = "application/zip" if filename.endswith(".zip") else "application/xml"
        resp = client.post(
            f"/orders/{order_id}/klic",
            files={"klic_zip": (filename, f, content_type)},
            auth=AUTH,
            follow_redirects=True,
        )
    assert resp.status_code == 200
    return resp


def _haal_upload(db, order_id):
    from app.order.models import KLICUpload
    db.expire_all()
    return db.query(KLICUpload).filter_by(order_id=order_id).order_by(KLICUpload.upload_datum.desc()).first()


# ── Legacy HDD11 tests (skipif no data) ─────────────────────────────────────

def _maak_project(client, naam="klic-test"):
    resp = client.post("/api/v1/projecten/nieuw", data={"naam": naam}, auth=AUTH, follow_redirects=True)
    project_id = str(resp.url).split("/api/v1/projecten/")[1].rstrip("/")
    return project_id


def _upload_klic(client, project_id, zip_pad=KLIC_ZIP_PAD):
    """Upload echte KLIC ZIP via de legacy project upload-route."""
    with open(zip_pad, "rb") as f:
        resp = client.post(
            f"/api/v1/projecten/{project_id}/klic",
            files={"klic_zip": ("Levering_25O0136974_1.zip", f, "application/zip")},
            auth=AUTH,
            follow_redirects=True,
        )
    assert resp.status_code == 200
    return resp


def _haal_project_upload(db, project_id):
    from app.order.models import KLICUpload
    db.expire_all()
    return db.query(KLICUpload).filter_by(order_id=project_id).order_by(KLICUpload.upload_datum.desc()).first()


def _verwerk(client, project_id, upload_id):
    resp = client.post(
        f"/api/v1/projecten/{project_id}/klic/{upload_id}/verwerken",
        auth=AUTH,
        follow_redirects=True,
    )
    assert resp.status_code == 200


@skip_hdd11
def test_klic_a_verwerkt_true(client, db, workspace):
    pid = _maak_project(client, "klic-a")
    _upload_klic(client, pid)
    upload = _haal_project_upload(db, pid)
    _verwerk(client, pid, upload.id)

    db.expire_all()
    upload = _haal_project_upload(db, pid)
    assert upload.verwerkt is True
    assert upload.verwerk_fout is None


@skip_hdd11
def test_klic_b_aantal_beheerders(client, db, workspace):
    pid = _maak_project(client, "klic-b")
    _upload_klic(client, pid)
    upload = _haal_project_upload(db, pid)
    _verwerk(client, pid, upload.id)

    db.expire_all()
    upload = _haal_project_upload(db, pid)
    assert upload.aantal_beheerders == 11


@skip_hdd11
def test_klic_c_aantal_leidingen(client, db, workspace):
    pid = _maak_project(client, "klic-c")
    _upload_klic(client, pid)
    upload = _haal_project_upload(db, pid)
    _verwerk(client, pid, upload.id)

    db.expire_all()
    upload = _haal_project_upload(db, pid)
    assert upload.aantal_leidingen == 1127


@skip_hdd11
def test_klic_d_liander_elektriciteit(client, db, workspace):
    pid = _maak_project(client, "klic-d")
    _upload_klic(client, pid)
    upload = _haal_project_upload(db, pid)
    _verwerk(client, pid, upload.id)

    from app.order.models import KLICLeiding
    db.expire_all()
    leidingen = (
        db.query(KLICLeiding)
        .filter_by(klic_upload_id=upload.id)
        .filter(KLICLeiding.beheerder.contains("Liander"))
        .all()
    )
    assert len(leidingen) > 0, "Geen Liander leidingen gevonden"
    elektra = [l for l in leidingen if "spanning" in (l.thema or "").lower()]
    assert len(elektra) > 0, "Geen elektriciteit thema voor Liander"


@skip_hdd11
def test_klic_e_reggefiber_sleufloze(client, db, workspace):
    pid = _maak_project(client, "klic-e")
    _upload_klic(client, pid)
    upload = _haal_project_upload(db, pid)
    _verwerk(client, pid, upload.id)

    from app.order.models import KLICLeiding
    db.expire_all()
    sleufloze = (
        db.query(KLICLeiding)
        .filter_by(klic_upload_id=upload.id, sleufloze_techniek=True)
        .filter(KLICLeiding.beheerder.contains("Reggefiber"))
        .all()
    )
    assert len(sleufloze) >= 1, "Geen sleufloze leidingen gevonden voor Reggefiber"


@skip_hdd11
def test_klic_f_alle_leidingen_geen_diepte(client, db, workspace):
    pid = _maak_project(client, "klic-f")
    _upload_klic(client, pid)
    upload = _haal_project_upload(db, pid)
    _verwerk(client, pid, upload.id)

    from app.order.models import KLICLeiding
    db.expire_all()
    met_diepte = (
        db.query(KLICLeiding)
        .filter_by(klic_upload_id=upload.id)
        .filter(KLICLeiding.diepte_m.isnot(None))
        .count()
    )
    assert met_diepte == 0, f"{met_diepte} leidingen hebben onverwacht diepte_m != NULL"


@skip_hdd11
def test_klic_g_status_diepte_waarschuwing(client, db, workspace):
    pid = _maak_project(client, "klic-g")
    _upload_klic(client, pid)
    upload = _haal_project_upload(db, pid)
    _verwerk(client, pid, upload.id)

    resp = client.get(f"/api/v1/projecten/{pid}/klic/status", auth=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert data["verwerkt"] is True
    assert data["diepte_waarschuwing"] is True


@skip_hdd11
def test_klic_h_geometrie_dekking(client, db, workspace):
    pid = _maak_project(client, "klic-h")
    _upload_klic(client, pid)
    upload = _haal_project_upload(db, pid)
    _verwerk(client, pid, upload.id)

    from app.order.models import KLICLeiding
    db.expire_all()
    leidingen = db.query(KLICLeiding).filter_by(klic_upload_id=upload.id).all()
    total = len(leidingen)
    assert total > 0
    met_wkt = sum(1 for l in leidingen if l.geometrie_wkt and l.geometrie_wkt.strip())
    dekking = met_wkt / total
    assert dekking >= 0.95, f"Geometrie dekking {dekking:.1%} < 95%"


@skip_hdd11
def test_klic_i_geldige_wkt(client, db, workspace):
    pid = _maak_project(client, "klic-i")
    _upload_klic(client, pid)
    upload = _haal_project_upload(db, pid)
    _verwerk(client, pid, upload.id)

    from app.order.models import KLICLeiding
    db.expire_all()
    leidingen = (
        db.query(KLICLeiding)
        .filter_by(klic_upload_id=upload.id)
        .filter(KLICLeiding.geometrie_wkt.isnot(None))
        .limit(100)
        .all()
    )
    for l in leidingen:
        geom = from_wkt(l.geometrie_wkt)
        assert geom is not None


@skip_hdd11
def test_klic_j_rd_bereik(client, db, workspace):
    pid = _maak_project(client, "klic-j")
    _upload_klic(client, pid)
    upload = _haal_project_upload(db, pid)
    _verwerk(client, pid, upload.id)

    from app.order.models import KLICLeiding
    db.expire_all()
    leidingen = (
        db.query(KLICLeiding)
        .filter_by(klic_upload_id=upload.id)
        .filter(KLICLeiding.geometrie_wkt.isnot(None))
        .all()
    )
    buiten_bereik = 0
    for l in leidingen:
        geom = from_wkt(l.geometrie_wkt)
        bounds = geom.bounds
        if not (0 <= bounds[0] <= 300000 and 0 <= bounds[2] <= 300000 and
                300000 <= bounds[1] <= 625000 and 300000 <= bounds[3] <= 625000):
            buiten_bereik += 1
    assert buiten_bereik == 0


@skip_hdd11
def test_klic_k_dxf_laagspanning_polylines(client, db, workspace):
    import ezdxf
    from app.documents.dxf_generator import generate_dxf
    from app.project.models import Project

    pid = _maak_project(client, "klic-k")
    _upload_klic(client, pid)
    upload = _haal_project_upload(db, pid)
    _verwerk(client, pid, upload.id)

    db.expire_all()
    project = db.get(Project, pid)
    dxf_bytes = generate_dxf(project, db=db)
    doc = ezdxf.read(io.StringIO(dxf_bytes.decode("utf-8")))
    msp = doc.modelspace()

    ls_polylines = [e for e in msp if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "LAAGSPANNING"]
    assert len(ls_polylines) >= 1


@skip_hdd11
def test_klic_l_dxf_geen_regressie(client, db, workspace):
    import ezdxf
    from app.documents.dxf_generator import generate_dxf, LAYERS
    from app.project.models import Project

    pid = _maak_project(client, "klic-l")
    _upload_klic(client, pid)
    upload = _haal_project_upload(db, pid)
    _verwerk(client, pid, upload.id)

    db.expire_all()
    project = db.get(Project, pid)
    dxf_bytes = generate_dxf(project, db=db)
    doc = ezdxf.read(io.StringIO(dxf_bytes.decode("utf-8")))

    for layer_naam in LAYERS:
        assert layer_naam in doc.layers


@skip_hdd11
def test_klic_m_onbekende_upload_404(client, db, workspace):
    pid = _maak_project(client, "klic-m")
    resp = client.post(
        f"/api/v1/projecten/{pid}/klic/niet-bestaande-upload-id/verwerken",
        auth=AUTH,
        follow_redirects=False,
    )
    assert resp.status_code == 404


@skip_hdd11
def test_klic_n_brondata_toont_tabel(client, db, workspace):
    pid = _maak_project(client, "klic-n")
    _upload_klic(client, pid)
    upload = _haal_project_upload(db, pid)
    _verwerk(client, pid, upload.id)

    resp = client.get(f"/api/v1/projecten/{pid}/brondata", auth=AUTH)
    assert resp.status_code == 200
    html = resp.text
    assert "<table" in html.lower()
    assert "Liander" in html or "liander" in html.lower()


@skip_hdd11
def test_klic_o_geen_duplicaten(client, db, workspace):
    pid = _maak_project(client, "klic-o")
    _upload_klic(client, pid)
    upload = _haal_project_upload(db, pid)

    _verwerk(client, pid, upload.id)
    from app.order.models import KLICLeiding
    db.expire_all()
    count1 = db.query(KLICLeiding).filter_by(klic_upload_id=upload.id).count()

    _verwerk(client, pid, upload.id)
    db.expire_all()
    count2 = db.query(KLICLeiding).filter_by(klic_upload_id=upload.id).count()

    assert count1 == count2


def test_klic_p_zip_zonder_gml(client, db, workspace):
    pid = _maak_project(client, "klic-p")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("readme.txt", "Geen GML hier")
    buf.seek(0)

    resp = client.post(
        f"/api/v1/projecten/{pid}/klic",
        files={"klic_zip": ("leeg.zip", buf, "application/zip")},
        auth=AUTH,
        follow_redirects=True,
    )
    assert resp.status_code == 200

    upload = _haal_project_upload(db, pid)
    assert upload is not None

    resp2 = client.post(
        f"/api/v1/projecten/{pid}/klic/{upload.id}/verwerken",
        auth=AUTH,
        follow_redirects=True,
    )
    assert resp2.status_code == 200

    db.expire_all()
    upload = _haal_project_upload(db, pid)
    assert upload.verwerkt is False
    assert upload.verwerk_fout is not None
    assert len(upload.verwerk_fout) > 0


# ══════════════════════════════════════════════════════════════════════════════
# Backlog 3 tests: EV-detectie, Diepte regex, Materiaal, Formaat B
# ══════════════════════════════════════════════════════════════════════════════


# ── TC-klic-Q: Diepte regex unit tests ──────────────────────────────────────

def test_extract_diepte_nap_patroon():
    """Test _extract_diepte_uit_tekst met diverse NAP patronen."""
    from app.geo.klic_parser import _extract_diepte_uit_tekst

    # Standaard NAP patroon
    val, bron = _extract_diepte_uit_tekst("-1.50 m NAP")
    assert val == -1.50
    assert bron == "tekstveld_onzeker"

    val, bron = _extract_diepte_uit_tekst("+2.30m NAP")
    assert val == 2.30
    assert bron == "tekstveld_onzeker"

    val, bron = _extract_diepte_uit_tekst("3,50 m-NAP")
    assert val == 3.50
    assert bron == "tekstveld_onzeker"

    val, bron = _extract_diepte_uit_tekst("-0.80 nap")
    assert val == -0.80
    assert bron == "tekstveld_onzeker"


def test_extract_diepte_generic_patroon():
    """Test _extract_diepte_uit_tekst met generiek diepte patroon."""
    from app.geo.klic_parser import _extract_diepte_uit_tekst

    val, bron = _extract_diepte_uit_tekst("diepte: -1.20")
    assert val == -1.20
    assert bron == "tekstveld_onzeker"

    val, bron = _extract_diepte_uit_tekst("Diepte circa 2,00 m")
    assert val == 2.0
    assert bron == "tekstveld_onzeker"


def test_extract_diepte_geen_match():
    """Test _extract_diepte_uit_tekst zonder match."""
    from app.geo.klic_parser import _extract_diepte_uit_tekst

    val, bron = _extract_diepte_uit_tekst("Buis HPE 160")
    assert val is None
    assert bron is None

    val, bron = _extract_diepte_uit_tekst("")
    assert val is None
    assert bron is None

    val, bron = _extract_diepte_uit_tekst("8.70 m")
    assert val is None  # Geen NAP suffix, geen "diepte" prefix
    assert bron is None


# ── TC-klic-R: Materiaalregel unit tests ────────────────────────────────────

def test_detect_materiaal_pe_sleufloze():
    """Test dat PE materialen als sleufloze worden gedetecteerd."""
    from lxml import etree
    from app.geo.klic_parser import _detect_materiaal_sleufloze, NS_IMKL, NS_XLINK

    xml = f'''<leiding xmlns:imkl="{NS_IMKL}" xmlns:xlink="{NS_XLINK}">
        <imkl:buismateriaalType xlink:href="http://definities.geostandaarden.nl/imkl2015/id/waarde/PipeMaterialTypeIMKLValue/PE"/>
    </leiding>'''
    el = etree.fromstring(xml.encode())
    sleufloze, mogelijk = _detect_materiaal_sleufloze(el)
    assert sleufloze is True
    assert mogelijk is False


def test_detect_materiaal_pvc_geen_sleufloze():
    """Test dat PVC materiaal geen sleufloze oplevert."""
    from lxml import etree
    from app.geo.klic_parser import _detect_materiaal_sleufloze, NS_IMKL, NS_XLINK

    xml = f'''<leiding xmlns:imkl="{NS_IMKL}" xmlns:xlink="{NS_XLINK}">
        <imkl:buismateriaalType xlink:href="http://definities.geostandaarden.nl/imkl2015/id/waarde/PipeMaterialTypeIMKLValue/PVC"/>
    </leiding>'''
    el = etree.fromstring(xml.encode())
    sleufloze, mogelijk = _detect_materiaal_sleufloze(el)
    assert sleufloze is False
    assert mogelijk is False


def test_detect_materiaal_staal_mogelijk():
    """Test dat staal als mogelijk_sleufloze wordt gedetecteerd."""
    from lxml import etree
    from app.geo.klic_parser import _detect_materiaal_sleufloze, NS_IMKL, NS_XLINK

    xml = f'''<leiding xmlns:imkl="{NS_IMKL}" xmlns:xlink="{NS_XLINK}">
        <imkl:buismateriaalType xlink:href="http://definities.geostandaarden.nl/imkl2015/id/waarde/PipeMaterialTypeIMKLValue/staal"/>
    </leiding>'''
    el = etree.fromstring(xml.encode())
    sleufloze, mogelijk = _detect_materiaal_sleufloze(el)
    assert sleufloze is False
    assert mogelijk is True


def test_detect_materiaal_geen_element():
    """Test dat ontbreken van buismateriaalType geen crash geeft."""
    from lxml import etree
    from app.geo.klic_parser import _detect_materiaal_sleufloze, NS_IMKL

    xml = f'''<leiding xmlns:imkl="{NS_IMKL}">
        <imkl:label>Test</imkl:label>
    </leiding>'''
    el = etree.fromstring(xml.encode())
    sleufloze, mogelijk = _detect_materiaal_sleufloze(el)
    assert sleufloze is False
    assert mogelijk is False


# ── TC-klic-S: EV-detectie op IJmuiden data ─────────────────────────────────

@skip_ijmuiden_gml
def test_ev_detectie_ijmuiden_gml(client, db, workspace):
    """Parse IJmuiden GML, check EV-partijen aanwezig op de order."""
    from app.order.models import EVPartij

    order_id = _maak_order(client, "klic-ev-ijm")
    _upload_klic_file(client, order_id, IJMUIDEN_GML_PAD, "ijmuiden.xml")

    upload = _haal_upload(db, order_id)
    assert upload is not None
    assert upload.verwerkt is True, f"Verwerk fout: {upload.verwerk_fout}"

    db.expire_all()
    ev_partijen = db.query(EVPartij).filter_by(order_id=order_id).all()
    assert len(ev_partijen) >= 1, "Geen EV-partijen gevonden"


@skip_ijmuiden_gml
def test_ev_contactgegevens_petrogas(client, db, workspace):
    """Check dat Petrogas EV-contactgegevens Pipeline Control bevatten."""
    from app.order.models import EVPartij

    order_id = _maak_order(client, "klic-ev-petro")
    _upload_klic_file(client, order_id, IJMUIDEN_GML_PAD, "ijmuiden.xml")

    upload = _haal_upload(db, order_id)
    assert upload.verwerkt is True, f"Verwerk fout: {upload.verwerk_fout}"

    db.expire_all()
    ev_partijen = db.query(EVPartij).filter_by(order_id=order_id).all()
    alle_namen = " ".join(ep.naam or "" for ep in ev_partijen)
    assert "Pipeline Control" in alle_namen, \
        f"Pipeline Control niet in EV partijen: {[ep.naam for ep in ev_partijen]}"


# ── TC-klic-T: Formaat B — enkel GML bestand ────────────────────────────────

@skip_ijmuiden_gml
def test_formaat_b_gml_upload(client, db, workspace):
    """Upload en verwerk een enkel GML bestand (Formaat B)."""
    from app.order.models import KLICLeiding

    order_id = _maak_order(client, "klic-fmtb")
    _upload_klic_file(client, order_id, IJMUIDEN_GML_PAD, "ijmuiden.gml")

    upload = _haal_upload(db, order_id)
    assert upload is not None
    assert upload.verwerkt is True, f"Verwerk fout: {upload.verwerk_fout}"
    assert upload.aantal_leidingen > 0, "Geen leidingen gevonden"
    assert upload.aantal_beheerders > 0, "Geen beheerders gevonden"

    # Check dat er daadwerkelijk leidingen in de DB staan
    db.expire_all()
    count = db.query(KLICLeiding).filter_by(klic_upload_id=upload.id).count()
    assert count > 0, "Geen KLICLeiding records in database"


@skip_ijmuiden_zip
def test_formaat_a_zip_upload_order(client, db, workspace):
    """Upload en verwerk IJmuiden ZIP via order route (auto-verwerking)."""
    from app.order.models import KLICLeiding

    order_id = _maak_order(client, "klic-fmta")
    _upload_klic_file(client, order_id, IJMUIDEN_ZIP_PAD)

    upload = _haal_upload(db, order_id)
    assert upload is not None
    assert upload.verwerkt is True, f"Verwerk fout: {upload.verwerk_fout}"
    assert upload.aantal_leidingen > 0, "Geen leidingen gevonden"


# ── TC-klic-U: Brondata pagina met EV-waarschuwing ──────────────────────────

@skip_ijmuiden_gml
def test_brondata_ev_waarschuwing(client, db, workspace):
    """Brondata pagina toont EV-waarschuwing als er EV-leidingen zijn."""
    order_id = _maak_order(client, "klic-ev-bron")
    _upload_klic_file(client, order_id, IJMUIDEN_GML_PAD, "ijmuiden.xml")

    upload = _haal_upload(db, order_id)
    assert upload.verwerkt is True, f"Verwerk fout: {upload.verwerk_fout}"

    # Haal brondata pagina op voor boring 1
    resp = client.get(
        f"/orders/{order_id}/boringen/1/brondata",
        auth=AUTH,
    )
    assert resp.status_code == 200
    html = resp.text
    assert "EV-leidingen" in html, "EV-waarschuwing ontbreekt op brondata pagina"


# ── TC-klic-V: IJmuiden GML parse resultaten ────────────────────────────────

@skip_ijmuiden_gml
def test_ijmuiden_gml_beheerders(client, db, workspace):
    """IJmuiden GML bevat meerdere beheerders."""
    order_id = _maak_order(client, "klic-ijm-beh")
    _upload_klic_file(client, order_id, IJMUIDEN_GML_PAD, "ijmuiden.xml")

    upload = _haal_upload(db, order_id)
    assert upload.verwerkt is True, f"Verwerk fout: {upload.verwerk_fout}"
    assert upload.aantal_beheerders >= 3, f"Te weinig beheerders: {upload.aantal_beheerders}"


@skip_ijmuiden_gml
def test_ijmuiden_gml_label_tekst(client, db, workspace):
    """IJmuiden GML: sommige leidingen hebben label_tekst."""
    from app.order.models import KLICLeiding

    order_id = _maak_order(client, "klic-ijm-label")
    _upload_klic_file(client, order_id, IJMUIDEN_GML_PAD, "ijmuiden.xml")

    upload = _haal_upload(db, order_id)
    assert upload.verwerkt is True

    db.expire_all()
    met_label = (
        db.query(KLICLeiding)
        .filter_by(klic_upload_id=upload.id)
        .filter(KLICLeiding.label_tekst.isnot(None))
        .count()
    )
    assert met_label > 0, "Geen leidingen met label_tekst gevonden"
