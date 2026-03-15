from pyproj import Transformer


_rd_to_wgs84 = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
_wgs84_to_rd = Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)


def rd_to_wgs84(x: float, y: float) -> tuple[float, float]:
    """RD New → (lat, lon) voor Leaflet."""
    lon, lat = _rd_to_wgs84.transform(x, y)
    return round(lat, 8), round(lon, 8)


def wgs84_to_rd(lat: float, lon: float) -> tuple[float, float]:
    """WGS84 → (RD_x, RD_y)."""
    x, y = _wgs84_to_rd.transform(lon, lat)
    return round(x, 2), round(y, 2)
