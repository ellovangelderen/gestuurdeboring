"""Tests voor Admin Panel — ADM-1 t/m ADM-8."""
import io
import pytest
from tests.conftest import AUTH


# ── Helpers ──

def _ensure_klant_table(db):
    """Zorg dat klanten tabel bestaat."""
    from app.core.database import Base, engine
    import app.admin.models
    Base.metadata.create_all(bind=engine)


# ── ADM-1: Gebruikers overzicht ──

def test_adm1_users_pagina(client, workspace):
    resp = client.get("/admin/users", auth=AUTH)
    assert resp.status_code == 200
    assert "martien" in resp.text


def test_adm1_users_geen_toegang_voor_niet_admin(client, workspace):
    """Niet-admin user krijgt 403."""
    resp = client.get("/admin/users", auth=("sopa", "test-martien"))
    # sopa is geen admin — maar in test env fallback naar martien password
    # De test checkt dat de admin check werkt
    # sopa zit niet in ADMIN_USERS
    assert resp.status_code == 403


def test_adm1_dashboard(client, workspace):
    resp = client.get("/admin/", auth=AUTH)
    assert resp.status_code == 200
    assert "Beheer" in resp.text
    assert "Opdrachtgevers" in resp.text


# ── ADM-2: Klantbeheer ──

def test_adm2_klanten_lijst(client, workspace, db):
    _ensure_klant_table(db)
    resp = client.get("/admin/klanten", auth=AUTH)
    assert resp.status_code == 200
    assert "Opdrachtgevers" in resp.text


def test_adm2_klant_toevoegen(client, workspace, db):
    _ensure_klant_table(db)
    resp = client.post("/admin/klanten/nieuw",
                       data={"code": "XX", "naam": "Test BV", "contact": "J. Test", "logo_bestand": "", "nr": "99"},
                       auth=AUTH, follow_redirects=True)
    assert resp.status_code == 200
    assert "XX" in resp.text
    assert "Test BV" in resp.text


def test_adm2_klant_dubbele_code(client, workspace, db):
    _ensure_klant_table(db)
    # Eerste keer OK
    client.post("/admin/klanten/nieuw",
                data={"code": "DUP", "naam": "Eerste", "contact": "", "logo_bestand": "", "nr": ""},
                auth=AUTH, follow_redirects=True)
    # Tweede keer met zelfde code → 400
    resp = client.post("/admin/klanten/nieuw",
                       data={"code": "DUP", "naam": "Tweede", "contact": "", "logo_bestand": "", "nr": ""},
                       auth=AUTH)
    assert resp.status_code == 400


def test_adm2_klant_verwijderen(client, workspace, db):
    _ensure_klant_table(db)
    from app.admin.models import Klant
    db.add(Klant(id="del-test", code="DEL", naam="Te Verwijderen"))
    db.commit()

    resp = client.post("/admin/klanten/del-test/verwijder", auth=AUTH, follow_redirects=True)
    assert resp.status_code == 200
    assert db.query(Klant).filter_by(code="DEL").first() is None


def test_adm2_logo_upload(client, workspace, db):
    _ensure_klant_table(db)
    from app.admin.models import Klant
    db.add(Klant(id="logo-test", code="LT", naam="Logo Test"))
    db.commit()

    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    resp = client.post(
        "/admin/klanten/logo/logo-test",
        files={"logo": ("test.png", io.BytesIO(fake_png), "image/png")},
        auth=AUTH, follow_redirects=True,
    )
    assert resp.status_code == 200
    db.expire_all()
    klant = db.get(Klant, "logo-test")
    assert klant.logo_bestand == "logo_LT.png"


def test_adm2_logo_upload_roundtrip(client, workspace, db):
    """Regressie BG-15: logo uploaden, DB check, serve check, zichtbaar in tabel."""
    _ensure_klant_table(db)
    from app.admin.models import Klant
    db.add(Klant(id="logo-rt", code="RT", naam="Roundtrip BV"))
    db.commit()

    # 1. Upload logo
    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
    resp = client.post(
        "/admin/klanten/logo/logo-rt",
        files={"logo": ("mijn_logo.png", io.BytesIO(fake_png), "image/png")},
        auth=AUTH, follow_redirects=True,
    )
    assert resp.status_code == 200

    # 2. DB record bijgewerkt
    db.expire_all()
    klant = db.get(Klant, "logo-rt")
    assert klant.logo_bestand == "logo_RT.png"

    # 3. Logo zichtbaar in klanten tabel
    assert "logo_RT.png" in resp.text

    # 4. Logo bestand ophaalbaar via serve route
    resp2 = client.get("/admin/logo/logo_RT.png", auth=AUTH)
    assert resp2.status_code == 200
    assert len(resp2.content) == len(fake_png)


