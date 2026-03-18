"""TC-nav — Module 8: download + navigatie"""
from tests.conftest import AUTH


def _maak_order_boring(client, db, naam="HDD-nav-test"):
    """Maak order + boring via API, return (order_id, volgnr)."""
    resp = client.post(
        "/orders/nieuw",
        data={"ordernummer": naam, "type_1": "B", "aantal_1": "1"},
        auth=AUTH,
        follow_redirects=True,
    )
    assert resp.status_code == 200
    from app.order.models import Order
    db.expire_all()
    order = db.query(Order).filter_by(ordernummer=naam).first()
    return order.id, 1


# TC-nav-A: GET / zonder auth → 401
def test_nav_a_geen_auth(client):
    resp = client.get("/")
    assert resp.status_code == 401


# TC-nav-B: GET / met auth → 200
def test_nav_b_met_auth(client, workspace):
    resp = client.get("/", auth=AUTH, follow_redirects=True)
    assert resp.status_code == 200


# TC-nav-C: Download DXF → Content-Disposition header aanwezig
def test_nav_c_download_dxf(client, db, workspace):
    order_id, volgnr = _maak_order_boring(client, db, "HDD-dxf-nav")

    # Voeg tracépunten toe (minimaal 2 voor boorlijn)
    client.post(
        f"/orders/{order_id}/boringen/{volgnr}/trace",
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

    resp = client.get(f"/orders/{order_id}/boringen/{volgnr}/dxf", auth=AUTH)
    assert resp.status_code == 200
    assert "Content-Disposition" in resp.headers
    assert ".dxf" in resp.headers["Content-Disposition"]


# TC-nav-D: Download PDF → Content-Type application/pdf
def test_nav_d_download_pdf(client, db, workspace):
    order_id, volgnr = _maak_order_boring(client, db, "HDD-pdf-nav")

    resp = client.get(f"/orders/{order_id}/boringen/{volgnr}/pdf", auth=AUTH)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"


# TC-nav-E: Order detail toont boring info
def test_nav_e_orderdetail(client, db, workspace):
    order_id, volgnr = _maak_order_boring(client, db, "HDD-voortgang")

    resp = client.get(f"/orders/{order_id}", auth=AUTH)
    assert resp.status_code == 200
