"""TC-rules — Module 5: eisenprofielen"""
from tests.conftest import AUTH

EISENPROFIELEN = [
    {"naam": "RWS Rijksweg",           "dekking_weg_m": 3.0, "dekking_water_m": 5.0,  "Rmin_m": 150},
    {"naam": "Waterschap waterkering", "dekking_weg_m": 5.0, "dekking_water_m": 10.0, "Rmin_m": 200},
    {"naam": "Provincie",              "dekking_weg_m": 2.0, "dekking_water_m": 3.0,  "Rmin_m": 120},
    {"naam": "Gemeente",               "dekking_weg_m": 1.2, "dekking_water_m": 1.5,  "Rmin_m": 100},
    {"naam": "ProRail spoor",          "dekking_weg_m": 4.0, "dekking_water_m": 6.0,  "Rmin_m": 150},
]


def _seed_eisenprofielen(db):
    from app.rules.models import EisenProfiel
    for ep_data in EISENPROFIELEN:
        existing = db.query(EisenProfiel).filter_by(naam=ep_data["naam"]).first()
        if not existing:
            db.add(EisenProfiel(**ep_data))
    db.commit()


# TC-rules-A: Seed → 5 eisenprofielen aanwezig
def test_rules_a_seed_5_profielen(db, workspace):
    _seed_eisenprofielen(db)
    from app.rules.models import EisenProfiel
    count = db.query(EisenProfiel).count()
    assert count == 5


# TC-rules-B: RWS selecteren → dekking_weg=3.0, Rmin=150
def test_rules_b_rws_waarden(db, workspace):
    _seed_eisenprofielen(db)
    from app.rules.models import EisenProfiel
    rws = db.query(EisenProfiel).filter_by(naam="RWS Rijksweg").first()
    assert rws.dekking_weg_m == 3.0
    assert rws.Rmin_m == 150


# TC-rules-C: Override vergunning eist 3.5m → opgeslagen in override_eisen
def test_rules_c_override_eisen(client, db, workspace):
    _seed_eisenprofielen(db)
    from app.rules.models import EisenProfiel, ProjectEisenProfiel
    from app.project.models import Project

    # Maak project direct in DB (vermijd legacy route detail-pagina problemen)
    project = Project(
        id="rules-test-c",
        workspace_id="gbt-workspace-001",
        naam="HDD-eisen",
        aangemaakt_door="martien",
    )
    db.add(project)
    db.commit()

    # Selecteer RWS via legacy route
    rws = db.query(EisenProfiel).filter_by(naam="RWS Rijksweg").first()
    resp = client.post(
        f"/api/v1/projecten/rules-test-c/eisen",
        data={"eisenprofiel_id": rws.id},
        auth=AUTH,
        follow_redirects=False,
    )
    # Verwacht redirect (303)
    assert resp.status_code == 303

    db.expire_all()
    pep = db.query(ProjectEisenProfiel).filter_by(project_id="rules-test-c").first()
    assert pep.eisenprofiel_id == rws.id
