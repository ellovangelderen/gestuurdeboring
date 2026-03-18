"""Seed volledige testdata — alle scenario's voor het HDD platform.

Idempotent: checkt of data al bestaat, maakt alleen aan wat ontbreekt.
Run: .venv/bin/python3 scripts/seed_full.py
"""
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal, Base, engine  # noqa: E402
import app.core.models  # noqa: F401
import app.project.models  # noqa: F401
import app.rules.models  # noqa: F401
from app.order.models import (  # noqa: E402
    Order, Boring, TracePunt, MaaiveldOverride,
    Doorsnede, Berekening, KLICUpload, EVPartij,
    EmailContact, AsBuiltPunt,
)
from app.core.models import Workspace  # noqa: E402

WORKSPACE_ID = "gbt-workspace-001"
now = datetime.now(timezone.utc)


def ensure_tables():
    """Maak ontbrekende tabellen aan."""
    Base.metadata.create_all(bind=engine)


def ensure_workspace(db):
    ws = db.query(Workspace).filter_by(id=WORKSPACE_ID).first()
    if not ws:
        db.add(Workspace(id=WORKSPACE_ID, naam="GestuurdeBoringTekening", slug="gbt"))
        db.commit()
        print("Workspace aangemaakt")


def order_exists(db, ordernummer):
    return db.query(Order).filter_by(ordernummer=ordernummer).first() is not None


def seed_hdd11(db):
    """HDD11 Haarlem Kennemerplein — primair referentieproject, volledig ingevuld."""
    if order_exists(db, "3D25V700"):
        print("[skip] 3D25V700 bestaat al")
        return

    order = Order(
        workspace_id=WORKSPACE_ID,
        ordernummer="3D25V700",
        locatie="Haarlem, Kennemerplein",
        klantcode="3D",
        opdrachtgever="3D-Drilling BV",
        status="in_progress",
        vergunning="P",
        tekenaar="martien",
        akkoord_contact="Michel Visser",
        prio=False,
        notitie="Primair referentieproject — HDD11. Werkplan voorbereiden.",
        ontvangen_op=datetime(2025, 9, 18, tzinfo=timezone.utc),
        deadline=datetime(2025, 10, 9, tzinfo=timezone.utc),
        google_maps_url="https://maps.app.goo.gl/QNtNwuXJBga7WiHs7",
    )
    db.add(order)
    db.flush()

    # Boring 01 — HDD11 type B
    b1 = Boring(
        order_id=order.id, volgnummer=1, type="B", naam="HDD11",
        materiaal="PE100", SDR=11, De_mm=160.0, dn_mm=14.6,
        medium="Drukloos", Db_mm=60.0, Dp_mm=110.0, Dg_mm=240.0,
        intreehoek_gr=18.0, uittreehoek_gr=22.0,
        aangemaakt_door="martien",
    )
    db.add(b1)
    db.flush()

    # 8 GPS sensorpunten
    for p in [
        (0, "intree",     103896.9, 489289.5, "A",   None),
        (1, "tussenpunt", 103916.4, 489284.1, "Tv1", None),
        (2, "tussenpunt", 103934.3, 489279.1, "Tv2", None),
        (3, "tussenpunt", 103947.3, 489275.5, "Th1", 150.0),
        (4, "tussenpunt", 103960.8, 489272.4, "Th2", 150.0),
        (5, "tussenpunt", 104079.7, 489250.8, "Tv3", None),
        (6, "tussenpunt", 104109.2, 489245.5, "Tv4", None),
        (7, "uittree",    104118.8, 489243.7, "B",   None),
    ]:
        db.add(TracePunt(boring_id=b1.id, volgorde=p[0], type=p[1],
                         RD_x=p[2], RD_y=p[3], label=p[4], Rh_m=p[5], variant=0))

    # Maaiveld
    db.add(MaaiveldOverride(
        boring_id=b1.id, MVin_NAP_m=0.916, MVuit_NAP_m=1.281,
        bron="ahn5", MVin_bron="ahn5", MVuit_bron="ahn5",
        MVin_ahn5_m=0.916, MVuit_ahn5_m=1.281,
    ))

    # 6 doorsneden
    for d in [
        (0, 0.0,    -3.5, "Zand", -1.0),
        (1, 45.0,   -5.2, "Zand", -1.2),
        (2, 90.0,   -6.0, "Klei", -1.5),
        (3, 135.0,  -5.8, "Klei", -1.3),
        (4, 180.0,  -5.0, "Zand", -1.1),
        (5, 226.58, -3.2, "Zand", -0.8),
    ]:
        db.add(Doorsnede(boring_id=b1.id, volgorde=d[0], afstand_m=d[1],
                         NAP_m=d[2], grondtype=d[3], GWS_m=d[4]))

    # Intrekkracht
    db.add(Berekening(boring_id=b1.id, Ttot_N=30106.0, bron="sigma_override"))

    # KLIC
    db.add(KLICUpload(
        order_id=order.id, meldingnummer="25O0136974", versie=1,
        type="orientatie", bestandsnaam="Levering_25O0136974_1.zip",
        bestandspad="uploads/klic/Levering_25O0136974_1.zip", verwerkt=False,
    ))

    # EV-partijen (uit Martien's XLS)
    db.add(EVPartij(order_id=order.id, naam="Ziggo", volgorde=1))
    db.add(EVPartij(order_id=order.id, naam="Colt", volgorde=2))
    db.add(EVPartij(order_id=order.id, naam="Gem. Haarlem (OVG)", volgorde=3))

    # Email contacten
    db.add(EmailContact(order_id=order.id, naam="Ziggo", volgorde=1))
    db.add(EmailContact(order_id=order.id, naam="Colt", volgorde=2))
    db.add(EmailContact(order_id=order.id, naam="Gem. Haarlem", volgorde=3))

    db.commit()
    print(f"[OK] 3D25V700 HDD11 — order + boring + 8 punten + maaiveld + 6 doorsneden + Ttot + KLIC + EV")


