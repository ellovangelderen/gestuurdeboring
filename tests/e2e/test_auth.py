"""E2E tests — Authentication (HTTP Basic Auth)."""
import base64

import pytest
from playwright.sync_api import sync_playwright

pytestmark = pytest.mark.e2e


def _make_auth_header(username: str, password: str) -> dict:
    """Build HTTP Basic Auth header."""
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def test_auth_no_credentials_returns_401(base_url):
    """Request without credentials gets 401 Unauthorized."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()  # No auth headers
        page = context.new_page()
        resp = page.goto(f"{base_url}/orders/", timeout=30000)
        assert resp.status == 401, f"Verwacht 401 zonder credentials, kreeg {resp.status}"
        browser.close()


def test_auth_correct_credentials_returns_200(base_url, auth_credentials):
    """Request with correct credentials gets 200 OK."""
    username, password = auth_credentials
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            extra_http_headers=_make_auth_header(username, password),
        )
        page = context.new_page()
        resp = page.goto(f"{base_url}/orders/", timeout=30000)
        assert resp.status == 200, f"Verwacht 200 met correcte credentials, kreeg {resp.status}"
        browser.close()


def test_auth_wrong_password_returns_401(base_url):
    """Request with wrong password gets 401 Unauthorized."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            extra_http_headers=_make_auth_header("martien", "fout-wachtwoord-xyz"),
        )
        page = context.new_page()
        resp = page.goto(f"{base_url}/orders/", timeout=30000)
        assert resp.status == 401, f"Verwacht 401 met fout wachtwoord, kreeg {resp.status}"
        browser.close()


def test_auth_unknown_user_returns_401(base_url):
    """Request with unknown username gets 401 Unauthorized."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            extra_http_headers=_make_auth_header("onbekende_gebruiker", "willekeurig"),
        )
        page = context.new_page()
        resp = page.goto(f"{base_url}/orders/", timeout=30000)
        assert resp.status == 401, f"Verwacht 401 met onbekende user, kreeg {resp.status}"
        browser.close()
