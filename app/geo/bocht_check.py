"""Horizontale bocht check — waarschuw als bocht te scherp is.

Publieke API:
    check_bochten(trace_coords, Rh_min) -> list[dict]
"""
from __future__ import annotations
import math


def _hoek_tussen_segmenten(p0, p1, p2):
    """Bereken de hoek (graden) tussen twee opeenvolgende segmenten."""
    dx1 = p1[0] - p0[0]
    dy1 = p1[1] - p0[1]
    dx2 = p2[0] - p1[0]
    dy2 = p2[1] - p1[1]

    len1 = math.sqrt(dx1**2 + dy1**2)
    len2 = math.sqrt(dx2**2 + dy2**2)
    if len1 < 0.01 or len2 < 0.01:
        return 0.0

    # Dot product → hoek tussen de twee richtingen
    # 0° = zelfde richting (recht door), 180° = terug
    dot = dx1 * dx2 + dy1 * dy2
    cos_angle = dot / (len1 * len2)
    cos_angle = max(-1.0, min(1.0, cos_angle))
    hoek_rad = math.acos(cos_angle)
    # Dit geeft de afbuigingshoek direct (0 = recht, 90 = haakse bocht)
    return math.degrees(hoek_rad)


def check_bochten(
    trace_coords: list[tuple[float, float]],
    Rh_waarden: list[float | None],
    Rv_min: float = 100.0,
) -> list[dict]:
    """Check of horizontale bochten niet te scherp zijn.

    Args:
        trace_coords: [(RD_x, RD_y), ...] van de tracélijn
        Rh_waarden: [Rh_m, ...] per segment (None = geen bocht)
        Rv_min: minimale buigradius in meters

    Returns:
        Lijst van waarschuwingen per bocht.
    """
    if len(trace_coords) < 3:
        return []

    waarschuwingen = []
    for i in range(1, len(trace_coords) - 1):
        afbuiging = _hoek_tussen_segmenten(
            trace_coords[i - 1], trace_coords[i], trace_coords[i + 1]
        )
        # afbuiging: 0° = recht door, 90° = haakse bocht, 180° = terug

        if afbuiging > 1.0:  # meer dan 1° afbuiging
            # Rh op dit punt
            rh = Rh_waarden[i] if i < len(Rh_waarden) and Rh_waarden[i] else None

            warning = {
                "punt_index": i,
                "afbuiging_gr": round(afbuiging, 1),
                "Rh_m": rh,
            }

            if rh and rh < Rv_min:
                warning["te_scherp"] = True
                warning["melding"] = f"Bocht te scherp: Rh={rh}m < Rmin={Rv_min}m"
            elif not rh and afbuiging > 5.0:
                warning["te_scherp"] = False
                warning["melding"] = f"Bocht van {afbuiging:.1f}° zonder Rh opgegeven"
            else:
                continue  # kleine bocht, geen waarschuwing

            waarschuwingen.append(warning)

    return waarschuwingen
