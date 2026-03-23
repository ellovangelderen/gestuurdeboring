"""Tests voor OPS-2 — Disaster Recovery / Restore vanuit R2."""
import pytest
from unittest.mock import patch, MagicMock
from tests.conftest import AUTH


def test_list_available_backups_zonder_r2():
    """Zonder R2 config: lege lijst."""
    from app.core.restore import list_available_backups
    with patch("app.core.restore._get_r2_client", return_value=None):
        assert list_available_backups() == []


def test_restore_zonder_r2():
    """Zonder R2 config: foutmelding."""
    from app.core.restore import restore_from_r2
    with patch("app.core.restore._get_r2_client", return_value=None):
        result = restore_from_r2()
        assert result["ok"] is False
        assert "niet geconfigureerd" in result.get("fout", "")


def test_restore_met_mock_r2():
    """Restore met mock R2: download DB + logo's."""
    from app.core.restore import restore_from_r2
    mock_client = MagicMock()
    mock_client.list_objects_v2.return_value = {
        "Contents": [
            {"Key": "staging/2026-03-23/logos/Logo3D.jpg"},
            {"Key": "staging/2026-03-23/logos/Logo_Liander.png"},
        ]
    }
    mock_client.download_file = MagicMock()

    with patch("app.core.restore._get_r2_client", return_value=mock_client), \
         patch("app.core.restore.settings") as mock_settings, \
         patch("app.core.restore.list_available_backups", return_value=["2026-03-23"]):
        mock_settings.R2_ENDPOINT = "https://test.r2.cloudflarestorage.com"
        mock_settings.R2_ACCESS_KEY_ID = "test"
        mock_settings.R2_SECRET_ACCESS_KEY = "test"
        mock_settings.R2_BUCKET = "test-bucket"
        mock_settings.ENV = "staging"
        mock_settings.DATABASE_URL = "sqlite:///./test_restore.db"

        result = restore_from_r2("2026-03-23")
        assert result["db_restored"] is True
        assert result["logos_restored"] == 2
        assert mock_client.download_file.call_count == 3  # 1 DB + 2 logos


def test_list_backups_met_mock_r2():
    """list_available_backups retourneert datums gesorteerd."""
    from app.core.restore import list_available_backups
    mock_client = MagicMock()
    mock_client.list_objects_v2.return_value = {
        "Contents": [
            {"Key": "staging/2026-03-22/hdd.db"},
            {"Key": "staging/2026-03-23/hdd.db"},
            {"Key": "staging/2026-03-21/hdd.db"},
        ]
    }

    with patch("app.core.restore._get_r2_client", return_value=mock_client), \
         patch("app.core.restore.settings") as mock_settings:
        mock_settings.ENV = "staging"
        mock_settings.R2_BUCKET = "test"

        datums = list_available_backups()
        assert datums == ["2026-03-23", "2026-03-22", "2026-03-21"]


def test_admin_restore_route(client, workspace, db):
    """POST /admin/restore draait restore en redirect."""
    with patch("app.core.restore.restore_from_r2", return_value={
        "ok": True,
        "datum": "2026-03-23",
        "db_restored": True,
        "logos_restored": 3,
        "fouten": [],
    }):
        resp = client.post("/admin/restore",
                           data={"datum": "2026-03-23"},
                           auth=AUTH, follow_redirects=True)
        assert resp.status_code == 200
        assert "Restore OK" in resp.text


def test_admin_restore_niet_admin(client, workspace, db):
    """POST /admin/restore als niet-admin geeft 403."""
    resp = client.post("/admin/restore",
                       data={"datum": ""},
                       auth=("sopa", "test-martien"))
    assert resp.status_code == 403


def test_admin_export_heeft_restore_knop(client, workspace, db):
    """Export pagina toont restore sectie."""
    resp = client.get("/admin/export", auth=AUTH)
    assert resp.status_code == 200
    assert "Restore vanuit R2" in resp.text
    assert "Overschrijft" in resp.text
