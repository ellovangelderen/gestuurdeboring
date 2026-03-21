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


def haal_maaiveld_profiel(
    trace_punten: list[tuple[float, float]],
    interval_m: float = 1.0,
) -> list[tuple[float, float, float | None]]:
    """Haal maaiveldprofiel op langs een tracélijn via 1 AHN5 WCS request.

    Args:
        trace_punten: [(RD_x, RD_y), ...] van de tracélijn
        interval_m: afstand tussen samplepunten in meters (default 1m)

    Returns:
        [(afstand_m, RD_x, RD_y, z_nap), ...] langs de lijn.
        z_nap is None als de waarde niet beschikbaar is.
    """
    if not TIFFFILE_AVAILABLE or len(trace_punten) < 2:
        return []

    import math as _m

    # Bereken punten langs de lijn op elke interval_m
    sample_punten = []  # (afstand, rd_x, rd_y)
    cumul = 0.0
    sample_punten.append((0.0, trace_punten[0][0], trace_punten[0][1]))

    for i in range(1, len(trace_punten)):
        x0, y0 = trace_punten[i - 1]
        x1, y1 = trace_punten[i]
        seg_len = _m.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)
        if seg_len < 0.001:
            continue

        # Hoeveel samples in dit segment
        d = interval_m - (cumul % interval_m) if cumul > 0 else interval_m
        while d <= seg_len:
            t = d / seg_len
            sx = x0 + t * (x1 - x0)
            sy = y0 + t * (y1 - y0)
            sample_punten.append((cumul + d, sx, sy))
            d += interval_m
        cumul += seg_len

    # Laatste punt
    sample_punten.append((cumul, trace_punten[-1][0], trace_punten[-1][1]))

    if not sample_punten:
        return []

    # Bbox van alle punten (met 5m buffer)
    xs = [p[1] for p in sample_punten]
    ys = [p[2] for p in sample_punten]
    buf = 5.0
    x_min, x_max = min(xs) - buf, max(xs) + buf
    y_min, y_max = min(ys) - buf, max(ys) + buf

    # 1 WCS request voor de hele bbox
    params = {
        "SERVICE": "WCS",
        "VERSION": "2.0.1",
        "REQUEST": "GetCoverage",
        "COVERAGEID": "dtm_05m",
        "SUBSETTINGCRS": "EPSG:28992",
        "SUBSET": [
            f"X({x_min:.1f},{x_max:.1f})",
            f"Y({y_min:.1f},{y_max:.1f})",
        ],
        "FORMAT": "image/tiff",
    }

    try:
        response = httpx.get(_WCS_BASE, params=params, timeout=15)
        response.raise_for_status()
    except Exception as exc:
        logger.warning("AHN5 profiel fout: %s", exc)
        return [(p[0], p[1], p[2], None) for p in sample_punten]

    # Parse GeoTIFF
    try:
        if len(response.content) < 100:
            return [(p[0], p[1], p[2], None) for p in sample_punten]

        with tifffile.TiffFile(io.BytesIO(response.content)) as tif:
            data = tif.asarray()
            # Lees geo-transformatie uit tags
            # AHN5 WCS geeft een GeoTIFF met bbox als extent
            rows, cols = data.shape[:2] if data.ndim >= 2 else (1, data.size)

        # Pixel coördinaten berekenen
        dx_per_px = (x_max - x_min) / cols if cols > 1 else 1.0
        dy_per_px = (y_max - y_min) / rows if rows > 1 else 1.0

        result = []
        for afstand, sx, sy in sample_punten:
            col = int((sx - x_min) / dx_per_px)
            row = int((y_max - sy) / dy_per_px)  # y is omgekeerd in raster
            col = max(0, min(col, cols - 1))
            row = max(0, min(row, rows - 1))

            if data.ndim >= 2:
                val = float(data[row, col])
            else:
                val = float(data[col])

            if _m.isnan(val) or val == _NODATA or abs(val) > 1e10:
                result.append((afstand, sx, sy, None))
            else:
                result.append((afstand, sx, sy, round(val, 3)))

        return result

    except Exception as exc:
        logger.warning("AHN5 profiel parse-fout: %s", exc)
        return [(p[0], p[1], p[2], None) for p in sample_punten]
