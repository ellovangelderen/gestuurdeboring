"""GWSW riool BOB data ophalen via PDOK OGC API Features.

Publieke API:
    haal_riooldata_op(rd_x, rd_y, buffer_m) -> list[RioolLeiding]
"""
import logging
from dataclasses import dataclass

import httpx

from app.geo.coords import rd_to_wgs84

logger = logging.getLogger(__name__)

_OGC_BASE = "https://api.pdok.nl/rioned/beheer-stedelijk-watersystemen-gwsw/ogc/v1"
_TIMEOUT_S = 10


@dataclass
class RioolLeiding:
    naam: str
    bob_begin: float | None      # BOB beginpunt (m NAP)
    bob_eind: float | None       # BOB eindpunt (m NAP)
    materiaal: str
    stelseltype: str             # gemengd, DWA, HWA, etc.
    hoogte_mm: float | None      # leidingdiameter in mm
    dataset: str                 # gemeente/dataset naam
    geometrie_wkt: str | None    # WKT geometrie (WGS84)

    @property
    def heeft_bob(self) -> bool:
        return self.bob_begin is not None or self.bob_eind is not None

    @property
    def gemeente(self) -> str:
        """Extract gemeente naam uit dataset URL."""
        if "dataset=" in self.dataset:
            return self.dataset.split("dataset=")[-1]
        return self.dataset or "Onbekend"


def _parse_uri_label(uri: str | None) -> str:
    """Haal label uit GWSW URI (bijv. 'http://data.gwsw.nl/.../PVC' → 'PVC')."""
    if not uri:
        return ""
    return uri.rsplit("/", 1)[-1] if "/" in uri else uri


def haal_riooldata_op(
    rd_x: float, rd_y: float, buffer_m: float = 50.0, limit: int = 50,
) -> list[RioolLeiding]:
    """Haal riooldata op voor een locatie via PDOK GWSW OGC API.

    Args:
        rd_x, rd_y: RD New coördinaten van het punt
        buffer_m: zoekstraal in meters rondom het punt
        limit: max aantal leidingen

    Returns:
        Lijst van RioolLeiding objecten
    """
    # API verwacht WGS84 bbox
    lat, lon = rd_to_wgs84(rd_x, rd_y)
    # Omrekenen buffer van meters naar graden (benadering)
    d_lat = buffer_m / 111320.0
    d_lon = buffer_m / (111320.0 * 0.6)  # cos(52°) ≈ 0.6

    bbox = f"{lon - d_lon:.6f},{lat - d_lat:.6f},{lon + d_lon:.6f},{lat + d_lat:.6f}"

    params = {
        "f": "json",
        "limit": str(limit),
        "bbox": bbox,
    }

    try:
        resp = httpx.get(
            f"{_OGC_BASE}/collections/beheerleiding/items",
            params=params,
            timeout=_TIMEOUT_S,
        )
        resp.raise_for_status()
    except httpx.TimeoutException as exc:
        logger.warning("GWSW timeout voor (%.1f, %.1f): %s", rd_x, rd_y, exc)
        return []
    except Exception as exc:
        logger.warning("GWSW fout voor (%.1f, %.1f): %s", rd_x, rd_y, exc)
        return []

    try:
        data = resp.json()
    except Exception:
        return []

    resultaat = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        geom = feature.get("geometry")
        geom_wkt = None
        if geom and geom.get("type") == "LineString":
            coords = geom["coordinates"]
            wkt_pts = ", ".join(f"{c[0]} {c[1]}" for c in coords)
            geom_wkt = f"LINESTRING({wkt_pts})"

        resultaat.append(RioolLeiding(
            naam=props.get("naam", ""),
            bob_begin=props.get("bob_beginpunt_leiding"),
            bob_eind=props.get("bob_eindpunt_leiding"),
            materiaal=_parse_uri_label(props.get("materiaal_leiding")),
            stelseltype=_parse_uri_label(props.get("stelseltype", "")),
            hoogte_mm=props.get("hoogte_leiding"),
            dataset=props.get("dataset", ""),
            geometrie_wkt=geom_wkt,
        ))

    return resultaat
