"""TC-bron — Module 4: brondata overrides"""
import io

from tests.conftest import AUTH


def _maak_order_boring(client, db, naam="HDD-bron-test"):
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


# TC-bron-A: KLIC ZIP uploaden → bestand opgeslagen, verwerkt=False
def test_bron_a_klic_upload(client, db, workspace):
    order_id, volgnr = _maak_order_boring(client, db, "HDD-klic-a")
    zip_content = b"PK\x03\x04"  # minimale ZIP header
    resp = client.post(
        f"/orders/{order_id}/klic",
        files={"klic_zip": ("Levering_test.zip", io.BytesIO(zip_content), "application/zip")},
        auth=AUTH,
        follow_redirects=True,
    )
    assert resp.status_code == 200

    from app.order.models import KLICUpload
    db.expire_all()
    upload = db.query(KLICUpload).filter_by(order_id=order_id).first()
    assert upload is not None
    assert upload.bestandsnaam == "Levering_test.zip"
    assert upload.verwerkt is False


# TC-bron-B: MVin=+1.01 MVuit=+1.27 (HDD11) → opgeslagen, bron=handmatig
def test_bron_b_maaiveld_hdd11(client, db, workspace):
    order_id, volgnr = _maak_order_boring(client, db, "HDD-mv-b")
    resp = client.post(
        f"/orders/{order_id}/boringen/{volgnr}/maaiveld",
        data={"MVin_NAP_m": "1.01", "MVuit_NAP_m": "1.27"},
        auth=AUTH,
        follow_redirects=True,
    )
    assert resp.status_code == 200

    from app.order.models import MaaiveldOverride, Boring
    db.expire_all()
    boring = db.query(Boring).filter_by(order_id=order_id, volgnummer=volgnr).first()
    mv = db.query(MaaiveldOverride).filter_by(boring_id=boring.id).first()
    assert mv.MVin_NAP_m == 1.01
    assert mv.MVuit_NAP_m == 1.27
    assert mv.bron == "handmatig"


# TC-bron-C: 6 doorsneden HDD11 invoeren → volgorde correct
def test_bron_c_doorsneden_hdd11(client, db, workspace):
    order_id, volgnr = _maak_order_boring(client, db, "HDD-ds-c")
    # 6 doorsneden conform BerekeningHDD11
    afstanden = "0,45,90,135,180,226.58"
    naps = "-1.0,-1.5,-2.0,-2.5,-2.0,-1.5"
    grondtypen = "Zand,Zand,Klei,Klei,Zand,Zand"

    resp = client.post(
        f"/orders/{order_id}/boringen/{volgnr}/doorsneden",
        data={"afstand_list": afstanden, "NAP_list": naps, "grondtype_list": grondtypen},
        auth=AUTH,
        follow_redirects=True,
    )
    assert resp.status_code == 200

    from app.order.models import Doorsnede, Boring
    db.expire_all()
    boring = db.query(Boring).filter_by(order_id=order_id, volgnummer=volgnr).first()
    dss = db.query(Doorsnede).filter_by(boring_id=boring.id).order_by(Doorsnede.volgorde).all()
    assert len(dss) == 6
    assert dss[0].afstand_m == 0.0
    assert dss[-1].afstand_m == 226.58


# TC-bron-D: Ttot=30106 N (HDD11) → opgeslagen als override
def test_bron_d_intrekkracht_hdd11(client, db, workspace):
    order_id, volgnr = _maak_order_boring(client, db, "HDD-ik-d")
    resp = client.post(
        f"/orders/{order_id}/boringen/{volgnr}/intrekkracht",
        data={"Ttot_N": "30106"},
        auth=AUTH,
        follow_redirects=True,
    )
    assert resp.status_code == 200

    from app.order.models import Berekening, Boring
    db.expire_all()
    boring = db.query(Boring).filter_by(order_id=order_id, volgnummer=volgnr).first()
    b = db.query(Berekening).filter_by(boring_id=boring.id).first()
    assert b.Ttot_N == 30106.0
    assert b.bron == "sigma_override"
