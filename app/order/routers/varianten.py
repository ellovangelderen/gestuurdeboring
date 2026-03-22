"""Tracévarianten: vergelijken, toevoegen, verwijderen."""
from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.dependencies import fetch_order, fetch_boring
from app.order.helpers import templates
from app.order.models import TracePunt

router = APIRouter()


@router.get("/{order_id}/boringen/{volgnr}/varianten", response_class=HTMLResponse)
def varianten_pagina(
    request: Request,
    order_id: str,
    volgnr: int,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Tracévarianten vergelijken — kaart + tabel."""
    from app.geo.profiel import trace_totale_afstand

    order = fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)

    variant_nrs = sorted(set(getattr(p, 'variant', 0) for p in boring.trace_punten))
    varianten = []
    try:
        from app.geo.coords import rd_to_wgs84
        for v in variant_nrs:
            punten = [p for p in boring.trace_punten if getattr(p, 'variant', 0) == v]
            punten = sorted(punten, key=lambda p: p.volgorde)
            if len(punten) < 2:
                continue
            coords = [(p.RD_x, p.RD_y) for p in punten]
            lengte = trace_totale_afstand(coords)
            wgs_punten = []
            for p in punten:
                lat, lon = rd_to_wgs84(p.RD_x, p.RD_y)
                wgs_punten.append({"lat": lat, "lon": lon, "label": p.label,
                                    "rd_x": p.RD_x, "rd_y": p.RD_y})
            varianten.append({
                "nr": v,
                "naam": "Hoofd" if v == 0 else f"Variant {v}",
                "kleur": ["#cc0000", "#0066cc", "#009933", "#cc6600"][v % 4],
                "lengte": round(lengte, 1),
                "punten": len(punten),
                "wgs_punten": wgs_punten,
            })
    except Exception:
        pass

    if len(varianten) >= 2:
        hoofd = varianten[0]
        for v in varianten[1:]:
            v["delta_lengte"] = round(v["lengte"] - hoofd["lengte"], 1)

    return templates.TemplateResponse(
        "order/varianten.html",
        {
            "request": request,
            "order": order,
            "boring": boring,
            "user": user,
            "varianten": varianten,
        },
    )


@router.post("/{order_id}/boringen/{volgnr}/varianten/nieuw")
def variant_toevoegen(
    order_id: str,
    volgnr: int,
    RD_x_list: str = Form(...),
    RD_y_list: str = Form(...),
    type_list: str = Form(...),
    label_list: str = Form(...),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Voeg een nieuwe tracévariant toe."""
    fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)

    bestaande = set(getattr(p, 'variant', 0) for p in boring.trace_punten)
    nieuw_nr = max(bestaande) + 1 if bestaande else 1

    try:
        xs = [float(v.strip()) for v in RD_x_list.split(",") if v.strip()]
        ys = [float(v.strip()) for v in RD_y_list.split(",") if v.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Ongeldige coördinaten")

    types = [v.strip() for v in type_list.split(",") if v.strip()]
    labels = [v.strip() for v in label_list.split(",") if v.strip()]

    for i, (x, y, t, lbl) in enumerate(zip(xs, ys, types, labels)):
        db.add(TracePunt(
            boring_id=boring.id, volgorde=i, type=t,
            RD_x=x, RD_y=y, label=lbl, variant=nieuw_nr,
        ))
    db.commit()
    return RedirectResponse(f"/orders/{order_id}/boringen/{volgnr}/varianten", status_code=303)


@router.post("/{order_id}/boringen/{volgnr}/varianten/{vnr}/verwijder")
def variant_verwijderen(
    order_id: str,
    volgnr: int,
    vnr: int,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Verwijder een tracévariant (niet de hoofdvariant)."""
    if vnr == 0:
        raise HTTPException(status_code=400, detail="Hoofdvariant kan niet verwijderd worden")
    fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)
    for p in boring.trace_punten:
        if getattr(p, 'variant', 0) == vnr:
            db.delete(p)
    db.commit()
    return RedirectResponse(f"/orders/{order_id}/boringen/{volgnr}/varianten", status_code=303)
