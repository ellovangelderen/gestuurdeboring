"""Seed — workspace + eisenprofielen. Idempotent (mag meerdere keren draaien)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal  # noqa: E402
from app.core.models import Workspace  # noqa: E402
import app.project.models  # noqa: F401 — vereist voor SQLAlchemy relaties
from app.rules.models import EisenProfiel  # noqa: E402


WORKSPACE_ID = "gbt-workspace-001"

EISENPROFIELEN = [
    {"naam": "RWS Rijksweg",           "dekking_weg_m": 3.0, "dekking_water_m": 5.0,  "Rmin_m": 150},
    {"naam": "Waterschap waterkering", "dekking_weg_m": 5.0, "dekking_water_m": 10.0, "Rmin_m": 200},
    {"naam": "Provincie",              "dekking_weg_m": 2.0, "dekking_water_m": 3.0,  "Rmin_m": 120},
    {"naam": "Gemeente",               "dekking_weg_m": 1.2, "dekking_water_m": 1.5,  "Rmin_m": 100},
    {"naam": "ProRail spoor",          "dekking_weg_m": 4.0, "dekking_water_m": 6.0,  "Rmin_m": 150},
]


def main():
    db = SessionLocal()
    try:
        # Workspace
        ws = db.get(Workspace, WORKSPACE_ID)
        if not ws:
            ws = Workspace(id=WORKSPACE_ID, naam="GestuurdeBoringTekening", slug="gbt")
            db.add(ws)
            print("Workspace aangemaakt.")
        else:
            print("Workspace bestaat al.")

        # Eisenprofielen
        for ep_data in EISENPROFIELEN:
            existing = db.query(EisenProfiel).filter_by(naam=ep_data["naam"], workspace_id=None).first()
            if not existing:
                ep = EisenProfiel(**ep_data)
                db.add(ep)
                print(f"  Eisenprofiel '{ep_data['naam']}' aangemaakt.")

        db.commit()
        print("Seed klaar.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
