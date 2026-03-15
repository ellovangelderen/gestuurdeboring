"""TC-klic — Module 9: KLIC IMKL 2.0 GML Parser"""
import io
import zipfile

import pytest
from shapely import from_wkt

from tests.conftest import AUTH

# Pad naar de echte testdata
KLIC_ZIP_PAD = "docs/input_data_14maart/Levering_25O0136974_1.zip"


def _maak_project(client, naam="klic-test"):
    resp = client.post("/api/v1/projecten/nieuw", data={"naam": naam}, auth=AUTH, follow_redirects=True)
    project_id = str(resp.url).split("/api/v1/projecten/")[1].rstrip("/")
    return project_id


def _upload_klic(client, project_id, zip_pad=KLIC_ZIP_PAD):
    """Upload echte KLIC ZIP via de upload-route."""
    with open(zip_pad, "rb") as f:
        resp = client.post(
            f"/api/v1/projecten/{project_id}/klic",
            files={"klic_zip": ("Levering_25O0136974_1.zip", f, "application/zip")},
            auth=AUTH,
            follow_redirects=True,
        )
    assert resp.status_code == 200
    return resp


def _haal_upload(db, project_id):
    from app.project.models import KLICUpload
    db.expire_all()
    return db.query(KLICUpload).filter_by(project_id=project_id).order_by(KLICUpload.upload_datum.desc()).first()


def _verwerk(client, project_id, upload_id):
    resp = client.post(
        f"/api/v1/projecten/{project_id}/klic/{upload_id}/verwerken",
        auth=AUTH,
        follow_redirects=True,
    )
    assert resp.status_code == 200


# ── TC-klic-A: HDD11 ZIP parsen → verwerkt=True, verwerk_fout=None ───────────

def test_klic_a_verwerkt_true(client, db, workspace):
    pid = _maak_project(client, "klic-a")
    _upload_klic(client, pid)
    upload = _haal_upload(db, pid)
    _verwerk(client, pid, upload.id)

    db.expire_all()
    upload = _haal_upload(db, pid)
    assert upload.verwerkt is True
    assert upload.verwerk_fout is None


# ── TC-klic-B: HDD11 ZIP parsen → aantal_beheerders=11 (exact) ───────────────

def test_klic_b_aantal_beheerders(client, db, workspace):
    pid = _maak_project(client, "klic-b")
    _upload_klic(client, pid)
    upload = _haal_upload(db, pid)
    _verwerk(client, pid, upload.id)

    db.expire_all()
    upload = _haal_upload(db, pid)
    assert upload.aantal_beheerders == 11


# ── TC-klic-C: HDD11 ZIP parsen → aantal_leidingen=1127 (exact) ──────────────

def test_klic_c_aantal_leidingen(client, db, workspace):
    pid = _maak_project(client, "klic-c")
    _upload_klic(client, pid)
    upload = _haal_upload(db, pid)
    _verwerk(client, pid, upload.id)

    db.expire_all()
    upload = _haal_upload(db, pid)
    assert upload.aantal_leidingen == 1127


# ── TC-klic-D: KL1040 Liander aanwezig → minstens 1 leiding thema=elektriciteit, dxf_laag correct ──

def test_klic_d_liander_elektriciteit(client, db, workspace):
    pid = _maak_project(client, "klic-d")
    _upload_klic(client, pid)
    upload = _haal_upload(db, pid)
    _verwerk(client, pid, upload.id)

    from app.project.models import KLICLeiding
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

    dxf_lagen = {l.dxf_laag for l in elektra}
    geldige_lagen = {"LAAGSPANNING", "MIDDENSPANNING", "HOOGSPANNING"}
    assert dxf_lagen & geldige_lagen, f"Geen geldige DXF-laag: {dxf_lagen}"


# ── TC-klic-E: KL1049 Reggefiber → sleufloze_techniek=True op minstens 1 leiding ──

def test_klic_e_reggefiber_sleufloze(client, db, workspace):
    pid = _maak_project(client, "klic-e")
    _upload_klic(client, pid)
    upload = _haal_upload(db, pid)
    _verwerk(client, pid, upload.id)

    from app.project.models import KLICLeiding
    db.expire_all()
    sleufloze = (
        db.query(KLICLeiding)
        .filter_by(klic_upload_id=upload.id, sleufloze_techniek=True)
        .filter(KLICLeiding.beheerder.contains("Reggefiber"))
        .all()
    )
    assert len(sleufloze) >= 1, "Geen sleufloze leidingen gevonden voor Reggefiber"


