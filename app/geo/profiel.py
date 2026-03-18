"""Boorprofiel geometrie — kernberekening voor HDD lengteprofiel met ARCs."""
import math
from dataclasses import dataclass, field


@dataclass
class BoorProfiel:
    Rv_m: float                    # buigradius
    L_totaal_m: float              # horizontale afstand intree-uittree
    diepte_NAP_m: float            # NAP-hoogte diepste punt horizontaal segment
    segmenten: list = field(default_factory=list)  # lijst van profiel-segmenten


def bereken_Rv(De_mm: float) -> float:
    """Minimale buigradius: Rv = 1200 x De (in meters)."""
    return 1200.0 * De_mm / 1000.0


def bereken_boorprofiel(
    L_totaal_m: float,
    MVin_NAP_m: float,
    MVuit_NAP_m: float,
    alpha_in_gr: float,
    alpha_uit_gr: float,
    De_mm: float,
    dekking_min_m: float = 3.0,
) -> BoorProfiel:
    """Bereken het complete boorprofiel met intreeboog, horizontaal segment, en uittreeboog.

    Profiel in verticaal vlak:
      x = horizontale afstand vanaf intreepunt (0..L_totaal)
      z = NAP hoogte

    Segmenten:
      1. Lijn: intreepunt schuin omlaag onder intreehoek
      2. ARC: intreeboog (van schuine lijn naar horizontaal)
      3. Lijn: horizontaal segment
      4. ARC: uittreeboog (van horizontaal naar schuine lijn omhoog)
      5. Lijn: uittreepunt schuin omhoog onder uittreehoek
    """
    Rv = bereken_Rv(De_mm)

    alpha_in_rad = math.radians(alpha_in_gr)
    alpha_uit_rad = math.radians(alpha_uit_gr)

    # Tangent lengtes van de bogen (horizontale en verticale componenten)
    Tin_h = Rv * math.sin(alpha_in_rad)
    Tin_v = Rv * (1 - math.cos(alpha_in_rad))
    Tuit_h = Rv * math.sin(alpha_uit_rad)
    Tuit_v = Rv * (1 - math.cos(alpha_uit_rad))

    # Controleer of trace lang genoeg is
    L_horiz = L_totaal_m - Tin_h - Tuit_h
    if L_horiz < 0:
        # Trace te kort: pas Rv aan zodat het net past
        # Rv_max zodat Rv*sin(a_in) + Rv*sin(a_uit) = L_totaal
        Rv = L_totaal_m / (math.sin(alpha_in_rad) + math.sin(alpha_uit_rad))
        Tin_h = Rv * math.sin(alpha_in_rad)
        Tin_v = Rv * (1 - math.cos(alpha_in_rad))
        Tuit_h = Rv * math.sin(alpha_uit_rad)
        Tuit_v = Rv * (1 - math.cos(alpha_uit_rad))
        L_horiz = 0.0

    # Rechte stukken boven de bogen (van maaiveld naar begin boog)
    # De schuine lijn begint bij maaiveld en gaat onder hoek naar beneden.
    # De boog sluit aan waar de lijn tangent raakt aan de boog.
    # Intree schuine lijn: van (0, MVin) naar beneden onder alpha_in
    # Horizontale lengte schuine intree lijn = afstand tot tangentpunt boog
    # Maar de boog begint NA de schuine lijn. De tangentlengte Tin_h is de
    # horizontale afstand van tangentpunt tot einde boog (= begin horizontaal).
    # Dus de schuine lijn loopt van x=0 tot x=x_boog_start.

    # Diepte van het horizontaal segment:
    # Verticale daling door schuine lijn + boog intree = Tin_h * tan(alpha_in)
    # Maar dat klopt niet helemaal. De verticale daling door de boog = Tin_v.
    # De schuine lijn voor de boog kan 0 lengte hebben als de boog direct begint.

    # Correct model:
    # Het punt waar de intreeboog begint heeft x-coordinaat x1 en de boog
    # eindigt bij x-coordinaat x1 + Tin_h. De boog gaat van hoek alpha_in
    # naar hoek 0 (horizontaal).
    #
    # De schuine intree lijn loopt van (0, MVin) naar (x1, z1) onder hoek alpha_in.
    # De boog buigt van alpha_in naar horizontaal.
    # Het horizontaal segment loopt op NAP-hoogte diepte_NAP.
    #
    # De NAP-hoogte van het begin van de intreeboog:
    #   z_boog_start = diepte_NAP + Tin_v
    # De verticale daling over de schuine lijn:
    #   MVin - z_boog_start = x1 * tan(alpha_in)
    #   x1 = (MVin - z_boog_start) / tan(alpha_in)
    #
    # Analoog voor uittrede:
    #   z_boog_start_uit = diepte_NAP + Tuit_v
    #   x5_lengte = (MVuit - z_boog_start_uit) / tan(alpha_uit)

    # Diepte berekening:
    # De diepte wordt bepaald door de minimale dekking.
    # Het laagste punt van het maaiveld bepaalt de maximaal toelaatbare NAP hoogte.
    diepte_NAP = min(MVin_NAP_m, MVuit_NAP_m) - dekking_min_m

    # Check dat diepte haalbaar is (diepte moet lager zijn dan de boog-tangenten)
    # De boog intree brengt je tot diepte_NAP + Tin_v, dit moet boven MVin liggen
    # anders is de schuine lijn negatief (leiding komt omhoog ipv omlaag).
    # In praktijk bij standaard HDD is dit altijd OK.

    # z-coordinaten
    z_boog_in_start = diepte_NAP + Tin_v    # NAP van begin intreeboog
    z_boog_uit_start = diepte_NAP + Tuit_v  # NAP van begin uittreeboog

    # Schuine lijn intree: van (0, MVin) naar (x1, z_boog_in_start)
    if alpha_in_gr > 0 and math.tan(alpha_in_rad) > 0:
        x1 = (MVin_NAP_m - z_boog_in_start) / math.tan(alpha_in_rad)
    else:
        x1 = 0.0
    x1 = max(x1, 0.0)  # kan niet negatief zijn

    # Schuine lijn uittree: van (x5_start, z_boog_uit_start) naar (L_totaal, MVuit)
    if alpha_uit_gr > 0 and math.tan(alpha_uit_rad) > 0:
        x5_lengte = (MVuit_NAP_m - z_boog_uit_start) / math.tan(alpha_uit_rad)
    else:
        x5_lengte = 0.0
    x5_lengte = max(x5_lengte, 0.0)

    # x-posities van alle segmenten
    # Segment 1: lijn x=0 tot x=x1
    # Segment 2: arc  x=x1 tot x=x1+Tin_h
    x2_end = x1 + Tin_h
    # Segment 3: lijn x=x2_end tot x=x3_end (horizontaal)
    x3_end = L_totaal_m - x5_lengte - Tuit_h
    # Segment 4: arc  x=x3_end tot x=x3_end+Tuit_h
    x4_end = x3_end + Tuit_h
    # Segment 5: lijn x=x4_end tot x=L_totaal

    # Intree ARC centrum: de boog gaat van hoek -alpha_in (omlaag) naar 0 (horizontaal)
    # Center zit recht onder het tangentpunt, op afstand Rv
    arc_in_cx = x1 + Tin_h   # = x2_end
    arc_in_cz = diepte_NAP + Rv  # center is Rv boven het horizontale segment

    # Uittree ARC centrum
    arc_uit_cx = x3_end       # begin van uittree boog
    arc_uit_cz = diepte_NAP + Rv

    segmenten = []

    # Segment 1: schuine lijn intree
    segmenten.append({
        "type": "lijn",
        "x_start": 0.0,
        "z_start": MVin_NAP_m,
        "x_end": x1,
        "z_end": z_boog_in_start,
        "horizontaal": False,
        "lengte": math.sqrt(x1**2 + (MVin_NAP_m - z_boog_in_start)**2) if x1 > 0 else 0.0,
    })

    # Segment 2: intree ARC
    # In ezdxf/SVG conventie: hoeken in graden, gemeten CCW van positieve x-as
    # De boog gaat van hoek (270 - alpha_in_gr) naar 270° (= -90° = recht omlaag naar beneden)
    # Eigenlijk: center is boven de boorlijn, boog loopt aan onderzijde
    # Hoeken gemeten vanaf center: de boog gaat van (270 - alpha_in_gr) naar 270°
    # In ons coordinatensysteem (x=rechts, z=omhoog):
    #   - Center op (arc_in_cx, arc_in_cz) = (x2_end, diepte_NAP + Rv)
    #   - Startpunt boog: (x1, z_boog_in_start) → relatief: (-Tin_h, -(Rv - Tin_v)) = (-Rv*sin(a), -Rv*cos(a))
    #     hoek = atan2(-(Rv*cos(a)), -(Rv*sin(a))) = atan2(-Rv*cos(a), -Rv*sin(a))
    #     = 180 + atan2(Rv*cos(a), Rv*sin(a)) = 180 + (90-a) = 270-a  [in graden]
    #   - Eindpunt boog: (x2_end, diepte_NAP) → relatief: (0, -Rv) → hoek = 270°
    segmenten.append({
        "type": "arc",
        "cx": arc_in_cx,
        "cz": arc_in_cz,
        "radius": Rv,
        "start_hoek_gr": 180.0 + alpha_in_gr,   # = 180+alpha vanuit center gezien
        "eind_hoek_gr": 180.0,                   # horizontaal links vanuit center
        "start_hoek_rad": math.pi + alpha_in_rad,
        "eind_hoek_rad": math.pi,
        "x_start": x1,
        "z_start": z_boog_in_start,
        "x_end": x2_end,
        "z_end": diepte_NAP,
    })

    # Segment 3: horizontaal segment
    horiz_lengte = max(x3_end - x2_end, 0.0)
    segmenten.append({
        "type": "lijn",
        "x_start": x2_end,
        "z_start": diepte_NAP,
        "x_end": x3_end,
        "z_end": diepte_NAP,
        "horizontaal": True,
        "lengte": horiz_lengte,
    })

    # Segment 4: uittree ARC
    # Center op (arc_uit_cx, arc_uit_cz) = (x3_end, diepte_NAP + Rv)
    # Startpunt: (x3_end, diepte_NAP) → relatief: (0, -Rv) → hoek = 0° (recht naar rechts vanuit center? Nee)
    # relatief: (0, -Rv) → hoek = 270° in standaard math
    # Eindpunt: (x4_end, z_boog_uit_start) → relatief: (Tuit_h, -(Rv-Tuit_v)) = (Rv*sin(a), -Rv*cos(a))
    #   hoek = atan2(-Rv*cos(a), Rv*sin(a)) = 360 - a  [in graden]
    segmenten.append({
        "type": "arc",
        "cx": arc_uit_cx,
        "cz": arc_uit_cz,
        "radius": Rv,
        "start_hoek_gr": 0.0,                      # horizontaal rechts vanuit center
        "eind_hoek_gr": 360.0 - alpha_uit_gr,      # naar uittreehoek
        "start_hoek_rad": 0.0,
        "eind_hoek_rad": 2 * math.pi - alpha_uit_rad,
        "x_start": x3_end,
        "z_start": diepte_NAP,
        "x_end": x4_end,
        "z_end": z_boog_uit_start,
    })

    # Segment 5: schuine lijn uittree
    segmenten.append({
        "type": "lijn",
        "x_start": x4_end,
        "z_start": z_boog_uit_start,
        "x_end": L_totaal_m,
        "z_end": MVuit_NAP_m,
        "horizontaal": False,
        "lengte": math.sqrt(x5_lengte**2 + (MVuit_NAP_m - z_boog_uit_start)**2) if x5_lengte > 0 else 0.0,
    })

    return BoorProfiel(
        Rv_m=Rv,
        L_totaal_m=L_totaal_m,
        diepte_NAP_m=diepte_NAP,
        segmenten=segmenten,
    )


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
