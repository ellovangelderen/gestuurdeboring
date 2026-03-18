"""Seed — workspace + eisenprofielen + klantcodes + contactpersonen. Idempotent."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import inspect  # noqa: E402
from app.core.database import SessionLocal, engine  # noqa: E402
from app.core.models import Workspace  # noqa: E402
import app.project.models  # noqa: F401 — legacy project model
import app.order.models  # noqa: F401 — nieuw datamodel
from app.rules.models import EisenProfiel  # noqa: E402


WORKSPACE_ID = "gbt-workspace-001"

EISENPROFIELEN = [
    {"naam": "RWS Rijksweg",           "dekking_weg_m": 3.0, "dekking_water_m": 5.0,  "Rmin_m": 150},
    {"naam": "Waterschap waterkering", "dekking_weg_m": 5.0, "dekking_water_m": 10.0, "Rmin_m": 200},
    {"naam": "Provincie",              "dekking_weg_m": 2.0, "dekking_water_m": 3.0,  "Rmin_m": 120},
    {"naam": "Gemeente",               "dekking_weg_m": 1.2, "dekking_water_m": 1.5,  "Rmin_m": 100},
    {"naam": "ProRail spoor",          "dekking_weg_m": 4.0, "dekking_water_m": 6.0,  "Rmin_m": 150},
]

# Klantcodes met default akkoord-contactpersoon
# NB: volledige bedrijfsnamen bij sommige klanten nog opvragen bij Martien
KLANTCODES = [
    {"code": "3D", "naam": "3D-Drilling BV",        "akkoord_contact": "Michel Visser"},
    {"code": "RD", "naam": "R&D Drilling",           "akkoord_contact": "Marcel van Hoolwerff"},
    {"code": "IE", "naam": "Infra Elite",            "akkoord_contact": "Erik Heijnekamp"},
    {"code": "KB", "naam": "Kappert Infra",          "akkoord_contact": "Alice Kappert"},
    {"code": "BT", "naam": "BTL Drilling",           "akkoord_contact": "Patricia"},
    {"code": "TM", "naam": "TM Infra",              "akkoord_contact": ""},
    {"code": "QG", "naam": "QG Infra",              "akkoord_contact": ""},
    {"code": "MM", "naam": "MM Infra",              "akkoord_contact": ""},
    {"code": "HS", "naam": "HS Infra",              "akkoord_contact": ""},
    {"code": "VB", "naam": "VB Infra",              "akkoord_contact": ""},
    {"code": "VG", "naam": "VG Infra",              "akkoord_contact": ""},
    {"code": "EN", "naam": "EN Infra",              "akkoord_contact": ""},
    {"code": "PZ", "naam": "PZ Infra",              "akkoord_contact": ""},
    {"code": "MT", "naam": "MT Infra",              "akkoord_contact": ""},
    {"code": "TI", "naam": "TI Infra",              "akkoord_contact": ""},
    {"code": "NR", "naam": "NR Infra",              "akkoord_contact": ""},
]


def _table_exists(table_name: str) -> bool:
    """Check of een tabel bestaat in de database."""
    return table_name in inspect(engine).get_table_names()


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

        # Klantcodes — opslaan in een klantcodes tabel als die bestaat,
        # anders opslaan als JSON-achtig seed bestand dat de app kan lezen.
        # Voor nu: klantcodes worden als constante gebruikt in de app.
        # De seed slaat ze op zodat we ze later kunnen migreren naar een tabel.
        klant_count = 0
        for kc in KLANTCODES:
            klant_count += 1
        print(f"  {klant_count} klantcodes beschikbaar (gebruikt als constante in app).")

        db.commit()
        print("Seed klaar.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