def seed_boogzinker(db):
    """Boogzinker testorder — type Z boring."""
    if order_exists(db, "BZ-TEST-001"):
        print("[skip] BZ-TEST-001 bestaat al")
        return

    order = Order(
        workspace_id=WORKSPACE_ID,
        ordernummer="BZ-TEST-001",
        locatie="Testlocatie Boogzinker",
        klantcode="3D",
        opdrachtgever="3D-Drilling BV",
        status="order_received",
        vergunning="-",
        tekenaar="martien",
        akkoord_contact="Michel Visser",
        ontvangen_op=now,
        deadline=now + timedelta(days=21),
    )
    db.add(order)
    db.flush()

    b = Boring(
        order_id=order.id, volgnummer=1, type="Z", naam="BZ1",
        materiaal="PE100", SDR=11, De_mm=110.0,
        medium="Drukloos", Dg_mm=165.0,
        booghoek_gr=10.0, stand=5,
        aangemaakt_door="martien",
    )
    db.add(b)
    db.flush()

    db.add(TracePunt(boring_id=b.id, volgorde=0, type="intree",
                     RD_x=155000.0, RD_y=463000.0, label="A", variant=0))
    db.add(TracePunt(boring_id=b.id, volgorde=1, type="uittree",
                     RD_x=155050.0, RD_y=463000.0, label="B", variant=0))

    db.add(MaaiveldOverride(
        boring_id=b.id, MVin_NAP_m=-0.5, MVuit_NAP_m=-0.3,
        bron="handmatig", MVin_bron="handmatig", MVuit_bron="handmatig",
    ))

    db.commit()
    print("[OK] BZ-TEST-001 — boogzinker Z, booghoek 10°, stand 5")


