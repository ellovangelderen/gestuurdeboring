"""Seed testdata — HDD11 Haarlem Kennemerplein als volledig testproject."""
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal  # noqa: E402
import app.core.models  # noqa: F401
import app.project.models  # noqa: F401
import app.rules.models  # noqa: F401
from app.order.models import (  # noqa: E402
    Order, Boring, TracePunt, MaaiveldOverride,
    Doorsnede, Berekening, KLICUpload,
)

WORKSPACE_ID = "gbt-workspace-001"


def main():
    db = SessionLocal()
    try:
        # Check if test order already exists
        existing = db.query(Order).filter_by(ordernummer="3D25V700").first()
        if existing:
            print("Testorder 3D25V700 bestaat al. Overslaan.")
            db.close()
            return

        # ── Order ──
        order = Order(
            workspace_id=WORKSPACE_ID,
            ordernummer="3D25V700",
            locatie="Haarlem, Kennemerplein",
            klantcode="3D",
            opdrachtgever="3D-Drilling BV",
            status="in_progress",
            vergunning="-",
            tekenaar="martien",
            akkoord_contact="Michel Visser",
            prio=False,
            notitie="Primair referentieproject — HDD11",
        )
        db.add(order)
        db.flush()
        print(f"Order aangemaakt: {order.ordernummer} ({order.id})")

        # ── Boring 01 (HDD11) ──
        boring = Boring(
            order_id=order.id,
            volgnummer=1,
            type="B",
            naam="HDD11",
            materiaal="PE100",
            SDR=11,
            De_mm=160.0,
            dn_mm=14.6,  # conform BerekeningHDD11
            medium="Drukloos",
            Db_mm=60.0,
            Dp_mm=110.0,
            Dg_mm=240.0,
            intreehoek_gr=18.0,
            uittreehoek_gr=22.0,
            aangemaakt_door="test",
        )
        db.add(boring)
        db.flush()
        print(f"  Boring {boring.volgnummer:02d} ({boring.type}) aangemaakt: {boring.naam}")

        # ── TracePunten (8 GPS punten HDD11 rev.1) ──
        punten = [
            {"volgorde": 0, "type": "intree",     "RD_x": 103896.9, "RD_y": 489289.5, "label": "A",   "Rh_m": None},
            {"volgorde": 1, "type": "tussenpunt",  "RD_x": 103916.4, "RD_y": 489284.1, "label": "Tv1", "Rh_m": None},
            {"volgorde": 2, "type": "tussenpunt",  "RD_x": 103934.3, "RD_y": 489279.1, "label": "Tv2", "Rh_m": None},
            {"volgorde": 3, "type": "tussenpunt",  "RD_x": 103947.3, "RD_y": 489275.5, "label": "Th1", "Rh_m": 150.0},
            {"volgorde": 4, "type": "tussenpunt",  "RD_x": 103960.8, "RD_y": 489272.4, "label": "Th2", "Rh_m": 150.0},
            {"volgorde": 5, "type": "tussenpunt",  "RD_x": 104079.7, "RD_y": 489250.8, "label": "Tv3", "Rh_m": None},
            {"volgorde": 6, "type": "tussenpunt",  "RD_x": 104109.2, "RD_y": 489245.5, "label": "Tv4", "Rh_m": None},
            {"volgorde": 7, "type": "uittree",     "RD_x": 104118.8, "RD_y": 489243.7, "label": "B",   "Rh_m": None},
        ]
        for p in punten:
            tp = TracePunt(boring_id=boring.id, **p)
            db.add(tp)
        print(f"  {len(punten)} tracepunten aangemaakt")

        # ── Maaiveld ──
        mv = MaaiveldOverride(
            boring_id=boring.id,
            MVin_NAP_m=1.01,
            MVuit_NAP_m=1.27,
            bron="handmatig",
            MVin_bron="handmatig",
            MVuit_bron="handmatig",
        )
        db.add(mv)
        print("  Maaiveld override aangemaakt (MVin=+1.01, MVuit=+1.27)")

        # ── Doorsneden (6 stuks conform BerekeningHDD11) ──
        doorsneden_data = [
            {"volgorde": 0, "afstand_m": 0.0,    "NAP_m": -3.5,  "grondtype": "Zand",  "GWS_m": -1.0},
            {"volgorde": 1, "afstand_m": 45.0,   "NAP_m": -5.2,  "grondtype": "Zand",  "GWS_m": -1.2},
            {"volgorde": 2, "afstand_m": 90.0,   "NAP_m": -6.0,  "grondtype": "Klei",  "GWS_m": -1.5},
            {"volgorde": 3, "afstand_m": 135.0,  "NAP_m": -5.8,  "grondtype": "Klei",  "GWS_m": -1.3},
            {"volgorde": 4, "afstand_m": 180.0,  "NAP_m": -5.0,  "grondtype": "Zand",  "GWS_m": -1.1},
            {"volgorde": 5, "afstand_m": 226.58, "NAP_m": -3.2,  "grondtype": "Zand",  "GWS_m": -0.8},
        ]
        for d in doorsneden_data:
            ds = Doorsnede(boring_id=boring.id, **d)
            db.add(ds)
        print(f"  {len(doorsneden_data)} doorsneden aangemaakt")

        # ── Berekening (Sigma override) ──
        ber = Berekening(
            boring_id=boring.id,
            Ttot_N=30106.0,
            bron="sigma_override",
        )
        db.add(ber)
        print("  Berekening aangemaakt (Ttot=30.106 N)")

        # ── KLIC upload (placeholder, niet verwerkt) ──
        klic = KLICUpload(
            order_id=order.id,
            meldingnummer="25O0136974",
            versie=1,
            type="orientatie",
            bestandsnaam="Levering_25O0136974_1.zip",
            bestandspad="docs/input_data_14maart/Levering_25O0136974_1.zip",
            verwerkt=False,
        )
        db.add(klic)
        print("  KLIC upload aangemaakt (25O0136974, niet verwerkt)")

        db.commit()
        print("\nTestdata HDD11 compleet geladen.")
        print(f"Order ID: {order.id}")
        print(f"Boring ID: {boring.id}")
        print(f"\nOpen in browser: http://localhost:8000/orders/{order.id}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