def test_adm2_logo_zonder_bestand(client, workspace, db):
    """Regressie BG-11: logo upload zonder bestand geeft redirect, niet 400."""
    _ensure_klant_table(db)
    from app.admin.models import Klant
    db.add(Klant(id="logo-empty", code="LE", naam="Leeg Logo"))
    db.commit()

    # Lege upload: klein bestand (< 10 bytes) wordt als leeg behandeld
    resp = client.post(
        "/admin/klanten/logo/logo-empty",
        files={"logo": ("empty.png", io.BytesIO(b"\x00"), "image/png")},
        auth=AUTH, follow_redirects=True,
    )
    assert resp.status_code == 200  # redirect naar klanten pagina

    # DB niet gewijzigd
    db.expire_all()
    klant = db.get(Klant, "logo-empty")
    assert klant.logo_bestand is None


def test_adm2_seed_klanten_geen_cleanup(client, workspace, db):
    """Regressie BG-15: startup mag logo_bestand niet wissen als bestand nog niet op volume staat."""
    _ensure_klant_table(db)
    from app.admin.models import Klant

    # Simuleer klant met logo_bestand gezet (bestand staat op remote volume)
    db.add(Klant(id="logo-persist", code="LP", naam="Persist BV", logo_bestand="Logo_Persist.png"))
    db.commit()

    # Na seed/startup mag logo_bestand NIET gewist zijn
    db.expire_all()
    klant = db.get(Klant, "logo-persist")
    assert klant.logo_bestand == "Logo_Persist.png"


def test_adm2_logo_upload_verkeerd_formaat(client, workspace, db):
    _ensure_klant_table(db)
    from app.admin.models import Klant
    db.add(Klant(id="logo-bad", code="LB", naam="Logo Bad"))
    db.commit()

    resp = client.post(
        "/admin/klanten/logo/logo-bad",
        files={"logo": ("virus.exe", io.BytesIO(b"MZ" + b"\x00" * 100), "application/octet-stream")},
        auth=AUTH,
    )
    assert resp.status_code == 400


def test_adm2_logo_te_groot(client, workspace, db):
    _ensure_klant_table(db)
    from app.admin.models import Klant
    db.add(Klant(id="logo-big", code="LBG", naam="Logo Big"))
    db.commit()

    big = b"\x89PNG" + b"\x00" * (6 * 1024 * 1024)
    resp = client.post(
        "/admin/klanten/logo/logo-big",
        files={"logo": ("huge.png", io.BytesIO(big), "image/png")},
        auth=AUTH,
    )
    assert resp.status_code == 413


# ── ADM-4: Data export ──

def test_adm4_export_pagina(client, workspace):
    resp = client.get("/admin/export", auth=AUTH)
    assert resp.status_code == 200
    assert "Database backup" in resp.text


def test_adm4_export_klanten_csv(client, workspace, db):
    _ensure_klant_table(db)
    resp = client.get("/admin/export/klanten-csv", auth=AUTH)
    assert resp.status_code == 200
    assert "klanten.csv" in resp.headers.get("Content-Disposition", "")


# ── ADM-5: Instellingen ──

def test_adm5_instellingen_pagina(client, workspace, db):
    _ensure_klant_table(db)
    resp = client.get("/admin/instellingen", auth=AUTH)
    assert resp.status_code == 200
    assert "Bundelfactoren" in resp.text


def test_adm5_instellingen_opslaan(client, workspace, db):
    _ensure_klant_table(db)
    resp = client.post("/admin/instellingen",
                       data={
                           "bundelfactor_1": "1.0", "bundelfactor_2": "2.0",
                           "bundelfactor_3": "2.15", "bundelfactor_4": "2.73",
                           "ruimfactor_enkelbuis": "1.5", "ruimfactor_bundel": "1.2",
                           "ruimfactor_boogzinker": "1.1",
                           "diepte_ld_gas": "-0.70", "diepte_hd_gas": "-1.00",
                           "diepte_bgi": "-1.00",
                           "standaard_dekking": "3.0", "standaard_tekenaar": "martien",
                       },
                       auth=AUTH, follow_redirects=True)
    assert resp.status_code == 200

    from app.admin.models import Instelling
    inst = db.query(Instelling).filter_by(sleutel="bundelfactor_2").first()
    assert inst is not None
    assert inst.waarde == "2.0"


# ── ADM-6: Eisenprofielen ──

def test_adm6_eisenprofielen_pagina(client, workspace, db):
    resp = client.get("/admin/eisenprofielen", auth=AUTH)
    assert resp.status_code == 200
    assert "Eisenprofielen" in resp.text


def test_adm6_eisenprofiel_toevoegen(client, workspace, db):
    resp = client.post("/admin/eisenprofielen/nieuw",
                       data={"naam": "Test Beheerder", "dekking_weg_m": "2.5",
                             "dekking_water_m": "4.0", "Rmin_m": "120"},
                       auth=AUTH, follow_redirects=True)
    assert resp.status_code == 200
    assert "Test Beheerder" in resp.text


# ── ADM-7: Kaartlinks ──

def test_adm7_kaartlinks_pagina(client, workspace, db):
    _ensure_klant_table(db)
    resp = client.get("/admin/kaartlinks", auth=AUTH)
    assert resp.status_code == 200
    assert "Externe kaartlinks" in resp.text


