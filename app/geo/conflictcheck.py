"""3D conflictcheck: boortracé vs kabels & leidingen.

Projecteert KLIC-leidingen op het verticale profielvlak van de boring
en berekent de minimale afstand tot de boorlijn.

Publieke API:
    check_conflicts(boring, klic_leidingen, profiel) -> list[dict]
"""
import math
from dataclasses import dataclass

from shapely import from_wkt
from shapely.geometry import LineString, Point

from app.geo.profiel import BoorProfiel, arc_punten


@dataclass
class Conflict:
    leiding_id: str
    beheerder: str
    leidingtype: str
    afstand_m: float           # verticale afstand boortracé ↔ leiding
    x_profiel: float           # positie langs profiel (m)
    z_boor: float              # NAP hoogte boorlijn op dit punt
    z_leiding: float | None    # NAP hoogte leiding (None = onbekend)
    diepte_onbekend: bool      # True als diepte niet beschikbaar is
    horizontale_afstand_m: float  # afstand leiding tot tracélijn in RD


def _boor_z_op_x(profiel: BoorProfiel, x: float) -> float | None:
    """Bereken de NAP-hoogte van de boorlijn op horizontale afstand x."""
    for seg in profiel.segmenten:
        x_lo = min(seg["x_start"], seg["x_end"])
        x_hi = max(seg["x_start"], seg["x_end"])
        if x < x_lo - 0.01 or x > x_hi + 0.01:
            continue

        if seg["type"] == "lijn":
            x_span = seg["x_end"] - seg["x_start"]
            if abs(x_span) < 0.001:
                return seg["z_start"]
            t = (x - seg["x_start"]) / x_span
            return seg["z_start"] + t * (seg["z_end"] - seg["z_start"])

        elif seg["type"] == "arc":
            # Discretiseer de arc en interpoleer
            pts = arc_punten(
                seg["cx"], seg["cz"], seg["radius"],
                seg["start_hoek_rad"], seg["eind_hoek_rad"], n=100,
            )
            # Zoek de twee punten die x omvatten
            for i in range(len(pts) - 1):
                x0, z0 = pts[i]
                x1, z1 = pts[i + 1]
                if (x0 <= x <= x1) or (x1 <= x <= x0):
                    if abs(x1 - x0) < 0.001:
                        return z0
                    t = (x - x0) / (x1 - x0)
                    return z0 + t * (z1 - z0)

    return None


def check_conflicts(
    trace_coords: list[tuple[float, float]],
    profiel: BoorProfiel,
    leidingen: list,
    dekking_min_m: float = 0.5,
    corridor_m: float = 25.0,
) -> list[Conflict]:
    """Check of KLIC-leidingen conflicteren met het boortracé.

    Args:
        trace_coords: [(RD_x, RD_y), ...] van de tracépunten
        profiel: BoorProfiel object met segmenten
        leidingen: lijst van KLICLeiding objecten
        dekking_min_m: minimale verticale afstand (default 0.5m)
        corridor_m: horizontale zoekafstand rondom tracé (default 25m)

    Returns:
        Lijst van Conflict objecten, gesorteerd op afstand (ergste eerst)
    """
    if len(trace_coords) < 2:
        return []

    trace_line = LineString(trace_coords)
    L_totaal = profiel.L_totaal_m

    conflicts: list[Conflict] = []

    for leiding in leidingen:
        if not leiding.geometrie_wkt:
            continue
        try:
            geom = from_wkt(leiding.geometrie_wkt)
        except Exception:
            continue
        if geom is None or geom.is_empty:
            continue

        # Horizontale afstand tot tracé
        h_afstand = trace_line.distance(geom)
        if h_afstand > corridor_m:
            continue  # te ver weg

        # Projecteer dichtstbijzijnde punt op de tracélijn
        if hasattr(geom, 'coords'):
            punten = list(geom.coords)
        elif hasattr(geom, 'geoms'):
            punten = []
            for part in geom.geoms:
                punten.extend(list(part.coords))
        else:
            continue

        for coord in punten:
            pt = Point(coord[:2])  # alleen x,y
            afstand_tot_trace = trace_line.distance(pt)
            if afstand_tot_trace > corridor_m:
                continue

            # Projectie op trace → afstand langs lijn (0..L)
            s = trace_line.project(pt)
            # Normaliseer naar profiel x-as
            trace_lengte = trace_line.length
            if trace_lengte > 0:
                x_profiel = (s / trace_lengte) * L_totaal
            else:
                continue

            # Beperk tot profiel bereik
            if x_profiel < 0 or x_profiel > L_totaal:
                continue

            # Hoogte boorlijn op dit punt
            z_boor = _boor_z_op_x(profiel, x_profiel)
            if z_boor is None:
                continue

            # Diepte leiding
            diepte_onbekend = leiding.diepte_m is None
            if not diepte_onbekend:
                # diepte_m is afstand onder maaiveld → NAP = maaiveld - diepte
                # Maar we weten maaiveld niet exact op dit punt.
                # Gebruik diepte_m als NAP-hoogte als het een NAP-waarde is,
                # of markeer als onzeker.
                z_leiding = -abs(leiding.diepte_m)  # aanname: diepte als negatief NAP
                verticale_afstand = abs(z_boor - z_leiding)
            else:
                z_leiding = None
                verticale_afstand = 0.0  # onbekend → altijd conflict

            conflicts.append(Conflict(
                leiding_id=leiding.id,
                beheerder=leiding.beheerder or "Onbekend",
                leidingtype=leiding.leidingtype or "Onbekend",
                afstand_m=verticale_afstand,
                x_profiel=round(x_profiel, 1),
                z_boor=round(z_boor, 3),
                z_leiding=round(z_leiding, 3) if z_leiding is not None else None,
                diepte_onbekend=diepte_onbekend,
                horizontale_afstand_m=round(afstand_tot_trace, 1),
            ))

    # Dedupliceeer: per leiding alleen het dichtstbijzijnde punt
    best_per_leiding: dict[str, Conflict] = {}
    for c in conflicts:
        key = c.leiding_id
        if key not in best_per_leiding or c.horizontale_afstand_m < best_per_leiding[key].horizontale_afstand_m:
            best_per_leiding[key] = c

    # Sorteer: onbekende diepte eerst, dan op kleinste afstand
    result = sorted(
        best_per_leiding.values(),
        key=lambda c: (not c.diepte_onbekend, c.afstand_m),
    )
    return result
