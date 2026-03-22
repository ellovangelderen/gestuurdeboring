"""E2E tests — Trace kaart (map) pagina."""
import pytest

pytestmark = pytest.mark.e2e


def _navigate_to_trace(page, base_url):
    """Find and navigate to a trace page from the cockpit.

    Returns True if a trace page was found, False otherwise.
    """
    page.goto(f"{base_url}/orders/", timeout=30000)
    page.wait_for_load_state("networkidle")

    # Find a trace link anywhere on the cockpit or order detail
    trace_link = page.locator("a[href*='/trace']").first
    if trace_link.count() == 0:
        # Try going to first order detail to find trace link
        order_link = page.locator("table a[href*='/orders/']").first
        if order_link.count() == 0:
            return False
        order_link.click()
        page.wait_for_load_state("networkidle")
        trace_link = page.locator("a[href*='/trace']").first
        if trace_link.count() == 0:
            return False

    trace_link.click()
    page.wait_for_load_state("networkidle")
    return True


def test_trace_map_container_renders(page, base_url):
    """Trace page has a map container element."""
    if not _navigate_to_trace(page, base_url):
        pytest.skip("Geen trace pagina gevonden (geen orders met boringen)")
    # Map container should be present (Leaflet creates #map or similar)
    map_el = page.locator("#map")
    assert map_el.is_visible(), "Map container #map niet gevonden"


def test_trace_leaflet_initializes(page, base_url):
    """Leaflet library initializes and adds .leaflet-container class."""
    if not _navigate_to_trace(page, base_url):
        pytest.skip("Geen trace pagina")
    # Wait for Leaflet to initialize
    page.wait_for_selector(".leaflet-container", timeout=10000)
    assert page.locator(".leaflet-container").count() > 0


def test_trace_layer_control_present(page, base_url):
    """Leaflet layer control (base layer switcher) is present."""
    if not _navigate_to_trace(page, base_url):
        pytest.skip("Geen trace pagina")
    page.wait_for_selector(".leaflet-container", timeout=10000)
    # Layer control adds a control element
    layer_control = page.locator(".leaflet-control-layers")
    assert layer_control.count() > 0, "Layer control niet gevonden"


def test_trace_bgt_tile_configured(page, base_url):
    """BGT tile source from PDOK is configured in the page source."""
    if not _navigate_to_trace(page, base_url):
        pytest.skip("Geen trace pagina")
    content = page.content()
    # Check that the BGT PDOK tile URL pattern is present in the page
    assert "pdok.nl" in content and "bgt" in content, \
        "BGT tile URL patroon (pdok.nl + bgt) niet gevonden in paginabron"


def test_trace_osm_tile_configured(page, base_url):
    """OpenStreetMap tile layer is configured as base layer."""
    if not _navigate_to_trace(page, base_url):
        pytest.skip("Geen trace pagina")
    content = page.content()
    assert "openstreetmap.org" in content, \
        "OpenStreetMap tile URL niet gevonden in paginabron"
