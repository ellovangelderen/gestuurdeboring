"""Boring CRUD: detail + update."""
from fastapi import APIRouter, Depends, Form
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.dependencies import fetch_order, fetch_boring
from app.order.helpers import _f, _i, templates

router = APIRouter()


@router.get("/{order_id}/boringen/{volgnr}", response_class=HTMLResponse)
def boring_detail(
    request: Request,
    order_id: str,
    volgnr: int,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)

    # Parameter validatie + profiel preview
    preview = None
    waarschuwingen = []
    if boring.type in ("B", "N") and boring.trace_punten and boring.maaiveld_override:
        try:
            from app.geo.profiel import bereken_boorprofiel, bereken_Rv, trace_totale_afstand, ProfielPunt
            import math

            coords = [(p.RD_x, p.RD_y) for p in boring.trace_punten
                       if getattr(p, 'variant', 0) == 0]
            if len(coords) >= 2:
                L = trace_totale_afstand(coords)
                Rv = bereken_Rv(boring.De_mm or 160.0)
                a_in = math.radians(boring.intreehoek_gr or 18.0)
                a_uit = math.radians(boring.uittreehoek_gr or 22.0)
                Tin_h = Rv * math.sin(a_in)
                Tuit_h = Rv * math.sin(a_uit)
                min_lengte = Tin_h + Tuit_h

                mv = boring.maaiveld_override
                dekking = min(mv.MVin_NAP_m, mv.MVuit_NAP_m) - (
                    bereken_boorprofiel(
                        L_totaal_m=L, MVin_NAP_m=mv.MVin_NAP_m, MVuit_NAP_m=mv.MVuit_NAP_m,
                        alpha_in_gr=boring.intreehoek_gr or 18.0,
                        alpha_uit_gr=boring.uittreehoek_gr or 22.0,
                        De_mm=boring.De_mm or 160.0,
                    ).diepte_NAP_m
                )

                preview = {
                    "L_totaal": round(L, 1),
                    "Rv": round(Rv, 1),
                    "Tin_h": round(Tin_h, 1),
                    "Tuit_h": round(Tuit_h, 1),
                    "min_lengte": round(min_lengte, 1),
                    "dekking": round(dekking, 1),
                }

                if L < min_lengte:
                    waarschuwingen.append(
                        f"Boring te kort ({L:.0f}m) voor Rv={Rv:.0f}m. "
                        f"Minimaal {min_lengte:.0f}m nodig (Tin={Tin_h:.0f}m + Tuit={Tuit_h:.0f}m). "
                        f"Rv wordt automatisch verkleind."
                    )
                if dekking < 1.5:
                    waarschuwingen.append(f"Dekking is slechts {dekking:.1f}m — controleer diepte.")
        except Exception:
            pass

    # Boormachines voor dropdown
    machines = []
    try:
        from app.admin.models import Boormachine
        machines = db.query(Boormachine).order_by(Boormachine.naam).all()
    except Exception:
        pass

    return templates.TemplateResponse(
        "order/boring_detail.html",
        {
            "request": request,
            "order": order,
            "boring": boring,
            "user": user,
            "preview": preview,
            "waarschuwingen": waarschuwingen,
            "machines": machines,
        },
    )


@router.post("/{order_id}/boringen/{volgnr}/update")
def boring_update(
    order_id: str,
    volgnr: int,
    materiaal: str = Form("PE100"),
    SDR: str = Form("11"),
    De_mm: str = Form("160.0"),
    dn_mm: str = Form(""),
    medium: str = Form("Drukloos"),
    Db_mm: str = Form("60.0"),
    Dp_mm: str = Form("110.0"),
    Dg_mm: str = Form("240.0"),
    intreehoek_gr: str = Form("18.0"),
    uittreehoek_gr: str = Form("22.0"),
    booghoek_gr: str = Form(""),
    stand: str = Form(""),
    naam: str = Form(""),
    machine_type: str = Form(""),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)
    boring.materiaal = materiaal
    boring.SDR = _i(SDR) or 11
    boring.De_mm = _f(De_mm) or 160.0
    boring.dn_mm = _f(dn_mm)
    boring.medium = medium
    boring.Db_mm = _f(Db_mm) or 60.0
    boring.Dp_mm = _f(Dp_mm) or 110.0
    boring.Dg_mm = _f(Dg_mm) or 240.0
    boring.intreehoek_gr = _f(intreehoek_gr) or 18.0
    boring.uittreehoek_gr = _f(uittreehoek_gr) or 22.0
    boring.booghoek_gr = _f(booghoek_gr)
    boring.stand = _i(stand)
    boring.naam = naam.strip() or None
    boring.machine_type = machine_type.strip() or None
    db.commit()
    return RedirectResponse(f"/orders/{order_id}/boringen/{volgnr}", status_code=303)