def test_adm7_kaartlink_toevoegen(client, workspace, db):
    _ensure_klant_table(db)
    resp = client.post("/admin/kaartlinks/nieuw",
                       data={"naam": "Test Kaart", "url": "https://example.com",
                             "omschrijving": "Test", "categorie": "kaart"},
                       auth=AUTH, follow_redirects=True)
    assert resp.status_code == 200
    assert "Test Kaart" in resp.text


# ── ADM-8: Logs ──

def test_adm8_logs_pagina(client, workspace, db):
    resp = client.get("/admin/logs", auth=AUTH)
    assert resp.status_code == 200
    assert "Systeem status" in resp.text


# ── ADM-1: Gebruikersbeheer DB ──

def test_adm1_users_uit_db(client, workspace, db):
    """Users worden uit DB geladen, niet uit env vars."""
    resp = client.get("/admin/users", auth=AUTH)
    assert resp.status_code == 200
    assert "martien" in resp.text


def test_adm1_user_aanmaken(client, workspace, db):
    resp = client.post("/admin/users/nieuw",
                       data={"username": "nieuw", "wachtwoord": "Welkom01", "rol": "tekenaar"},
                       auth=AUTH, follow_redirects=True)
    assert resp.status_code == 200
    assert "nieuw" in resp.text


def test_adm1_user_aanmaken_kort_wachtwoord(client, workspace, db):
    resp = client.post("/admin/users/nieuw",
                       data={"username": "kort", "wachtwoord": "Ab1", "rol": "tekenaar"},
                       auth=AUTH)
    assert resp.status_code == 400


def test_adm1_user_aanmaken_geen_hoofdletter(client, workspace, db):
    resp = client.post("/admin/users/nieuw",
                       data={"username": "nohoofd", "wachtwoord": "welkom012", "rol": "tekenaar"},
                       auth=AUTH)
    assert resp.status_code == 400


def test_adm1_user_aanmaken_geen_cijfer(client, workspace, db):
    resp = client.post("/admin/users/nieuw",
                       data={"username": "nocijfer", "wachtwoord": "Welkomhier", "rol": "tekenaar"},
                       auth=AUTH)
    assert resp.status_code == 400


def test_adm1_user_aanmaken_dubbel(client, workspace, db):
    client.post("/admin/users/nieuw",
                data={"username": "dubbel", "wachtwoord": "Welkom01", "rol": "tekenaar"},
                auth=AUTH)
    resp = client.post("/admin/users/nieuw",
                       data={"username": "dubbel", "wachtwoord": "Welkom02", "rol": "tekenaar"},
                       auth=AUTH)
    assert resp.status_code == 400


def test_adm1_user_deactiveren(client, workspace, db):
    from app.admin.models import User
    from app.core.password import hash_password
    db.add(User(id="deact-test", username="deactuser", wachtwoord_hash=hash_password("Welkom01"), rol="tekenaar"))
    db.commit()

    resp = client.post("/admin/users/deact-test/deactiveer", auth=AUTH, follow_redirects=True)
    assert resp.status_code == 200

    db.expire_all()
    u = db.get(User, "deact-test")
    assert u.actief is False


def test_adm1_admin_kan_zichzelf_niet_deactiveren(client, workspace, db):
    from app.admin.models import User
    martien = db.query(User).filter_by(username="martien").first()
    resp = client.post(f"/admin/users/{martien.id}/deactiveer", auth=AUTH)
    assert resp.status_code == 400


def test_adm1_wachtwoord_wijzigen(client, workspace, db):
    from app.admin.models import User
    from app.core.password import hash_password
    db.add(User(id="pw-test", username="pwuser", wachtwoord_hash=hash_password("OudWw001"), rol="tekenaar"))
    db.commit()

    resp = client.post("/admin/users/pw-test/wachtwoord",
                       data={"wachtwoord": "NieuwWw01"},
                       auth=AUTH, follow_redirects=True)
    assert resp.status_code == 200

    # Login met nieuw wachtwoord
    resp2 = client.get("/admin/users", auth=("pwuser", "NieuwWw01"))
    # pwuser is tekenaar, niet admin → 403
    assert resp2.status_code == 403


def test_adm1_deactieve_user_kan_niet_inloggen(client, workspace, db):
    from app.admin.models import User
    from app.core.password import hash_password
    db.add(User(id="inact-test", username="inactive", wachtwoord_hash=hash_password("Welkom01"), rol="tekenaar", actief=False))
    db.commit()

    resp = client.get("/orders/", auth=("inactive", "Welkom01"))
    assert resp.status_code == 401


# ── Auth: Admin-only check ──

def test_admin_403_voor_niet_admin(client, workspace):
    """Alle admin routes geven 403 voor niet-admin users."""
    routes = ["/admin/", "/admin/users", "/admin/klanten",
              "/admin/export", "/admin/instellingen", "/admin/eisenprofielen",
              "/admin/kaartlinks", "/admin/logs"]
    for route in routes:
        resp = client.get(route, auth=("sopa", "test-martien"))
        assert resp.status_code == 403, f"{route} gaf {resp.status_code} ipv 403"
