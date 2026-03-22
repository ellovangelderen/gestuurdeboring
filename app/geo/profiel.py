"""Boorprofiel geometrie — kernberekening voor HDD lengteprofiel met ARCs.

Ondersteunt N-segment profielen: tussenliggende dieptepunten met eigen buigradius.
"""
import math
from dataclasses import dataclass, field


@dataclass
class ProfielPunt:
    """Verticaal profielpunt voor N-segment engine (pure data, geen DB)."""
    afstand_m: float     # horizontale afstand vanaf intreepunt
    NAP_z: float         # doel NAP-hoogte op dit punt
    Rv_m: float = 0.0    # buigradius bij dit punt (0 = gebruik standaard Rv)


@dataclass
class BoorProfiel:
    Rv_m: float                    # standaard buigradius (intree/uittree)
    L_totaal_m: float              # horizontale afstand intree-uittree
    diepte_NAP_m: float            # NAP-hoogte diepste punt
    segmenten: list = field(default_factory=list)


def bereken_Rv(De_mm: float) -> float:
    """Minimale buigradius: Rv = 1200 x De (in meters)."""
    return 1200.0 * De_mm / 1000.0


def _maak_intree_segmenten(
    MVin: float, diepte: float, alpha_rad: float, alpha_gr: float, Rv: float,
) -> list:
    """Genereer intree lijn + boog segmenten. Returned (segmenten, x_positie_na_boog)."""
    Tin_h = Rv * math.sin(alpha_rad)
    Tin_v = Rv * (1 - math.cos(alpha_rad))
    z_boog_start = diepte + Tin_v

    if alpha_gr > 0 and math.tan(alpha_rad) > 0:
        x1 = (MVin - z_boog_start) / math.tan(alpha_rad)
    else:
        x1 = 0.0
    x1 = max(x1, 0.0)

    x2_end = x1 + Tin_h
    arc_cx = x2_end
    arc_cz = diepte + Rv

    segs = []
    # Schuine lijn intree
    segs.append({
        "type": "lijn",
        "x_start": 0.0, "z_start": MVin,
        "x_end": x1, "z_end": z_boog_start,
        "horizontaal": False,
        "lengte": math.sqrt(x1**2 + (MVin - z_boog_start)**2) if x1 > 0 else 0.0,
    })
    # Intree boog
    segs.append({
        "type": "arc",
        "cx": arc_cx, "cz": arc_cz, "radius": Rv,
        "start_hoek_gr": 180.0 + alpha_gr, "eind_hoek_gr": 180.0,
        "start_hoek_rad": math.pi + alpha_rad, "eind_hoek_rad": math.pi,
        "x_start": x1, "z_start": z_boog_start,
        "x_end": x2_end, "z_end": diepte,
    })
    return segs, x2_end


def _maak_uittree_segmenten(
    MVuit: float, diepte: float, alpha_rad: float, alpha_gr: float, Rv: float,
    L_totaal: float,
) -> list:
    """Genereer uittree boog + lijn segmenten. Returned (segmenten, x_positie_voor_boog)."""
    Tuit_h = Rv * math.sin(alpha_rad)
    Tuit_v = Rv * (1 - math.cos(alpha_rad))
    z_boog_start = diepte + Tuit_v

    if alpha_gr > 0 and math.tan(alpha_rad) > 0:
        x5_lengte = (MVuit - z_boog_start) / math.tan(alpha_rad)
    else:
        x5_lengte = 0.0
    x5_lengte = max(x5_lengte, 0.0)

    x3_end = L_totaal - x5_lengte - Tuit_h
    x4_end = x3_end + Tuit_h
    arc_cx = x3_end
    arc_cz = diepte + Rv

    segs = []
    # Uittree boog
    segs.append({
        "type": "arc",
        "cx": arc_cx, "cz": arc_cz, "radius": Rv,
        "start_hoek_gr": 0.0, "eind_hoek_gr": 360.0 - alpha_gr,
        "start_hoek_rad": 0.0, "eind_hoek_rad": 2 * math.pi - alpha_rad,
        "x_start": x3_end, "z_start": diepte,
        "x_end": x4_end, "z_end": z_boog_start,
    })
    # Schuine lijn uittree
    segs.append({
        "type": "lijn",
        "x_start": x4_end, "z_start": z_boog_start,
        "x_end": L_totaal, "z_end": MVuit,
        "horizontaal": False,
        "lengte": math.sqrt(x5_lengte**2 + (MVuit - z_boog_start)**2) if x5_lengte > 0 else 0.0,
    })
    return segs, x3_end


