"""TC-proj — Module 2: Project CRUD"""
import pytest

from tests.conftest import AUTH


# TC-proj-A: Project aanmaken → opgeslagen, redirect naar detail
def test_proj_a_aanmaken(client, workspace):
    resp = client.post(
        "/api/v1/projecten/nieuw",
        data={"naam": "HDD11 Haarlem Kennemerplein", "ordernummer": "3D25V700"},
        auth=AUTH,
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "HDD11 Haarlem Kennemerplein" in resp.text


# TC-proj-B: SDR=11, De=160 → dn_berekend=14.5, Di≈131.0
def test_proj_b_dn_berekening():
    from app.project.models import Project
    p = Project(naam="Test", workspace_id="x", SDR=11, De_mm=160.0)
    assert p.dn_berekend == 14.5
    # Di = 160 - 2 * 14.5 = 131.0
    assert p.Di_mm == 131.0


# TC-proj-C: HDD11 — dn=14.6 conform BerekeningHDD11 p.5
def test_proj_c_dn_handmatig_hdd11():
    from app.project.models import Project
    p = Project(naam="HDD11", workspace_id="x", SDR=11, De_mm=160.0, dn_mm=14.6)
    assert p.dn_effectief == 14.6
    assert p.Di_mm == pytest.approx(160.0 - 2 * 14.6, abs=0.01)


# TC-proj-D: Verplicht veld 'naam' leeg → validatiefout (422 of form-redirect)
def test_proj_d_naam_verplicht(client, workspace):
    resp = client.post(
        "/api/v1/projecten/nieuw",
        data={"naam": ""},
        auth=AUTH,
        follow_redirects=False,
    )
    # FastAPI geeft 422 bij ontbrekend verplicht Form veld
    assert resp.status_code in (422, 400)


# TC-proj-E: Projectenlijst toont alle projecten van workspace
def test_proj_e_lijst(client, workspace):
    # Maak 2 projecten
    for naam in ["HDD11", "HDD28"]:
        client.post("/api/v1/projecten/nieuw", data={"naam": naam}, auth=AUTH, follow_redirects=True)

    resp = client.get("/", auth=AUTH)
    assert resp.status_code == 200
    assert "HDD11" in resp.text
    assert "HDD28" in resp.text
