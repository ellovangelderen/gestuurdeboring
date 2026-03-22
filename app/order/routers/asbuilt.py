"""As-Built: werkelijke meetpunten invoeren en vergelijken met ontwerp."""
from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.dependencies import fetch_order, fetch_boring
from app.order.helpers import templates

router = APIRouter()


@router.get("/{order_id}/boringen/{volgnr}/asbuilt", response_class=HTMLResponse)
def asbuilt_pagina(
    request: Request,
    order_id: str,
    volgnr: int,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.order.models import AsBuiltPunt
    order = fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)

    ontwerp_punten = [p for p in boring.trace_punten if getattr(p, 'variant', 0) == 0]
    asbuilt_punten = boring.asbuilt_punten or []

    punten_wgs = {"ontwerp": [], "asbuilt": []}
    try:
        from app.geo.coords import rd_to_wgs84
        for p in ontwerp_punten:
            lat, lon = rd_to_wgs84(p.RD_x, p.RD_y)
            punten_wgs["ontwerp"].append({"label": p.label, "lat": lat, "lon": lon,
                                           "rd_x": p.RD_x, "rd_y": p.RD_y})
        for p in asbuilt_punten:
            lat, lon = rd_to_wgs84(p.RD_x, p.RD_y)
            punten_wgs["asbuilt"].append({"label": p.label, "lat": lat, "lon": lon,
                                           "rd_x": p.RD_x, "rd_y": p.RD_y})
    except Exception:
        pass

    deltas = []
    for ab in asbuilt_punten:
        ontw = next((p for p in ontwerp_punten if p.label == ab.label), None)
        if ontw:
            import math
            afwijking = math.sqrt((ab.RD_x - ontw.RD_x)**2 + (ab.RD_y - ontw.RD_y)**2)
            deltas.append({"label": ab.label, "afwijking_m": round(afwijking, 2),
                           "ontwerp_x": ontw.RD_x, "ontwerp_y": ontw.RD_y,
                           "asbuilt_x": ab.RD_x, "asbuilt_y": ab.RD_y})

    return templates.TemplateResponse(
        "order/asbuilt.html",
        {
            "request": request,
            "order": order,
            "boring": boring,
            "user": user,
            "ontwerp_punten": ontwerp_punten,
            "asbuilt_punten": asbuilt_punten,
            "punten_wgs": punten_wgs,
            "deltas": deltas,
        },
    )


@router.post("/{order_id}/boringen/{volgnr}/asbuilt")
def asbuilt_opslaan(
    order_id: str,
    volgnr: int,
    RD_x_list: str = Form(...),
    RD_y_list: str = Form(...),
    label_list: str = Form(...),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sla as-built meetpunten op en verhoog revisienummer."""
    from app.order.models import AsBuiltPunt

    fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)

    try:
        xs = [float(v.strip()) for v in RD_x_list.split(",") if v.strip()]
        ys = [float(v.strip()) for v in RD_y_list.split(",") if v.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Ongeldige coördinaten")
    labels = [v.strip() for v in label_list.split(",") if v.strip()]

    for p in boring.asbuilt_punten:
        db.delete(p)
    db.flush()

    for i, (x, y, lbl) in enumerate(zip(xs, ys, labels)):
        db.add(AsBuiltPunt(boring_id=boring.id, volgorde=i, label=lbl, RD_x=x, RD_y=y))

    if not boring.revisie or boring.revisie < 1:
        boring.revisie = 1
    else:
        boring.revisie += 1

    db.commit()
    return RedirectResponse(f"/orders/{order_id}/boringen/{volgnr}/asbuilt", status_code=303)
