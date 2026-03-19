"""AHN5 PDOK WCS — ophalen maaiveldwaarde voor een RD-punt.

Publieke API:
    haal_maaiveld_op(rd_x, rd_y) -> float | None

Gebruikt tifffile + numpy voor GeoTIFF-parsing.
Alle fouten worden gevangen en gelogd; de functie geeft altijd None terug bij fouten.
"""
import io
import logging
import math

import httpx

try:
    import numpy
    import tifffile
    TIFFFILE_AVAILABLE = True
except ImportError:
    TIFFFILE_AVAILABLE = False
    numpy = None
    tifffile = None

logger = logging.getLogger(__name__)

_WCS_BASE = "https://service.pdok.nl/rws/ahn/wcs/v1_0"
_TIMEOUT_S = 8
_NODATA = -9999.0
_BUFFER_M = 1  # 1 meter buffer rondom het punt


def haal_maaiveld_op(rd_x: float, rd_y: float) -> float | None:
    """Vraag de AHN5 WCS op voor punt (rd_x, rd_y) in EPSG:28992.

    Retourneert de pixelwaarde in meters NAP, of None bij fout / NoData.
    Geeft nooit een exception terug.
    """
    params = {
        "SERVICE": "WCS",
        "VERSION": "2.0.1",
        "REQUEST": "GetCoverage",
        "COVERAGEID": "dtm_05m",
        "SUBSETTINGCRS": "EPSG:28992",
        "SUBSET": [
            f"X({rd_x - _BUFFER_M},{rd_x + _BUFFER_M})",
            f"Y({rd_y - _BUFFER_M},{rd_y + _BUFFER_M})",
        ],
        "FORMAT": "image/tiff",
    }
    try:
        response = httpx.get(_WCS_BASE, params=params, timeout=_TIMEOUT_S)
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        logger.warning("AHN5 timeout voor (%.1f, %.1f): %s", rd_x, rd_y, exc)
        return None
    except Exception as exc:
        logger.warning("AHN5 HTTP-fout voor (%.1f, %.1f): %s", rd_x, rd_y, exc)
        return None

    try:
        return _lees_tiff_pixelwaarde(response.content)
    except Exception as exc:
        logger.warning("AHN5 GeoTIFF parse-fout voor (%.1f, %.1f): %s", rd_x, rd_y, exc)
        return None


def _lees_tiff_pixelwaarde(tiff_bytes: bytes) -> float | None:
    """Lees de eerste pixelwaarde uit een GeoTIFF via tifffile.

    Geeft None bij NoData (-9999.0) of nan.
    """
    if len(tiff_bytes) < 8:
        return None

    with tifffile.TiffFile(io.BytesIO(tiff_bytes)) as tif:
        data = tif.asarray()

    waarde = float(data.flat[0])

    if math.isnan(waarde) or waarde == _NODATA:
        return None

    return round(waarde, 3)
