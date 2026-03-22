"""Analyse: conflictcheck + topotijdreis."""
from fastapi import APIRouter, Depends
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.dependencies import fetch_order, fetch_boring
from app.order.helpers import templates
from app.order.models import KLICLeiding

router = APIRouter()

TOPOTIJDREIS_JAREN = [
    1815, 1850, 1900, 1910, 1920, 1925, 1930, 1940, 1950,
    1960, 1970, 1975, 1980, 1990, 2000, 2005, 2010, 2015,
]


@router.get("/{order_id}/boringen/{volgnr}/topotijdreis", response_class=HTMLResponse)
def topotijdreis_pagina(
    request: Request,
    order_id: str,
    volgnr: int,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Topotijdreis: historische kaarten voor het tracégebied."""
    order = fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)

    punten_wgs84 = []
    rd_center = None
    try:
        from app.geo.coords import rd_to_wgs84
        for p in boring.trace_punten:
            lat, lon = rd_to_wgs84(p.RD_x, p.RD_y)
            punten_wgs84.append({"label": p.label, "lat": lat, "lon": lon,
                                  "rd_x": p.RD_x, "rd_y": p.RD_y})
        if boring.trace_punten:
            xs = [p.RD_x for p in boring.trace_punten]
            ys = [p.RD_y for p in boring.trace_punten]
            rd_center = {"x": sum(xs) / len(xs), "y": sum(ys) / len(ys)}
    except Exception:
        pass

    topotijdreis_url = None
    if punten_wgs84:
        mid = punten_wgs84[len(punten_wgs84) // 2]
        topotijdreis_url = f"https://www.topotijdreis.nl/#/52/{mid['lat']:.6f}/{mid['lon']:.6f}"

    return templates.TemplateResponse(
        "order/topotijdreis.html",
        {
            "request": request,
            "order": order,
            "boring": boring,
            "user": user,
            "punten_wgs84": punten_wgs84,
            "rd_center": rd_center,
            "topotijdreis_url": topotijdreis_url,
            "jaren": TOPOTIJDREIS_JAREN,
        },
    )


@router.get("/{order_id}/boringen/{volgnr}/conflictcheck", response_class=HTMLResponse)
def conflictcheck_pagina(
    request: Request,
    order_id: str,
    volgnr: int,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Toon conflictcheck: boortracé vs KLIC leidingen."""
    from app.geo.conflictcheck import check_conflicts
    from app.geo.profiel import bereken_boorprofiel, bereken_boorprofiel_z, trace_totale_afstand

    order = fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)

    fout = None
    conflicts = []
    profiel = None

    punten = boring.trace_punten
    mv = boring.maaiveld_override
    if len(punten) < 2:
        fout = "Geen tracépunten — sla eerst het tracé op."
    elif mv is None or mv.MVin_NAP_m is None or mv.MVuit_NAP_m is None:
        fout = "Geen maaiveld — vul eerst MVin/MVuit in."
    else:
        coords = [(p.RD_x, p.RD_y) for p in punten]
        L_totaal = trace_totale_afstand(coords)
        if L_totaal < 1.0:
            fout = "Tracé te kort."
        else:
            try:
                if boring.type == "Z" and boring.booghoek_gr:
                    profiel = bereken_boorprofiel_z(
                        L_totaal_m=L_totaal,
                        MVin_NAP_m=mv.MVin_NAP_m, MVuit_NAP_m=mv.MVuit_NAP_m,
                        booghoek_gr=boring.booghoek_gr, De_mm=boring.De_mm or 160.0,
                    )
                else:
                    profiel = bereken_boorprofiel(
                        L_totaal_m=L_totaal,
                        MVin_NAP_m=mv.MVin_NAP_m, MVuit_NAP_m=mv.MVuit_NAP_m,
                        alpha_in_gr=boring.intreehoek_gr or 18.0,
                        alpha_uit_gr=boring.uittreehoek_gr or 22.0,
                        De_mm=boring.De_mm or 160.0,
                    )
            except Exception:
                fout = "Fout bij berekening boorprofiel."

    klic_leidingen = []
    if profiel and not fout:
        laatste_upload = None
        if order.klic_uploads:
            uploads = [u for u in order.klic_uploads if u.verwerkt]
            if uploads:
                laatste_upload = sorted(uploads, key=lambda u: u.upload_datum)[-1]
        if laatste_upload:
            klic_leidingen = (
                db.query(KLICLeiding)
                .filter_by(klic_upload_id=laatste_upload.id)
                .all()
            )

        if not klic_leidingen:
            fout = "Geen KLIC leidingen beschikbaar — upload eerst een KLIC bestand."
        else:
            coords = [(p.RD_x, p.RD_y) for p in punten]
            conflicts = check_conflicts(coords, profiel, klic_leidingen)

    onbekend = [c for c in conflicts if c.diepte_onbekend]
    te_dicht = [c for c in conflicts if not c.diepte_onbekend and c.afstand_m < 0.5]
    waarschuwing = [c for c in conflicts if not c.diepte_onbekend and 0.5 <= c.afstand_m < 1.5]
    veilig = [c for c in conflicts if not c.diepte_onbekend and c.afstand_m >= 1.5]

    return templates.TemplateResponse(
        "order/conflictcheck.html",
        {
            "request": request,
            "order": order,
            "boring": boring,
            "user": user,
            "fout": fout,
            "onbekend": onbekend,
            "te_dicht": te_dicht,
            "waarschuwing": waarschuwing,
            "veilig": veilig,
            "totaal_leidingen": len(klic_leidingen),
            "totaal_in_corridor": len(conflicts),
        },
    )
