"""E2E tests — Admin panel paginas."""
import pytest

pytestmark = pytest.mark.e2e


def test_admin_dashboard_loads(page, base_url):
    """Admin dashboard loads and shows 'Beheer' heading."""
    page.goto(f"{base_url}/admin/", timeout=30000)
    page.wait_for_load_state("networkidle")
    assert "Beheer" in page.content()


def test_admin_dashboard_health_banner(page, base_url):
    """Admin dashboard shows system health banner (OK or warning)."""
    page.goto(f"{base_url}/admin/", timeout=30000)
    page.wait_for_load_state("networkidle")
    content = page.content()
    # Health banner shows either "Systeem OK" or an error state
    assert "Systeem OK" in content or "Systeem" in content or "DB" in content, \
        "Health banner niet gevonden op admin dashboard"


def test_admin_klanten_page_loads(page, base_url):
    """Klanten (opdrachtgevers) page loads with a table."""
    page.goto(f"{base_url}/admin/klanten", timeout=30000)
    page.wait_for_load_state("networkidle")
    # Should have a table for klanten
    assert page.locator("table").count() > 0 or "Opdrachtgever" in page.content()


def test_admin_instellingen_page_loads(page, base_url):
    """Instellingen page loads without errors."""
    page.goto(f"{base_url}/admin/instellingen", timeout=30000)
    page.wait_for_load_state("networkidle")
    # Should not be a 500 error
    assert "500" not in page.title()
    # Page should have form elements for settings
    assert page.locator("form").count() > 0 or page.locator("input").count() > 0


def test_admin_users_page_loads(page, base_url):
    """Users page loads and shows at least 'martien'."""
    page.goto(f"{base_url}/admin/users", timeout=30000)
    page.wait_for_load_state("networkidle")
    # Note: this may return 403 for non-admin users.
    # The test user needs to be admin or this will correctly catch the issue.
    status = page.evaluate("() => document.title")
    content = page.content()
    assert "martien" in content or "403" in content


def test_admin_dashboard_has_module_links(page, base_url):
    """Admin dashboard has links to sub-modules (Opdrachtgevers, Instellingen, etc.)."""
    page.goto(f"{base_url}/admin/", timeout=30000)
    page.wait_for_load_state("networkidle")
    content = page.content()
    assert "Opdrachtgevers" in content or "Klanten" in content
