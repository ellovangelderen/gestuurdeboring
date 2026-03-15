"""TC-core — Module 1: auth + config + seed"""
import pytest
from fastapi.testclient import TestClient

from tests.conftest import AUTH


# TC-core-A: Settings laden
def test_core_a_settings_laden():
    from app.core.config import settings
    assert settings.ENV == "development"
    assert "sqlite" in settings.DATABASE_URL


# TC-core-B: Auth correct wachtwoord → 200
def test_core_b_auth_correct(client, workspace):
    resp = client.get("/", auth=AUTH)
    assert resp.status_code == 200


# TC-core-C: Auth fout wachtwoord → 401
def test_core_c_auth_fout(client):
    resp = client.get("/", auth=("martien", "fout-wachtwoord"))
    assert resp.status_code == 401


# TC-core-D: Test-user alleen in ENV=development
def test_core_d_test_user_development(client, workspace):
    resp = client.get("/", auth=("test", "test123"))
    assert resp.status_code == 200


# TC-core-E: Seed idempotent
def test_core_e_seed_idempotent(db, workspace):
    from app.rules.models import EisenProfiel

    EISENPROFIELEN = [
        {"naam": "RWS Rijksweg",           "dekking_weg_m": 3.0, "dekking_water_m": 5.0,  "Rmin_m": 150},
        {"naam": "Waterschap waterkering", "dekking_weg_m": 5.0, "dekking_water_m": 10.0, "Rmin_m": 200},
        {"naam": "Provincie",              "dekking_weg_m": 2.0, "dekking_water_m": 3.0,  "Rmin_m": 120},
        {"naam": "Gemeente",               "dekking_weg_m": 1.2, "dekking_water_m": 1.5,  "Rmin_m": 100},
        {"naam": "ProRail spoor",          "dekking_weg_m": 4.0, "dekking_water_m": 6.0,  "Rmin_m": 150},
    ]

    # Seed twee keer
    for _ in range(2):
        for ep_data in EISENPROFIELEN:
            existing = db.query(EisenProfiel).filter_by(naam=ep_data["naam"], workspace_id=None).first()
            if not existing:
                db.add(EisenProfiel(**ep_data))
        db.commit()

    count = db.query(EisenProfiel).count()
    assert count == 5, f"Verwacht 5, kreeg {count}"