def _maak_tussenovergang(x_van: float, z_van: float, x_naar: float, z_naar: float, Rv: float) -> list:
    """Genereer boog + lijn + boog overgang tussen twee diepteniveaus.

    Van (x_van, z_van) horizontaal naar (x_naar, z_naar) horizontaal.
    Gebruikt één boog om af te buigen en één boog om weer horizontaal te worden.
    """
    dx = x_naar - x_van
    dz = z_naar - z_van

    if abs(dx) < 0.01 or abs(dz) < 0.01:
        # Geen hoogteverschil of geen afstand: rechte lijn
        return [{
            "type": "lijn",
            "x_start": x_van, "z_start": z_van,
            "x_end": x_naar, "z_end": z_naar,
            "horizontaal": abs(dz) < 0.01,
            "lengte": math.sqrt(dx**2 + dz**2),
        }]

    # Hoek van de schuine verbinding
    alpha_rad = abs(math.atan2(abs(dz), dx))
    alpha_gr = math.degrees(alpha_rad)

    # Beperk alpha om te grote bogen te voorkomen
    alpha_rad = min(alpha_rad, math.radians(30))
    alpha_gr = math.degrees(alpha_rad)

    # Tangent lengtes voor deze boog
    T_h = Rv * math.sin(alpha_rad)
    T_v = Rv * (1 - math.cos(alpha_rad))

    # Check of er genoeg ruimte is voor 2 bogen
    if 2 * T_h > dx * 0.95:
        # Te krap: verklein Rv voor deze overgang
        Rv = (dx * 0.45) / math.sin(alpha_rad) if math.sin(alpha_rad) > 0.01 else dx
        T_h = Rv * math.sin(alpha_rad)
        T_v = Rv * (1 - math.cos(alpha_rad))

    segs = []
    gaat_omlaag = dz < 0

    # Boog 1: van horizontaal naar schuine lijn
    x_boog1_end = x_van + T_h
    if gaat_omlaag:
        z_boog1_end = z_van - T_v
        arc1_cx = x_van
        arc1_cz = z_van - Rv
        segs.append({
            "type": "arc",
            "cx": arc1_cx, "cz": arc1_cz, "radius": Rv,
            "start_hoek_gr": 90.0, "eind_hoek_gr": 90.0 - alpha_gr,
            "start_hoek_rad": math.pi / 2, "eind_hoek_rad": math.pi / 2 - alpha_rad,
            "x_start": x_van, "z_start": z_van,
            "x_end": x_boog1_end, "z_end": z_boog1_end,
        })
    else:
        z_boog1_end = z_van + T_v
        arc1_cx = x_van
        arc1_cz = z_van + Rv
        segs.append({
            "type": "arc",
            "cx": arc1_cx, "cz": arc1_cz, "radius": Rv,
            "start_hoek_gr": 270.0, "eind_hoek_gr": 270.0 + alpha_gr,
            "start_hoek_rad": 3 * math.pi / 2, "eind_hoek_rad": 3 * math.pi / 2 + alpha_rad,
            "x_start": x_van, "z_start": z_van,
            "x_end": x_boog1_end, "z_end": z_boog1_end,
        })

    # Rechte lijn (schuine verbinding)
    x_boog2_start = x_naar - T_h
    if gaat_omlaag:
        z_boog2_start = z_naar + T_v
    else:
        z_boog2_start = z_naar - T_v

    if x_boog2_start > x_boog1_end + 0.01:
        lijn_len = math.sqrt((x_boog2_start - x_boog1_end)**2 + (z_boog2_start - z_boog1_end)**2)
        segs.append({
            "type": "lijn",
            "x_start": x_boog1_end, "z_start": z_boog1_end,
            "x_end": x_boog2_start, "z_end": z_boog2_start,
            "horizontaal": False,
            "lengte": lijn_len,
        })
    else:
        x_boog2_start = x_boog1_end
        z_boog2_start = z_boog1_end

    # Boog 2: van schuine lijn terug naar horizontaal
    if gaat_omlaag:
        arc2_cx = x_naar
        arc2_cz = z_naar + Rv
        segs.append({
            "type": "arc",
            "cx": arc2_cx, "cz": arc2_cz, "radius": Rv,
            "start_hoek_gr": 270.0 + alpha_gr, "eind_hoek_gr": 270.0,
            "start_hoek_rad": 3 * math.pi / 2 + alpha_rad, "eind_hoek_rad": 3 * math.pi / 2,
            "x_start": x_boog2_start, "z_start": z_boog2_start,
            "x_end": x_naar, "z_end": z_naar,
        })
    else:
        arc2_cx = x_naar
        arc2_cz = z_naar - Rv
        segs.append({
            "type": "arc",
            "cx": arc2_cx, "cz": arc2_cz, "radius": Rv,
            "start_hoek_gr": 90.0 - alpha_gr, "eind_hoek_gr": 90.0,
            "start_hoek_rad": math.pi / 2 - alpha_rad, "eind_hoek_rad": math.pi / 2,
            "x_start": x_boog2_start, "z_start": z_boog2_start,
            "x_end": x_naar, "z_end": z_naar,
        })

    return segs


