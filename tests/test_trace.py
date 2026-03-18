"""TC-trace — Module 3: tracépunten + RD→WGS84"""
import pytest


def _maak_order_boring(client, db, naam="HDD-test"):
    """Maak order + boring via API, return (order_id, volgnr)."""
    from tests.conftest import AUTH
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


# TC-trace-A: RD (103896.9, 489289.5) → WGS84 correcte locatie (HDD11 punt A)
def test_trace_a_rd_naar_wgs84_hdd11_a():
    from app.geo.coords import rd_to_wgs84
    lat, lon = rd_to_wgs84(103896.9, 489289.5)
    # Haarlem Kennemerplein — verwacht ~52.38°N, ~4.63°E
    assert 52.37 < lat < 52.40, f"Lat buiten verwacht bereik: {lat}"
    assert 4.60 < lon < 4.67, f"Lon buiten verwacht bereik: {lon}"


# TC-trace-B: Alle 8 HDD11 GPS punten → correcte WGS84 (geen grote afwijkingen)
def test_trace_b_hdd11_alle_gps_punten():
    from app.geo.coords import rd_to_wgs84

    hdd11_punten = [
        (103896.9, 489289.5, "A"),
        (103916.4, 489284.1, "Tv1"),
        (103934.3, 489279.1, "Tv2"),
        (103947.3, 489275.5, "Th1"),
        (103960.8, 489272.4, "Th2"),
        (104079.7, 489250.8, "Tv3"),
        (104109.2, 489245.5, "Tv4"),
        (104118.8, 489243.7, "B"),
    ]

    for x, y, label in hdd11_punten:
        lat, lon = rd_to_wgs84(x, y)
        assert 52.0 < lat < 53.0, f"{label}: lat {lat} buiten bereik"
        assert 4.0 < lon < 5.5, f"{label}: lon {lon} buiten bereik"


# TC-trace-C: Tussenpunt met Rh=150m → opgeslagen
def test_trace_c_tussenpunt_opgeslagen(client, db, workspace):
    from tests.conftest import AUTH

    order_id, volgnr = _maak_order_boring(client, db, "HDD-trace-c")

    # Sla tracé op
    resp = client.post(
        f"/orders/{order_id}/boringen/{volgnr}/trace",
        data={
            "RD_x_list": "103896.9,103934.3,104118.8",
            "RD_y_list": "489289.5,489279.1,489243.7",
            "type_list": "intree,tussenpunt,uittree",
            "label_list": "A,Tv2,B",
            "Rh_list": ",150,",
        },
        auth=AUTH,
        follow_redirects=True,
    )
    assert resp.status_code == 200

    from app.order.models import TracePunt, Boring
    db.expire_all()
    boring = db.query(Boring).filter_by(order_id=order_id, volgnummer=volgnr).first()
    punten = db.query(TracePunt).filter_by(boring_id=boring.id).order_by(TracePunt.volgorde).all()
    tussenpunt = next(p for p in punten if p.type == "tussenpunt")
    assert tussenpunt.Rh_m == 150.0


# TC-trace-D: Volgorde behouden
def test_trace_d_volgorde(client, db, workspace):
    from tests.conftest import AUTH

    order_id, volgnr = _maak_order_boring(client, db, "HDD-trace-d")

    client.post(
        f"/orders/{order_id}/boringen/{volgnr}/trace",
        data={
            "RD_x_list": "103896.9,103916.4,103934.3,104118.8",
            "RD_y_list": "489289.5,489284.1,489279.1,489243.7",
            "type_list": "intree,tussenpunt,tussenpunt,uittree",
            "label_list": "A,Tv1,Tv2,B",
            "Rh_list": ",,150,",
        },
        auth=AUTH,
        follow_redirects=True,
    )

    from app.order.models import TracePunt, Boring
    db.expire_all()
    boring = db.query(Boring).filter_by(order_id=order_id, volgnummer=volgnr).first()
    punten = db.query(TracePunt).filter_by(boring_id=boring.id).order_by(TracePunt.volgorde).all()
    labels = [p.label for p in punten]
    assert labels == ["A", "Tv1", "Tv2", "B"]


# TC-trace-E: HDD28 sensorpunt Tv1(105315, 498805) → kaartlocatie klopt (Velsen-Noord)
def test_trace_e_hdd28_tv1():
    from app.geo.coords import rd_to_wgs84
    lat, lon = rd_to_wgs84(105315, 498805)
    # Velsen-Noord ~52.46°N, ~4.67°E
    assert 52.44 < lat < 52.49, f"Lat buiten verwacht bereik: {lat}"
    assert 4.64 < lon < 4.72, f"Lon buiten verwacht bereik: {lon}"
