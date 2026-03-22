"""Waterschap bepalen op basis van RD-coördinaten via PDOK WMS GetFeatureInfo.

Publieke API:
    bepaal_waterschap(rd_x, rd_y) -> str | None
    waterschap_kaart_url(waterschap_naam) -> str | None
"""
from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

_WMS_URL = "https://service.pdok.nl/hwh/waterschappen-waterschapsgrenzen-imso/wms/v2_0"
_TIMEOUT_S = 8
_BUFFER_M = 7  # halve breedte van het bbox-venster

# Lookup: waterschap naam (lowercase, zonder INSPIRE-suffix) → kaart-URL
# Bron: publieke ArcGIS Experience / Hub portalen per waterschap
WATERSCHAP_KAART_URLS: dict[str, str] = {
    "hoogheemraadschap van rijnland": "https://rfrijnland.maps.arcgis.com/apps/webappviewer/index.html",
    "waterschap amstel, gooi en vecht": "https://avgmap.waternet.nl/kaarten/",
    "hoogheemraadschap hollands noorderkwartier": "https://geoservices.hhnk.nl/arcgis/apps/webappviewer/index.html",
    "hoogheemraadschap van delfland": "https://www.hhdelfland.nl/kaart",
    "hoogheemraadschap de stichtse rijnlanden": "https://www.hdsr.nl/kaart",
    "hoogheemraadschap van schieland en de krimpenerwaard": "https://www.schielandendekrimpenerwaard.nl/kaart",
    "waterschap hollandse delta": "https://www.wshd.nl/kaart",
    "waterschap rivierenland": "https://www.waterschaprivierenland.nl/kaart",
    "waterschap drents overijsselse delta": "https://www.wdodelta.nl/kaart",
    "waterschap vechtstromen": "https://www.vechtstromen.nl/kaart",
    "waterschap vallei en veluwe": "https://www.valleioveluwe.nl/kaart",
    "waterschap rijn en ijssel": "https://www.wrij.nl/kaart",
    "wetterskip fryslân": "https://www.wetterskipfryslan.nl/kaart",
    "waterschap noorderzijlvest": "https://www.noorderzijlvest.nl/kaart",
    "waterschap hunze en aa's": "https://www.hunzeenaas.nl/kaart",
    "waterschap zuiderzeeland": "https://www.zuiderzeeland.nl/kaart",
    "waterschap scheldestromen": "https://www.scheldestromen.nl/kaart",
    "waterschap de dommel": "https://www.dommel.nl/kaart",
    "waterschap aa en maas": "https://www.aaenmaas.nl/kaart",
    "waterschap brabantse delta": "https://www.brabantsedelta.nl/kaart",
    "waterschap limburg": "https://www.waterschaplimburg.nl/kaart",
}


def _normaliseer_naam(naam: str) -> str:
    """Strip ' (INSPIRE-grens)' suffix en trim."""
    if naam.endswith(" (INSPIRE-grens)"):
        naam = naam[: -len(" (INSPIRE-grens)")]
    return naam.strip()


def bepaal_waterschap(rd_x: float, rd_y: float) -> str | None:
    """Bepaal het waterschap op basis van RD-coördinaten via PDOK WMS GetFeatureInfo.

    Retourneert de waterbeheerder-naam of None bij fout.
    """
    # Bouw een klein bbox-venster rondom het punt (14×14 px)
    size = _BUFFER_M
    bbox = f"{rd_x - size},{rd_y - size},{rd_x + size},{rd_y + size}"

    params = {
        "SERVICE": "WMS",
        "VERSION": "1.3.0",
        "REQUEST": "GetFeatureInfo",
        "LAYERS": "Waterschap",
        "QUERY_LAYERS": "Waterschap",
        "CRS": "EPSG:28992",
        "BBOX": bbox,
        "WIDTH": "14",
        "HEIGHT": "14",
        "I": "7",
        "J": "7",
        "INFO_FORMAT": "application/json",
    }

    try:
        response = httpx.get(_WMS_URL, params=params, timeout=_TIMEOUT_S)
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        logger.warning("PDOK WMS timeout voor (%.1f, %.1f): %s", rd_x, rd_y, exc)
        return None
    except Exception as exc:
        logger.warning("PDOK WMS fout voor (%.1f, %.1f): %s", rd_x, rd_y, exc)
        return None

    try:
        data = response.json()
        features = data.get("features", [])
        if not features:
            logger.info("Geen waterschap gevonden voor (%.1f, %.1f)", rd_x, rd_y)
            return None
        props = features[0].get("properties", {})
        # Gebruik 'waterbeheerder' veld (volledige naam)
        naam = props.get("waterbeheerder") or props.get("naam") or ""
        return _normaliseer_naam(naam) if naam else None
    except Exception as exc:
        logger.warning("PDOK WMS parse-fout voor (%.1f, %.1f): %s", rd_x, rd_y, exc)
        return None


def waterschap_kaart_url(waterschap_naam: str | None) -> str | None:
    """Zoek de kaart-URL voor een waterschap.

    Retourneert de URL of None als waterschap onbekend.
    """
    if not waterschap_naam:
        return None
    return WATERSCHAP_KAART_URLS.get(waterschap_naam.lower().strip())