def seed_multi_boring(db):
    """Multi-boring order — 2 boringen (B+N) voor cockpit testen."""
    if order_exists(db, "IE26V001"):
        print("[skip] IE26V001 bestaat al")
        return

    order = Order(
        workspace_id=WORKSPACE_ID,
        ordernummer="IE26V001",
        locatie="Utrecht, Oudenoord",
        klantcode="IE",
        opdrachtgever="Infra Elite",
        status="waiting_for_approval",
        vergunning="W",
        tekenaar="martien",
        akkoord_contact="Erik Heijnekamp",
        prio=True,
        ontvangen_op=now - timedelta(days=14),
        deadline=now + timedelta(days=7),
        geleverd_op=now - timedelta(days=3),
    )
    db.add(order)
    db.flush()

    # Boring 1: type B
    b1 = Boring(
        order_id=order.id, volgnummer=1, type="B", naam="HDD1",
        materiaal="PE100", SDR=11, De_mm=200.0,
        medium="Drukloos", Dg_mm=300.0,
        intreehoek_gr=15.0, uittreehoek_gr=20.0,
        aangemaakt_door="martien",
    )
    db.add(b1)
    db.flush()

    db.add(TracePunt(boring_id=b1.id, volgorde=0, type="intree",
                     RD_x=136500.0, RD_y=456800.0, label="A", variant=0))
    db.add(TracePunt(boring_id=b1.id, volgorde=1, type="uittree",
                     RD_x=136650.0, RD_y=456780.0, label="B", variant=0))

    # Boring 2: type N
    b2 = Boring(
        order_id=order.id, volgnummer=2, type="N", naam="NANO1",
        materiaal="PE100", SDR=11, De_mm=63.0,
        medium="Glasvezel", Dg_mm=100.0,
        intreehoek_gr=25.0, uittreehoek_gr=25.0,
        aangemaakt_door="martien",
    )
    db.add(b2)
    db.flush()

    db.add(TracePunt(boring_id=b2.id, volgorde=0, type="intree",
                     RD_x=136510.0, RD_y=456810.0, label="A", variant=0))
    db.add(TracePunt(boring_id=b2.id, volgorde=1, type="uittree",
                     RD_x=136560.0, RD_y=456805.0, label="B", variant=0))

    db.commit()
    print("[OK] IE26V001 — 2 boringen (B+N), status wacht_akkoord, PRIO")


def seed_delivered_orders(db):
    """Geleverde orders voor statusmail testen."""
    orders_data = [
        ("RD26V010", "Amersfoort, Stadsring", "RD", "delivered",
         "R&D Drilling", "Marcel van Hoolwerff"),
        ("KB26V005", "Deventer, Brinkgreverweg", "KB", "delivered",
         "Kappert Infra", "Alice Kappert"),
        ("3D26V820", "Almere, Buitenring", "3D", "waiting_for_approval",
         "3D-Drilling BV", "Michel Visser"),
    ]
    for nr, loc, klant, status, opdr, contact in orders_data:
        if order_exists(db, nr):
            print(f"[skip] {nr} bestaat al")
            continue
        order = Order(
            workspace_id=WORKSPACE_ID,
            ordernummer=nr, locatie=loc, klantcode=klant,
            opdrachtgever=opdr, status=status,
            tekenaar="martien", akkoord_contact=contact,
            vergunning="-",
            ontvangen_op=now - timedelta(days=30),
            geleverd_op=now - timedelta(days=5) if status == "delivered" else None,
        )
        db.add(order)
        db.flush()
        db.add(Boring(order_id=order.id, volgnummer=1, type="B",
                       aangemaakt_door="martien"))
        db.commit()
        print(f"[OK] {nr} — {loc}, status={status}")


def seed_asbuilt(db):
    """As-Built punten voor HDD11 (als die boring bestaat)."""
    order = db.query(Order).filter_by(ordernummer="3D25V700").first()
    if not order:
        return
    boring = next((b for b in order.boringen if b.volgnummer == 1), None)
    if not boring:
        return
    if boring.asbuilt_punten:
        print("[skip] As-Built punten bestaan al voor HDD11")
        return

    # Werkelijke punten (licht afwijkend van ontwerp)
    for p in [
        (0, "A",   103897.2, 489289.8),
        (1, "Tv1", 103916.8, 489284.4),
        (2, "Tv2", 103934.0, 489279.5),
        (3, "Th1", 103947.6, 489275.2),
        (4, "Th2", 103961.1, 489272.1),
        (5, "Tv3", 104079.4, 489251.1),
        (6, "Tv4", 104109.5, 489245.2),
        (7, "B",   104118.5, 489243.4),
    ]:
        db.add(AsBuiltPunt(boring_id=boring.id, volgorde=p[0], label=p[1],
                            RD_x=p[2], RD_y=p[3]))

    boring.revisie = 1
    db.commit()
    print("[OK] As-Built punten voor HDD11 (8 punten, revisie 1)")


def main():
    ensure_tables()
    db = SessionLocal()
    try:
        ensure_workspace(db)
        print()
        seed_hdd11(db)
        seed_boogzinker(db)
        seed_multi_boring(db)
        seed_delivered_orders(db)
        seed_asbuilt(db)
        print()

        # Samenvatting
        totaal_orders = db.query(Order).count()
        totaal_boringen = db.query(Boring).count()
        totaal_punten = db.query(TracePunt).count()
        print(f"Database: {totaal_orders} orders, {totaal_boringen} boringen, {totaal_punten} tracepunten")
        print("Done.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