def bereken_boorprofiel(
    L_totaal_m: float,
    MVin_NAP_m: float,
    MVuit_NAP_m: float,
    alpha_in_gr: float,
    alpha_uit_gr: float,
    De_mm: float,
    dekking_min_m: float = 3.0,
    profiel_punten: list = None,
) -> BoorProfiel:
    """Bereken het complete boorprofiel met N-segment ondersteuning.

    Zonder profiel_punten: standaard 5-segment profiel (intree, boog, horizontaal, boog, uittree).
    Met profiel_punten: tussenliggende dieptepunten met eigen buigradius.

    Parameters:
        profiel_punten: lijst van ProfielPunt objecten (uit DB of direct).
                        Elk punt definieert een diepte (NAP_z) op een afstand (afstand_m)
                        met optioneel eigen Rv_m.
    """
    Rv = bereken_Rv(De_mm)
    alpha_in_rad = math.radians(alpha_in_gr)
    alpha_uit_rad = math.radians(alpha_uit_gr)

    # Standaard diepte
    diepte_NAP = min(MVin_NAP_m, MVuit_NAP_m) - dekking_min_m

    # Geen profielpunten → standaard 5-segment profiel
    if not profiel_punten:
        return _bereken_standaard_profiel(
            L_totaal_m, MVin_NAP_m, MVuit_NAP_m,
            alpha_in_gr, alpha_uit_gr, Rv, diepte_NAP,
        )

    # N-segment profiel
    # Sorteer profielpunten op afstand
    pp = sorted(profiel_punten, key=lambda p: p.afstand_m)

    # Bouw lijst van waypoints: intree-diepte, profielpunten, uittree-diepte
    waypoints = []
    waypoints.append((0.0, diepte_NAP, Rv))  # virtueel startpunt op intree-diepte
    for p in pp:
        rv = p.Rv_m if p.Rv_m and p.Rv_m > 0 else Rv
        waypoints.append((p.afstand_m, p.NAP_z, rv))
    waypoints.append((L_totaal_m, diepte_NAP, Rv))  # virtueel eindpunt op uittree-diepte

    # Diepste punt
    diepte_NAP_min = min(w[1] for w in waypoints)

    # Intree segmenten
    intree_segs, x_na_intree = _maak_intree_segmenten(
        MVin_NAP_m, waypoints[0][1], alpha_in_rad, alpha_in_gr, Rv,
    )

    # Uittree segmenten
    uittree_segs, x_voor_uittree = _maak_uittree_segmenten(
        MVuit_NAP_m, waypoints[-1][1], alpha_uit_rad, alpha_uit_gr, Rv, L_totaal_m,
    )

    # Midden segmenten: van waypoint naar waypoint
    midden_segs = []
    # We lopen van x_na_intree (na intree boog, op waypoints[0] diepte)
    # via alle profielpunten naar x_voor_uittree (voor uittree boog)
    huidige_x = x_na_intree
    huidige_z = waypoints[0][1]

    for i in range(1, len(waypoints)):
        doel_x = waypoints[i][0]
        doel_z = waypoints[i][1]
        doel_rv = waypoints[i][2]

        # Laatste waypoint: stop bij x_voor_uittree
        if i == len(waypoints) - 1:
            doel_x = x_voor_uittree

        if doel_x <= huidige_x + 0.1:
            continue

        if abs(doel_z - huidige_z) < 0.01:
            # Zelfde diepte: horizontale lijn
            midden_segs.append({
                "type": "lijn",
                "x_start": huidige_x, "z_start": huidige_z,
                "x_end": doel_x, "z_end": doel_z,
                "horizontaal": True,
                "lengte": doel_x - huidige_x,
            })
        else:
            # Diepteverschil: boog-lijn-boog overgang
            overgang = _maak_tussenovergang(huidige_x, huidige_z, doel_x, doel_z, doel_rv)
            midden_segs.extend(overgang)

        huidige_x = doel_x
        huidige_z = doel_z

    # Assembleer: intree + midden + uittree
    segmenten = intree_segs + midden_segs + uittree_segs

    return BoorProfiel(
        Rv_m=Rv,
        L_totaal_m=L_totaal_m,
        diepte_NAP_m=diepte_NAP_min,
        segmenten=segmenten,
    )


