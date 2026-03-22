"""E2E tests — Order detail pagina."""
import pytest

pytestmark = pytest.mark.e2e


def _get_first_order_url(page, base_url):
    """Navigate to cockpit and return URL of first order, or None."""
    page.goto(f"{base_url}/orders/", timeout=30000)
    page.wait_for_load_state("networkidle")
    # Orders are links in the table rows
    order_link = page.locator("table a[href*='/orders/']").first
    if order_link.count() == 0:
        return None
    href = order_link.get_attribute("href")
    return href


def test_order_detail_loads(page, base_url):
    """Order detail page loads when navigating from cockpit."""
    href = _get_first_order_url(page, base_url)
    if href is None:
        pytest.skip("Geen orders in database om te testen")
    page.goto(f"{base_url}{href}" if href.startswith("/") else href, timeout=30000)
    page.wait_for_load_state("networkidle")
    # Should show order info — a table with order details
    assert page.locator("table").count() > 0


def test_order_detail_shows_ordernummer(page, base_url):
    """Order detail page shows the order number somewhere."""
    page.goto(f"{base_url}/orders/", timeout=30000)
    page.wait_for_load_state("networkidle")
    # Get first order number from the table
    first_row = page.locator("table tbody tr").first
    if first_row.count() == 0:
        pytest.skip("Geen orders in database")
    ordernummer_cell = first_row.locator("td").first
    ordernummer_text = ordernummer_cell.inner_text().strip()

    # Navigate to detail
    first_row.locator("a").first.click()
    page.wait_for_load_state("networkidle")
    # Order number should appear on detail page
    assert ordernummer_text in page.content() or page.url.endswith(ordernummer_text)


def test_order_detail_boring_link(page, base_url):
    """Boring detail link on order detail page is clickable."""
    href = _get_first_order_url(page, base_url)
    if href is None:
        pytest.skip("Geen orders")
    page.goto(f"{base_url}{href}" if href.startswith("/") else href, timeout=30000)
    page.wait_for_load_state("networkidle")

    boring_link = page.locator("a[href*='/boringen/']").first
    if boring_link.count() == 0:
        pytest.skip("Order heeft geen boringen")
    boring_link.click()
    page.wait_for_load_state("networkidle")
    # Should not be an error page
    assert page.locator("text=500").count() == 0 or "500" not in page.title()


def test_order_detail_has_action_buttons(page, base_url):
    """Order detail page has action buttons (details, trace, brondata links)."""
    href = _get_first_order_url(page, base_url)
    if href is None:
        pytest.skip("Geen orders")
    page.goto(f"{base_url}{href}" if href.startswith("/") else href, timeout=30000)
    page.wait_for_load_state("networkidle")

    # Check for common action links/buttons
    buttons = page.locator("a.btn")
    assert buttons.count() >= 1
