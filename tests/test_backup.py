"""Tests voor OPS-1 — Backup naar Cloudflare R2."""
import pytest
from unittest.mock import patch, MagicMock
from tests.conftest import AUTH


def test_backup_database_lokaal():
    """backup_database() maakt een consistente SQLite kopie."""
    from app.core.backup import backup_database
    path = backup_database()
    assert path is not None
    from pathlib import Path
    assert Path(path).exists()
    assert Path(path).stat().st_size > 0
    # Cleanup
    Path(path).unlink(missing_ok=True)


def test_backup_database_bestand_niet_gevonden():
    """backup_database() gooit FileNotFoundError als DB niet bestaat."""
    from app.core.backup import backup_database
    with patch("app.core.backup.settings") as mock_settings:
        mock_settings.DATABASE_URL = "sqlite:///./nonexistent_test.db"
        with pytest.raises(FileNotFoundError):
            backup_database()


def test_r2_client_geen_config():
    """Zonder R2 config geeft _get_r2_client() None."""
    from app.core.backup import _get_r2_client
    with patch("app.core.backup.settings") as mock_settings:
        mock_settings.R2_ENDPOINT = ""
        mock_settings.R2_ACCESS_KEY_ID = ""
        assert _get_r2_client() is None


def test_upload_to_r2_zonder_config():
    """upload_to_r2 returned False als R2 niet geconfigureerd is."""
    from app.core.backup import upload_to_r2
    with patch("app.core.backup._get_r2_client", return_value=None):
        assert upload_to_r2("/tmp/test.db", "test/test.db") is False


def test_list_r2_backups_zonder_config():
    """list_r2_backups returned lege lijst als R2 niet geconfigureerd is."""
    from app.core.backup import list_r2_backups
    with patch("app.core.backup._get_r2_client", return_value=None):
        assert list_r2_backups() == []


def test_run_backup_zonder_r2():
    """run_backup draait lokale backup maar R2 upload faalt graceful."""
    from app.core.backup import run_backup
    with patch("app.core.backup._get_r2_client", return_value=None):
        result = run_backup()
        assert result["datum"] is not None
        assert result["db_backup"] is not None
        assert result["db_uploaded"] is False
        # Cleanup
        from pathlib import Path
        if result["db_backup"]:
            Path(result["db_backup"]).unlink(missing_ok=True)


def test_run_backup_met_mock_r2():
    """run_backup uploadt naar R2 als geconfigureerd (mock)."""
    from app.core.backup import run_backup
    mock_client = MagicMock()
    mock_client.upload_file = MagicMock()

    with patch("app.core.backup._get_r2_client", return_value=mock_client), \
         patch("app.core.backup.settings") as mock_settings:
        mock_settings.DATABASE_URL = "sqlite:///./hdd.db"
        mock_settings.R2_ENDPOINT = "https://test.r2.cloudflarestorage.com"
        mock_settings.R2_ACCESS_KEY_ID = "test"
        mock_settings.R2_SECRET_ACCESS_KEY = "test"
        mock_settings.R2_BUCKET = "test-bucket"
        mock_settings.ENV = "staging"

        result = run_backup()
        assert result["db_uploaded"] is True
        assert mock_client.upload_file.called

        # Cleanup
        from pathlib import Path
        if result["db_backup"]:
            Path(result["db_backup"]).unlink(missing_ok=True)


def test_admin_backup_route(client, workspace, db):
    """POST /admin/backup draait backup en redirect naar export pagina."""
    with patch("app.core.backup.run_backup", return_value={
        "datum": "2026-03-23",
        "db_backup": "/data/backups/hdd-2026-03-23.db",
        "db_uploaded": True,
        "logos_uploaded": 3,
        "backups_opgeruimd": 0,
        "fouten": [],
    }):
        resp = client.post("/admin/backup", auth=AUTH, follow_redirects=True)
        assert resp.status_code == 200
        assert "Backup OK" in resp.text


def test_admin_backup_route_niet_admin(client, workspace, db):
    """POST /admin/backup als niet-admin geeft 403."""
    resp = client.post("/admin/backup", auth=("sopa", "test-martien"))
    assert resp.status_code == 403


def test_admin_export_pagina_heeft_backup_knop(client, workspace, db):
    """Export pagina toont R2 backup knop."""
    resp = client.get("/admin/export", auth=AUTH)
    assert resp.status_code == 200
    assert "Backup naar R2" in resp.text
    assert "Backup nu" in resp.text
