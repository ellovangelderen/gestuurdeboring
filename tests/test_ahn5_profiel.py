"""Tests voor AHN5 maaiveldprofiel langs boorlijn (F5)."""
import pytest
from unittest.mock import patch, MagicMock


def test_profiel_sample_punten_count():
    """Samplepunten worden elke 1m gegenereerd."""
    from app.geo.ahn5 import haal_maaiveld_profiel

    # Mock de WCS call
    with patch("app.geo.ahn5.httpx.get") as mock_get:
        # Laat de mock falen zodat we de fallback (None) krijgen
        mock_get.side_effect = Exception("test")
        trace = [(103900.0, 489290.0), (104100.0, 489290.0)]  # 200m
        result = haal_maaiveld_profiel(trace, interval_m=1.0)

    # ~200 punten + begin + eind
    assert len(result) >= 200
    # Alle z-waarden zijn None (want mock faalde)
    assert all(p[3] is None for p in result)


def test_profiel_afstanden_correct():
    """Afstanden langs de lijn zijn correct berekend."""
    from app.geo.ahn5 import haal_maaiveld_profiel

    with patch("app.geo.ahn5.httpx.get", side_effect=Exception("test")):
        trace = [(0.0, 0.0), (100.0, 0.0)]  # 100m horizontaal
        result = haal_maaiveld_profiel(trace, interval_m=5.0)

    afstanden = [p[0] for p in result]
    assert afstanden[0] == pytest.approx(0.0)
    assert afstanden[-1] == pytest.approx(100.0)
    # Tussenafstanden zijn ~5m
    for i in range(1, len(afstanden) - 1):
        assert afstanden[i] == pytest.approx(i * 5.0, abs=0.1)


def test_profiel_lege_trace():
    """Lege trace geeft lege lijst."""
    from app.geo.ahn5 import haal_maaiveld_profiel
    assert haal_maaiveld_profiel([], interval_m=1.0) == []
    assert haal_maaiveld_profiel([(0, 0)], interval_m=1.0) == []


@pytest.mark.external
def test_profiel_echte_ahn5_haarlem():
    """Echte AHN5 profiel voor HDD11 Haarlem tracé."""
    from app.geo.ahn5 import haal_maaiveld_profiel

    trace = [
        (103896.9, 489289.5),  # A
        (104118.8, 489243.7),  # B
    ]
    result = haal_maaiveld_profiel(trace, interval_m=5.0)

    # Moet punten teruggeven
    assert len(result) > 40  # ~226m / 5m ≈ 45 punten
    # Minstens sommige z-waarden beschikbaar
    met_z = [p for p in result if p[3] is not None]
    assert len(met_z) > 20, f"Te weinig AHN5 waarden: {len(met_z)} van {len(result)}"
    # Z-waarden moeten in redelijk bereik liggen voor Haarlem (~0-3m NAP)
    for p in met_z:
        assert -2.0 < p[3] < 10.0, f"Onverwachte NAP waarde {p[3]} op afstand {p[0]:.0f}m"
