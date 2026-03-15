"""TC-nav — Module 8: download + navigatie"""
from tests.conftest import AUTH


# TC-nav-A: GET / zonder auth → 401
def test_nav_a_geen_auth(client):
    resp = client.get("/")
    assert resp.status_code == 401


# TC-nav-B: GET / met auth → 200
def test_nav_b_met_auth(client, workspace):
    resp = client.get("/", auth=AUTH)
    assert resp.status_code == 200


# TC-nav-C: Download DXF → Content-Disposition header aanwezig
def test_nav_c_download_dxf(client, workspace):
    # Maak project met tracépunten
    resp = client.post(
        "/api/v1/projecten/nieuw",
        data={"naam": "HDD-nav-test", "De_mm": "160", "Dg_mm": "240", "SDR": "11"},
        auth=AUTH,
        follow_redirects=True,
    )
    project_id = str(resp.url).split("/api/v1/projecten/")[1].rstrip("/").rstrip("/")

    # Voeg tracépunten toe (minimaal 2 voor boorlijn)
    client.post(
        f"/api/v1/projecten/{project_id}/trace",
        data={
            "RD_x_list": "103896.9,104118.8",
            "RD_y_list": "489289.5,489243.7",
            "type_list": "intree,uittree",
            "label_list": "A,B",
            "Rh_list": ",",
        },
        auth=AUTH,
        follow_redirects=True,
    )

    resp = client.get(f"/api/v1/projecten/{project_id}/dxf", auth=AUTH)
    assert resp.status_code == 200
    assert "Content-Disposition" in resp.headers
    assert ".dxf" in resp.headers["Content-Disposition"]


# TC-nav-D: Download PDF → Content-Type application/pdf
def test_nav_d_download_pdf(client, workspace):
    resp = client.post(
        "/api/v1/projecten/nieuw",
        data={"naam": "HDD-pdf-nav"},
        auth=AUTH,
        follow_redirects=True,
    )
    project_id = str(resp.url).split("/api/v1/projecten/")[1].rstrip("/").rstrip("/")

    resp = client.get(f"/api/v1/projecten/{project_id}/pdf", auth=AUTH)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"


# TC-nav-E: Projectdetail toont voortgangsstatus
def test_nav_e_projectdetail_voortgang(client, workspace):
    resp = client.post("/api/v1/projecten/nieuw", data={"naam": "HDD-voortgang"}, auth=AUTH, follow_redirects=True)
    project_id = str(resp.url).split("/api/v1/projecten/")[1].rstrip("/").rstrip("/")

    resp = client.get(f"/api/v1/projecten/{project_id}", auth=AUTH)
    assert resp.status_code == 200
    assert "Tracé invoeren" in resp.text
    assert "Brondata" in resp.text