def _bereken_standaard_profiel(
    L_totaal_m: float, MVin: float, MVuit: float,
    alpha_in_gr: float, alpha_uit_gr: float,
    Rv: float, diepte_NAP: float,
) -> BoorProfiel:
    """Standaard 5-segment profiel (backward compatible)."""
    alpha_in_rad = math.radians(alpha_in_gr)
    alpha_uit_rad = math.radians(alpha_uit_gr)

    Tin_h = Rv * math.sin(alpha_in_rad)
    Tin_v = Rv * (1 - math.cos(alpha_in_rad))
    Tuit_h = Rv * math.sin(alpha_uit_rad)
    Tuit_v = Rv * (1 - math.cos(alpha_uit_rad))

    L_horiz = L_totaal_m - Tin_h - Tuit_h
    if L_horiz < 0:
        Rv = L_totaal_m / (math.sin(alpha_in_rad) + math.sin(alpha_uit_rad))
        Tin_h = Rv * math.sin(alpha_in_rad)
        Tin_v = Rv * (1 - math.cos(alpha_in_rad))
        Tuit_h = Rv * math.sin(alpha_uit_rad)
        Tuit_v = Rv * (1 - math.cos(alpha_uit_rad))
        L_horiz = 0.0

    z_boog_in_start = diepte_NAP + Tin_v
    z_boog_uit_start = diepte_NAP + Tuit_v

    if alpha_in_gr > 0 and math.tan(alpha_in_rad) > 0:
        x1 = (MVin - z_boog_in_start) / math.tan(alpha_in_rad)
    else:
        x1 = 0.0
    x1 = max(x1, 0.0)

    if alpha_uit_gr > 0 and math.tan(alpha_uit_rad) > 0:
        x5_lengte = (MVuit - z_boog_uit_start) / math.tan(alpha_uit_rad)
    else:
        x5_lengte = 0.0
    x5_lengte = max(x5_lengte, 0.0)

    x2_end = x1 + Tin_h
    x3_end = L_totaal_m - x5_lengte - Tuit_h
    x4_end = x3_end + Tuit_h

    arc_in_cx = x2_end
    arc_in_cz = diepte_NAP + Rv
    arc_uit_cx = x3_end
    arc_uit_cz = diepte_NAP + Rv

    segmenten = [
        {"type": "lijn", "x_start": 0.0, "z_start": MVin,
         "x_end": x1, "z_end": z_boog_in_start, "horizontaal": False,
         "lengte": math.sqrt(x1**2 + (MVin - z_boog_in_start)**2) if x1 > 0 else 0.0},
        {"type": "arc", "cx": arc_in_cx, "cz": arc_in_cz, "radius": Rv,
         "start_hoek_gr": 180.0 + alpha_in_gr, "eind_hoek_gr": 180.0,
         "start_hoek_rad": math.pi + alpha_in_rad, "eind_hoek_rad": math.pi,
         "x_start": x1, "z_start": z_boog_in_start, "x_end": x2_end, "z_end": diepte_NAP},
        {"type": "lijn", "x_start": x2_end, "z_start": diepte_NAP,
         "x_end": x3_end, "z_end": diepte_NAP, "horizontaal": True,
         "lengte": max(x3_end - x2_end, 0.0)},
        {"type": "arc", "cx": arc_uit_cx, "cz": arc_uit_cz, "radius": Rv,
         "start_hoek_gr": 0.0, "eind_hoek_gr": 360.0 - alpha_uit_gr,
         "start_hoek_rad": 0.0, "eind_hoek_rad": 2 * math.pi - alpha_uit_rad,
         "x_start": x3_end, "z_start": diepte_NAP, "x_end": x4_end, "z_end": z_boog_uit_start},
        {"type": "lijn", "x_start": x4_end, "z_start": z_boog_uit_start,
         "x_end": L_totaal_m, "z_end": MVuit, "horizontaal": False,
         "lengte": math.sqrt(x5_lengte**2 + (MVuit - z_boog_uit_start)**2) if x5_lengte > 0 else 0.0},
    ]

    return BoorProfiel(Rv_m=Rv, L_totaal_m=L_totaal_m, diepte_NAP_m=diepte_NAP, segmenten=segmenten)


