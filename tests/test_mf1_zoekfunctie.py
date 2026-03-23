"""MF-1 — Kaart zoekfunctie: adres/postcode zoeken op trace pagina."""
import pytest
from tests.conftest import AUTH


def _maak_order_boring(db):
    """Helper: maak order + boring voor trace pagina."""
    from app.core.database import Base, engine
    import app.order.models
    Base.metadata.create_all(bind=engine)

    from app.order.models import Order, Boring
    order = Order(id="mf1-order", workspace_id="gbt-workspace-001", ordernummer="MF1-TEST")
    db.add(order)
    boring = Boring(id="mf1-boring", order_id="mf1-order", volgnummer=1, type="B")
    db.add(boring)
    db.commit()
    return order, boring


# ── Template tests ──

def test_trace_pagina_heeft_zoekbalk(client, workspace, db):
    """Trace pagina bevat zoekbalk HTML."""
    _maak_order_boring(db)
    resp = client.get("/orders/mf1-order/boringen/1/trace", auth=AUTH)
    assert resp.status_code == 200
    assert 'id="address-search"' in resp.text
    assert 'id="search-input"' in resp.text
    assert "Zoek adres" in resp.text


def test_trace_pagina_heeft_pdok_script(client, workspace, db):
    """Trace pagina bevat PDOK locatieserver API URL in JavaScript."""
    _maak_order_boring(db)
    resp = client.get("/orders/mf1-order/boringen/1/trace", auth=AUTH)
    assert "api.pdok.nl/bzk/locatieserver" in resp.text


def test_trace_pagina_heeft_search_results(client, workspace, db):
    """Trace pagina bevat resultaten container."""
    _maak_order_boring(db)
    resp = client.get("/orders/mf1-order/boringen/1/trace", auth=AUTH)
    assert 'id="search-results"' in resp.text


# ── MF-2: Fullscreen knop ──

def test_trace_pagina_heeft_fullscreen_knop(client, workspace, db):
    """Trace pagina bevat fullscreen knop."""
    _maak_order_boring(db)
    resp = client.get("/orders/mf1-order/boringen/1/trace", auth=AUTH)
    assert 'id="fullscreen-btn"' in resp.text
    assert "Volledig scherm" in resp.text


# ── PDOK API tests (staging) ──

@pytest.mark.external
def test_pdok_locatieserver_bereikbaar():
    """PDOK Locatieserver API is bereikbaar en geeft resultaten."""
    import httpx
    r = httpx.get(
        "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free?q=Gasthuisdijk+Zwolle&rows=3",
        timeout=10,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["response"]["numFound"] > 0
    assert "Zwolle" in data["response"]["docs"][0].get("weergavenaam", "")


@pytest.mark.external
def test_pdok_locatieserver_postcode():
    """PDOK zoeken op postcode geeft resultaten."""
    import httpx
    r = httpx.get(
        "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free?q=8041AG+16&rows=3",
        timeout=10,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["response"]["numFound"] > 0


@pytest.mark.external
def test_pdok_locatieserver_heeft_coordinaten():
    """PDOK resultaat bevat centroide_ll (WGS84 coordinaten)."""
    import httpx
    r = httpx.get(
        "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free?q=Amsterdam+Centraal&rows=1",
        timeout=10,
    )
    data = r.json()
    doc = data["response"]["docs"][0]
    assert "centroide_ll" in doc
    assert "POINT(" in doc["centroide_ll"]
