"""E2E tests — Cockpit (orderlijst) pagina."""
import pytest

pytestmark = pytest.mark.e2e


def test_cockpit_loads_with_stats_bar(page, base_url):
    """Cockpit page loads and shows the stats bar with stat cards."""
    page.goto(f"{base_url}/orders/", timeout=30000)
    assert page.locator(".stats-bar").is_visible()
    # Must have stat cards for totaal, in uitvoering, etc.
    stat_cards = page.locator(".stat-card")
    assert stat_cards.count() >= 3


def test_cockpit_stats_show_totaal(page, base_url):
    """Stats bar shows 'Totaal' label."""
    page.goto(f"{base_url}/orders/", timeout=30000)
    assert page.locator("text=Totaal").is_visible()


def test_cockpit_stats_show_in_uitvoering(page, base_url):
    """Stats bar shows 'In uitvoering' label."""
    page.goto(f"{base_url}/orders/", timeout=30000)
    assert page.locator("text=In uitvoering").is_visible()


def test_cockpit_order_table_renders(page, base_url):
    """Order table or empty-state message should be present."""
    page.goto(f"{base_url}/orders/", timeout=30000)
    table = page.locator("table")
    empty_msg = page.locator("text=Geen orders gevonden")
    # Either there is a table with orders, or an empty message
    assert table.count() > 0 or empty_msg.is_visible()


def test_cockpit_search_input_present(page, base_url):
    """Search input field is present on cockpit page."""
    page.goto(f"{base_url}/orders/", timeout=30000)
    search = page.locator("input.cockpit-search")
    assert search.is_visible()
    assert search.get_attribute("placeholder") is not None


def test_cockpit_search_works(page, base_url):
    """Typing in search field and submitting does not crash."""
    page.goto(f"{base_url}/orders/", timeout=30000)
    search = page.locator("input.cockpit-search")
    search.fill("test-zoekterm")
    search.press("Enter")
    # Page should reload without error
    page.wait_for_load_state("networkidle")
    assert page.locator(".stats-bar").is_visible()


def test_cockpit_filter_actief(page, base_url):
    """Clicking 'Actief' filter navigates and keeps page functional."""
    page.goto(f"{base_url}/orders/?filter=actief", timeout=30000)
    page.wait_for_load_state("networkidle")
    assert page.locator(".stats-bar").is_visible()
    # The actief pill should have active state
    active_pill = page.locator("button.filter-pill--active")
    assert active_pill.count() >= 1


def test_cockpit_filter_wacht_akkoord(page, base_url):
    """Filter 'wacht_akkoord' works."""
    page.goto(f"{base_url}/orders/?filter=wacht_akkoord", timeout=30000)
    page.wait_for_load_state("networkidle")
    assert page.locator(".stats-bar").is_visible()


def test_cockpit_filter_geleverd(page, base_url):
    """Filter 'geleverd' works."""
    page.goto(f"{base_url}/orders/?filter=geleverd", timeout=30000)
    page.wait_for_load_state("networkidle")
    assert page.locator(".stats-bar").is_visible()


def test_cockpit_sort_dropdown_present(page, base_url):
    """Sort dropdown is present with expected options."""
    page.goto(f"{base_url}/orders/", timeout=30000)
    sort_select = page.locator("select.cockpit-sort")
    assert sort_select.is_visible()
    options = sort_select.locator("option")
    assert options.count() >= 3


def test_cockpit_sort_by_datum(page, base_url):
    """Sorting by 'Ontvangen' (datum) does not crash."""
    page.goto(f"{base_url}/orders/?sorteer=datum&richting=desc", timeout=30000)
    page.wait_for_load_state("networkidle")
    assert page.locator(".stats-bar").is_visible()


def test_cockpit_sort_by_klant(page, base_url):
    """Sorting by 'Klant' does not crash."""
    page.goto(f"{base_url}/orders/?sorteer=klant&richting=asc", timeout=30000)
    page.wait_for_load_state("networkidle")
    assert page.locator(".stats-bar").is_visible()
