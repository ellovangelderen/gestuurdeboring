"""PDOK URL generatie op basis van RD-coördinaten.

Genereert een PDOK Viewer URL zodat de gebruiker direct de juiste locatie ziet.
"""


def genereer_pdok_url(rd_x: float, rd_y: float, zoom: int = 12) -> str:
    """Genereer PDOK Viewer URL voor een RD-punt.

    Args:
        rd_x: X-coördinaat in EPSG:28992 (RD New)
        rd_y: Y-coördinaat in EPSG:28992 (RD New)
        zoom: Zoomniveau (default 12, geschikt voor boortracé)

    Returns:
        PDOK Viewer URL string
    """
    return (
        f"https://app.pdok.nl/viewer/"
        f"#x={rd_x:.2f}&y={rd_y:.2f}&z={zoom}"
    )