# ── TC-klic-F: Alle 1127 leidingen → diepte_m IS NULL ────────────────────────

def test_klic_f_alle_leidingen_geen_diepte(client, db, workspace):
    pid = _maak_project(client, "klic-f")
    _upload_klic(client, pid)
    upload = _haal_upload(db, pid)
    _verwerk(client, pid, upload.id)

    from app.project.models import KLICLeiding
    db.expire_all()
    met_diepte = (
        db.query(KLICLeiding)
        .filter_by(klic_upload_id=upload.id)
        .filter(KLICLeiding.diepte_m.isnot(None))
        .count()
    )
    assert met_diepte == 0, f"{met_diepte} leidingen hebben onverwacht diepte_m != NULL"


# ── TC-klic-G: GET klic/status → diepte_waarschuwing=True als alle leidingen geen diepte ──

def test_klic_g_status_diepte_waarschuwing(client, db, workspace):
    pid = _maak_project(client, "klic-g")
    _upload_klic(client, pid)
    upload = _haal_upload(db, pid)
    _verwerk(client, pid, upload.id)

    resp = client.get(f"/api/v1/projecten/{pid}/klic/status", auth=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert data["verwerkt"] is True
    assert data["diepte_waarschuwing"] is True


# ── TC-klic-H: Minstens 95% van leidingen heeft geometrie_wkt niet None/leeg ──

def test_klic_h_geometrie_dekking(client, db, workspace):
    pid = _maak_project(client, "klic-h")
    _upload_klic(client, pid)
    upload = _haal_upload(db, pid)
    _verwerk(client, pid, upload.id)

    from app.project.models import KLICLeiding
    db.expire_all()
    leidingen = db.query(KLICLeiding).filter_by(klic_upload_id=upload.id).all()
    total = len(leidingen)
    assert total > 0

    met_wkt = sum(1 for l in leidingen if l.geometrie_wkt and l.geometrie_wkt.strip())
    dekking = met_wkt / total
    assert dekking >= 0.95, f"Geometrie dekking {dekking:.1%} < 95% (met_wkt={met_wkt}, totaal={total})"


# ── TC-klic-I: geometrie_wkt bevat geldige WKT: shapely.from_wkt() gooit geen exception ──

def test_klic_i_geldige_wkt(client, db, workspace):
    pid = _maak_project(client, "klic-i")
    _upload_klic(client, pid)
    upload = _haal_upload(db, pid)
    _verwerk(client, pid, upload.id)

    from app.project.models import KLICLeiding
    db.expire_all()
    leidingen = (
        db.query(KLICLeiding)
        .filter_by(klic_upload_id=upload.id)
        .filter(KLICLeiding.geometrie_wkt.isnot(None))
        .limit(100)
        .all()
    )
    for l in leidingen:
        try:
            geom = from_wkt(l.geometrie_wkt)
            assert geom is not None, f"None geometrie voor {l.imkl_feature_id}"
        except Exception as exc:
            pytest.fail(f"Ongeldige WKT voor {l.imkl_feature_id}: {exc}\nWKT: {l.geometrie_wkt[:200]}")


# ── TC-klic-J: Leidingen in RD-bereik NL: x ∈ [0, 300000], y ∈ [300000, 625000] ──

def test_klic_j_rd_bereik(client, db, workspace):
    pid = _maak_project(client, "klic-j")
    _upload_klic(client, pid)
    upload = _haal_upload(db, pid)
    _verwerk(client, pid, upload.id)

    from app.project.models import KLICLeiding
    db.expire_all()
    leidingen = (
        db.query(KLICLeiding)
        .filter_by(klic_upload_id=upload.id)
        .filter(KLICLeiding.geometrie_wkt.isnot(None))
        .all()
    )
    buiten_bereik = 0
    for l in leidingen:
        try:
            geom = from_wkt(l.geometrie_wkt)
            bounds = geom.bounds  # (minx, miny, maxx, maxy)
            if not (0 <= bounds[0] <= 300000 and 0 <= bounds[2] <= 300000 and
                    300000 <= bounds[1] <= 625000 and 300000 <= bounds[3] <= 625000):
                buiten_bereik += 1
        except Exception:
            continue
    assert buiten_bereik == 0, f"{buiten_bereik} leidingen buiten RD-bereik NL"


# ── TC-klic-K: DXF na KLIC → laag "LAAGSPANNING" bevat minstens 1 LWPolyline ──

def test_klic_k_dxf_laagspanning_polylines(client, db, workspace):
    import ezdxf
    from app.documents.dxf_generator import generate_dxf
    from app.project.models import Project, TracePunt, KLICUpload

    pid = _maak_project(client, "klic-k")
    _upload_klic(client, pid)
    upload = _haal_upload(db, pid)
    _verwerk(client, pid, upload.id)

    db.expire_all()
    project = db.get(Project, pid)
    dxf_bytes = generate_dxf(project, db=db)
    doc = ezdxf.read(io.StringIO(dxf_bytes.decode("utf-8")))
    msp = doc.modelspace()

    ls_polylines = [e for e in msp if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "LAAGSPANNING"]
    assert len(ls_polylines) >= 1, "Geen LWPolylines op laag LAAGSPANNING"


# ── TC-klic-L: DXF na KLIC → alle bestaande lagen nog aanwezig (geen regressie) ──

def test_klic_l_dxf_geen_regressie(client, db, workspace):
    import ezdxf
    from app.documents.dxf_generator import generate_dxf, LAYERS
    from app.project.models import Project

    pid = _maak_project(client, "klic-l")
    _upload_klic(client, pid)
    upload = _haal_upload(db, pid)
    _verwerk(client, pid, upload.id)

    db.expire_all()
    project = db.get(Project, pid)
    dxf_bytes = generate_dxf(project, db=db)
    doc = ezdxf.read(io.StringIO(dxf_bytes.decode("utf-8")))

    for layer_naam in LAYERS:
        assert layer_naam in doc.layers, f"Laag {layer_naam} ontbreekt na KLIC"


# ── TC-klic-M: POST verwerken met niet-bestaande upload_id → 404 ─────────────

def test_klic_m_onbekende_upload_404(client, db, workspace):
    pid = _maak_project(client, "klic-m")
    resp = client.post(
        f"/api/v1/projecten/{pid}/klic/niet-bestaande-upload-id/verwerken",
        auth=AUTH,
        follow_redirects=False,
    )
    assert resp.status_code == 404


# ── TC-klic-N: Brondata-pagina toont tabel met beheerders na verwerking ───────

def test_klic_n_brondata_toont_tabel(client, db, workspace):
    pid = _maak_project(client, "klic-n")
    _upload_klic(client, pid)
    upload = _haal_upload(db, pid)
    _verwerk(client, pid, upload.id)

    resp = client.get(f"/api/v1/projecten/{pid}/brondata", auth=AUTH)
    assert resp.status_code == 200
    html = resp.text
    # Tabel met beheerders moet aanwezig zijn
    assert "<table" in html.lower(), "Geen tabel op brondata-pagina"
    assert "Liander" in html or "liander" in html.lower(), "Liander niet in tabel"


# ── TC-klic-O: Verwerking twee keer aanroepen → geen duplicaten ───────────────

def test_klic_o_geen_duplicaten(client, db, workspace):
    pid = _maak_project(client, "klic-o")
    _upload_klic(client, pid)
    upload = _haal_upload(db, pid)

    # Eerste verwerking
    _verwerk(client, pid, upload.id)
    from app.project.models import KLICLeiding
    db.expire_all()
    count1 = db.query(KLICLeiding).filter_by(klic_upload_id=upload.id).count()

    # Tweede verwerking
    _verwerk(client, pid, upload.id)
    db.expire_all()
    count2 = db.query(KLICLeiding).filter_by(klic_upload_id=upload.id).count()

    assert count1 == count2, f"Duplicaten na tweede verwerking: {count1} vs {count2}"


# ── TC-klic-P: ZIP zonder GML → verwerk_fout beschrijvend, verwerkt=False, geen crash ──

def test_klic_p_zip_zonder_gml(client, db, workspace):
    pid = _maak_project(client, "klic-p")

    # Maak een ZIP zonder GML-bestanden
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

    upload = _haal_upload(db, pid)
    assert upload is not None

    # Verwerk de lege ZIP
    resp2 = client.post(
        f"/api/v1/projecten/{pid}/klic/{upload.id}/verwerken",
        auth=AUTH,
        follow_redirects=True,
    )
    assert resp2.status_code == 200

    db.expire_all()
    upload = _haal_upload(db, pid)
    assert upload.verwerkt is False
    assert upload.verwerk_fout is not None
    assert len(upload.verwerk_fout) > 0
