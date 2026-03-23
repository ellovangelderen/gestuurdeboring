"""MF-5 — Lengteprofiel bij horizontale bochten.

Verificatie dat het lengteprofiel de werkelijke tracélengte gebruikt
(som van segmenten = "platgeslagen dwarsprofiel"), niet de rechte lijn.
"""
import math
import pytest


def test_trace_totale_afstand_rechte_lijn():
    """Rechte lijn: afstand = rechte lijn."""
    from app.geo.profiel import trace_totale_afstand
    L = trace_totale_afstand([(0, 0), (200, 0)])
    assert L == pytest.approx(200.0)


def test_trace_totale_afstand_bocht():
    """90° bocht: afstand = som segmenten (200m), niet rechte lijn (141m)."""
    from app.geo.profiel import trace_totale_afstand
    L = trace_totale_afstand([(0, 0), (100, 0), (100, 100)])
    assert L == pytest.approx(200.0)
    # Rechte lijn zou 141.4m zijn — we gebruiken de langere "platgeslagen" afstand
    assert L > math.sqrt(100**2 + 100**2)


def test_trace_totale_afstand_s_bocht():
    """S-bocht: afstand is langer dan rechte lijn."""
    from app.geo.profiel import trace_totale_afstand
    L = trace_totale_afstand([(0, 0), (50, 30), (100, 0), (150, 0)])
    rechte_lijn = trace_totale_afstand([(0, 0), (150, 0)])
    assert L > rechte_lijn


def test_profiel_gebruikt_platgeslagen_lengte():
    """Boorprofiel bij bochtig tracé gebruikt platgeslagen lengte, niet rechte lijn."""
    from app.geo.profiel import bereken_boorprofiel, trace_totale_afstand

    # Bochtig tracé: 100m + 100m = 200m langs tracé
    coords = [(0, 0), (100, 0), (100, 100)]
    L_platgeslagen = trace_totale_afstand(coords)
    L_rechte_lijn = math.sqrt(100**2 + 100**2)

    profiel = bereken_boorprofiel(
        L_totaal_m=L_platgeslagen,
        MVin_NAP_m=0.5, MVuit_NAP_m=0.3,
        alpha_in_gr=18.0, alpha_uit_gr=22.0, De_mm=160.0,
    )

    # Profiel L_totaal moet de platgeslagen lengte zijn, niet de rechte lijn
    assert profiel.L_totaal_m == pytest.approx(200.0)
    assert profiel.L_totaal_m > L_rechte_lijn

    # Eerste segment start bij x=0, laatste eindigt bij x=L_totaal
    assert profiel.segmenten[0]["x_start"] == pytest.approx(0.0)
    assert profiel.segmenten[-1]["x_end"] == pytest.approx(200.0)
