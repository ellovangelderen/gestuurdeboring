"""Regressietests voor kaartlagen — valideer PDOK endpoints en zoom levels.

Test dat alle tile endpoints bereikbaar zijn op de zoom levels die we gebruiken.
Voorkomt dat een 401/404 op een PDOK endpoint onopgemerkt de kaart breekt.

Draai los:  pytest tests/test_map_tiles.py -v
Skip in CI: SKIP_EXTERNAL_CALLS=1 pytest
"""
import pytest
import httpx

pytestmark = pytest.mark.external

TILE_COORDS = {
    10: (526, 340),
    13: (4212, 2722),
    15: (16850, 10890),
    18: (134802, 87123),
}


@pytest.mark.parametrize("zoom", [13, 15, 18])
def test_bgt_wmts_tile_bereikbaar(zoom):
    """BGT WMTS tiles laden op zoom 13-18."""
    x, y = TILE_COORDS[zoom]
    url = f"https://service.pdok.nl/lv/bgt/wmts/v1_0/standaardvisualisatie/EPSG:3857/{zoom}/{x}/{y}.png"
    resp = httpx.get(url, timeout=10)
    assert resp.status_code == 200, f"BGT tile z={zoom} gaf {resp.status_code}"
    assert "image/png" in resp.headers.get("content-type", "")


def test_bgt_wmts_capabilities():
    """BGT WMTS GetCapabilities is bereikbaar."""
    url = "https://service.pdok.nl/lv/bgt/wmts/v1_0?SERVICE=WMTS&REQUEST=GetCapabilities"
    resp = httpx.get(url, timeout=10)
    assert resp.status_code == 200
    assert "standaardvisualisatie" in resp.text


def test_bgt_wms_geeft_401():
    """BGT WMS endpoint geeft 401 — bevestig dat we WMTS moeten gebruiken."""
    url = "https://service.pdok.nl/lv/bgt/wms/v1_0?SERVICE=WMS&REQUEST=GetCapabilities"
    resp = httpx.get(url, timeout=10)
    assert resp.status_code in (401, 403), f"BGT WMS geeft {resp.status_code} — check of WMS weer werkt"


@pytest.mark.parametrize("zoom", [10, 13, 15, 18])
def test_brt_wmts_tile_bereikbaar(zoom):
    """BRT achtergrondkaart tiles laden op alle zoom levels."""
    x, y = TILE_COORDS[zoom]
    url = f"https://service.pdok.nl/brt/achtergrondkaart/wmts/v2_0/standaard/EPSG:3857/{zoom}/{x}/{y}.png"
    resp = httpx.get(url, timeout=10)
    assert resp.status_code == 200, f"BRT tile z={zoom} gaf {resp.status_code}"


@pytest.mark.parametrize("zoom", [10, 15, 18])
def test_luchtfoto_wmts_tile_bereikbaar(zoom):
    """PDOK luchtfoto tiles laden."""
    x, y = TILE_COORDS[zoom]
    url = f"https://service.pdok.nl/hwh/luchtfotorgb/wmts/v1_0/Actueel_orthoHR/EPSG:3857/{zoom}/{x}/{y}.jpeg"
    resp = httpx.get(url, timeout=10)
    assert resp.status_code == 200, f"Luchtfoto tile z={zoom} gaf {resp.status_code}"


def test_osm_tile_bereikbaar():
    """OSM fallback tiles laden."""
    url = "https://a.tile.openstreetmap.org/10/526/340.png"
    resp = httpx.get(url, timeout=10, headers={"User-Agent": "HDD-Platform-Test/1.0"})
    assert resp.status_code == 200


def test_bgt_niet_beschikbaar_op_laag_zoom():
    """BGT tiles bestaan niet op zoom < 11."""
    url = "https://service.pdok.nl/lv/bgt/wmts/v1_0/standaardvisualisatie/EPSG:3857/8/131/85.png"
    resp = httpx.get(url, timeout=10)
    assert resp.status_code in (400, 404, 500), f"BGT z=8 gaf {resp.status_code}"


def test_brt_beschikbaar_op_laag_zoom():
    """BRT werkt ook op lage zoom (overzicht heel NL)."""
    url = "https://service.pdok.nl/brt/achtergrondkaart/wmts/v2_0/standaard/EPSG:3857/8/131/85.png"
    resp = httpx.get(url, timeout=10)
    assert resp.status_code == 200
