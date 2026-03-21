"""Tests voor security fixes — SEC-1 t/m SEC-3."""
import io
from tests.conftest import AUTH


# ── SEC-1: File upload size limits ──

def test_sec1_klic_size_limit(client, workspace, db):
    """KLIC upload >50MB wordt geweigerd met 413."""
    from app.order.models import Order, Boring
    db.add(Order(id="order-sec1", workspace_id="gbt-workspace-001", ordernummer="SEC1"))
    db.add(Boring(id="boring-sec1", order_id="order-sec1", volgnummer=1, type="B"))
    db.commit()

    # 51MB dummy bestand
    big_file = b"X" * (51 * 1024 * 1024)
    resp = client.post(
        "/orders/order-sec1/klic",
        files={"klic_zip": ("huge.zip", io.BytesIO(big_file), "application/zip")},
        auth=AUTH,
    )
    assert resp.status_code == 413


def test_sec1_klic_normal_size_accepted(client, workspace, db):
    """KLIC upload <50MB wordt geaccepteerd (400 want geen geldig ZIP, maar niet 413)."""
    from app.order.models import Order, Boring
    db.add(Order(id="order-sec1b", workspace_id="gbt-workspace-001", ordernummer="SEC1B"))
    db.add(Boring(id="boring-sec1b", order_id="order-sec1b", volgnummer=1, type="B"))
    db.commit()

    small_file = b"PK" + b"\x00" * 1000
    resp = client.post(
        "/orders/order-sec1b/klic",
        files={"klic_zip": ("small.zip", io.BytesIO(small_file), "application/zip")},
        auth=AUTH,
    )
    # Niet 413 — bestand is klein genoeg (mag 200 of 303 of 500 zijn, maar niet 413)
    assert resp.status_code != 413


# ── SEC-2: Auth failure logging ──

def test_sec2_auth_failure_logged(client, caplog):
    """Mislukte login poging wordt gelogd."""
    import logging
    with caplog.at_level(logging.WARNING, logger="app.core.auth"):
        resp = client.get("/orders/", auth=("hacker", "wrongpass"))
    assert resp.status_code == 401
    assert "AUTH_FAILURE" in caplog.text
    assert "hacker" in caplog.text


def test_sec2_auth_success_no_warning(client, workspace, caplog):
    """Succesvolle login geeft geen warning."""
    import logging
    with caplog.at_level(logging.WARNING, logger="app.core.auth"):
        resp = client.get("/orders/", auth=AUTH, follow_redirects=True)
    assert resp.status_code == 200
    assert "AUTH_FAILURE" not in caplog.text


# ── SEC-3: tifffile importeerbaar ──

def test_sec3_tifffile_importeerbaar():
    """tifffile is importeerbaar (nodig voor AHN5)."""
    import tifffile
    assert hasattr(tifffile, "TiffFile")


def test_sec3_numpy_importeerbaar():
    """numpy is importeerbaar (nodig voor AHN5)."""
    import numpy
    assert hasattr(numpy, "ndarray")


# ── SEC-4: Rate limiting op auth failures ──

def test_sec4_rate_limit_na_10_pogingen(client):
    """Na 10 mislukte pogingen → 429 Too Many Requests."""
    from app.core.auth import _auth_failures
    # Reset
    _auth_failures.clear()

    # 10 mislukte pogingen
    for i in range(10):
        resp = client.get("/orders/", auth=("brute", "wrong"))
        assert resp.status_code == 401

    # 11e poging → 429
    resp = client.get("/orders/", auth=("brute", "wrong"))
    assert resp.status_code == 429

    # Cleanup
    _auth_failures.clear()


def test_sec4_succesvolle_login_reset_counter(client, workspace):
    """Succesvolle login reset de failure counter."""
    from app.core.auth import _auth_failures
    _auth_failures.clear()

    # 5 mislukte pogingen
    for _ in range(5):
        client.get("/orders/", auth=("martien", "fout"))

    assert len(_auth_failures.get("martien", [])) == 5

    # Succesvolle login
    resp = client.get("/orders/", auth=AUTH, follow_redirects=True)
    assert resp.status_code == 200

    # Counter gereset
    assert len(_auth_failures.get("martien", [])) == 0
    _auth_failures.clear()


# ── SEC-6: Lock file bestaat ──

def test_sec6_lockfile_bestaat():
    """requirements.lock bestaat."""
    from pathlib import Path
    lock = Path("requirements.lock")
    assert lock.exists(), "requirements.lock ontbreekt"
    content = lock.read_text()
    assert "fastapi" in content.lower()


# ── QUA-4: Lifespan ipv on_startup ──

def test_qua4_geen_deprecated_on_event():
    """main.py gebruikt lifespan, niet on_event('startup')."""
    from pathlib import Path
    main_py = Path("app/main.py").read_text()
    assert "on_event" not in main_py, "on_event is deprecated — gebruik lifespan"
    assert "lifespan" in main_py