def arc_punten(cx: float, cz: float, radius: float,
               start_hoek_rad: float, eind_hoek_rad: float,
               n: int = 50) -> list[tuple[float, float]]:
    """Discretiseer een ARC naar punten voor polyline rendering.

    Hoeken in radialen, standaard wiskundige conventie (CCW van x-as).
    """
    punten = []
    for i in range(n + 1):
        t = i / n
        hoek = start_hoek_rad + t * (eind_hoek_rad - start_hoek_rad)
        x = cx + radius * math.cos(hoek)
        z = cz + radius * math.sin(hoek)
        punten.append((x, z))
    return punten


def bereken_boorprofiel_z(
    L_totaal_m: float,
    MVin_NAP_m: float,
    MVuit_NAP_m: float,
    booghoek_gr: float,
    De_mm: float,
    dekking_min_m: float = 3.0,
) -> BoorProfiel:
    """Bereken boorprofiel voor boogzinker (type Z): 1 enkele ARC.

    Een boogzinker is een simpele gebogen boring: één ARC van intree naar uittree,
    zonder horizontaal segment of aparte schuine lijnen.

    Parameters:
        L_totaal_m: horizontale afstand intree-uittree (uit tracépunten)
        MVin_NAP_m: maaiveld intree (m NAP)
        MVuit_NAP_m: maaiveld uittree (m NAP)
        booghoek_gr: booghoek in graden (standaard 5, 7.5, of 10)
        De_mm: buitendiameter buis (mm)
        dekking_min_m: minimale gronddekking (m)
    """
    booghoek_rad = math.radians(booghoek_gr)

    # Boogradius: volgt uit L_totaal en booghoek
    # De chord (koorde) = L_totaal_m. Voor een cirkelboog: chord = 2 * R * sin(theta/2)
    # Dus R = L_totaal / (2 * sin(booghoek/2))
    half_hoek = booghoek_rad / 2
    if half_hoek < 0.001:
        # Vrijwel recht — degenereer naar lijn
        return BoorProfiel(
            Rv_m=0.0,
            L_totaal_m=L_totaal_m,
            diepte_NAP_m=min(MVin_NAP_m, MVuit_NAP_m) - dekking_min_m,
            segmenten=[{
                "type": "lijn",
                "x_start": 0.0, "z_start": MVin_NAP_m,
                "x_end": L_totaal_m, "z_end": MVuit_NAP_m,
                "horizontaal": True, "lengte": L_totaal_m,
            }],
        )

    R = L_totaal_m / (2 * math.sin(half_hoek))

    # De boog zakt onder het maaiveld. De sagitta (pijlhoogte) = R * (1 - cos(theta/2))
    sagitta = R * (1 - math.cos(half_hoek))

    # Gemiddeld maaiveld als referentie
    mv_gem = (MVin_NAP_m + MVuit_NAP_m) / 2

    # Diepste punt van de boog = maaiveld - dekking - sagitta geeft de center positie
    # De boog hangt onder het maaiveld; diepste punt = center_z - R
    # We positioneren zodat het diepste punt op dekking_min onder laagste maaiveld zit
    diepte_NAP = min(MVin_NAP_m, MVuit_NAP_m) - dekking_min_m

    # Center van de boog zit boven het diepste punt op afstand R
    # Maar de boog moet intree en uittree verbinden.
    # Horizontaal: center op L_totaal/2
    cx = L_totaal_m / 2

    # Verticaal: center boven de boorlijn, boog hangt eronder
    # Het diepste punt van de boog = cz - R (bij symmetrische boog)
    # We willen dat het diepste punt = diepte_NAP, maar we moeten ook
    # de start/eindpunten correct positioneren.
    #
    # De boog gaat van intree (0, z_in) naar uittree (L, z_uit).
    # Met center op (cx, cz) en radius R:
    #   z_in = cz - R * cos(half_hoek)  (boog begint half_hoek links van onderste punt)
    #   z_uit = cz - R * cos(half_hoek)  (idem, symmetrisch)
    #
    # Dus z_in = z_uit = cz - R*cos(half_hoek). Dit is symmetrisch.
    # De intree en uittree liggen op hetzelfde NAP-niveau op de boog.
    # Dat is prima voor een boogzinker (maaiveld verschilt, maar de buis-ingang/-uitgang zit onder maaiveld).

    # We kiezen cz zodat het laagste punt precies op diepte_NAP zit:
    cz = diepte_NAP + R  # laagste punt boog = cz - R = diepte_NAP

    # z van intree en uittree op de boog
    z_boog = cz - R * math.cos(half_hoek)

    # Booglengte (werkelijke buislengte)
    booglengte = R * booghoek_rad

    # Start- en eindhoeken voor de ARC (gemeten vanuit center, standaard math conventie)
    # Center is boven, boog hangt eronder.
    # Startpunt: (0, z_boog) → relatief tot center: (-L/2, z_boog - cz) = (-L/2, -R*cos(half))
    # Eindpunt:  (L, z_boog) → relatief: (+L/2, -R*cos(half))
    # Starthoek: atan2(-R*cos(half), -L/2) = atan2(-R*cos(half), -R*sin(half))
    #          = π + half_hoek (in het 3e kwadrant)
    start_hoek_rad = math.pi + half_hoek
    eind_hoek_rad = 2 * math.pi - half_hoek  # = π - half vanuit negatief

    segmenten = [{
        "type": "arc",
        "cx": cx,
        "cz": cz,
        "radius": R,
        "start_hoek_gr": math.degrees(start_hoek_rad),
        "eind_hoek_gr": math.degrees(eind_hoek_rad),
        "start_hoek_rad": start_hoek_rad,
        "eind_hoek_rad": eind_hoek_rad,
        "x_start": 0.0,
        "z_start": z_boog,
        "x_end": L_totaal_m,
        "z_end": z_boog,
        "booglengte": booglengte,
    }]

    return BoorProfiel(
        Rv_m=R,
        L_totaal_m=L_totaal_m,
        diepte_NAP_m=diepte_NAP,
        segmenten=segmenten,
    )


def trace_totale_afstand(punten: list[tuple[float, float]]) -> float:
    """Bereken totale horizontale afstand langs trace-punten (RD coords)."""
    if len(punten) < 2:
        return 0.0
    totaal = 0.0
    for i in range(1, len(punten)):
        dx = punten[i][0] - punten[i - 1][0]
        dy = punten[i][1] - punten[i - 1][1]
        totaal += math.sqrt(dx * dx + dy * dy)
    return totaal
