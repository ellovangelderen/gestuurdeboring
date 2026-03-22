"""E2E test fixtures — Playwright + HTTP Basic Auth."""
import base64
import os

import pytest


# ── Configuration ──

E2E_BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8000")
E2E_USERNAME = os.environ.get("E2E_USERNAME", "test")
E2E_PASSWORD = os.environ.get("E2E_PASSWORD", "test123")


@pytest.fixture(scope="session")
def base_url():
    """Base URL for the running app."""
    return E2E_BASE_URL


@pytest.fixture(scope="session")
def auth_credentials():
    """Return (username, password) tuple."""
    return (E2E_USERNAME, E2E_PASSWORD)


@pytest.fixture(scope="session")
def auth_header(auth_credentials):
    """Pre-built Authorization header for HTTP Basic Auth."""
    username, password = auth_credentials
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


@pytest.fixture(scope="session")
def browser_context_args(auth_header):
    """Playwright browser context args — inject auth headers into every request."""
    return {
        "extra_http_headers": auth_header,
    }


@pytest.fixture(scope="session")
def browser_type_launch_args():
    """Launch browser headless."""
    return {
        "headless": True,
    }


@pytest.fixture
def authed_page(page, base_url, auth_header):
    """Convenience: a page with base_url pre-set and auth headers active.

    Usage: authed_page.goto("/orders/")
    """
    # Auth headers are already set via browser_context_args.
    # This fixture just provides a page with the base_url for convenience.
    page._base_url = base_url
    return page


def _goto(page, path, base_url):
    """Navigate to a path on the app."""
    url = f"{base_url}{path}" if path.startswith("/") else path
    return page.goto(url, timeout=30000)
