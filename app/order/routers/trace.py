"""Trace: tracépunten invoeren op kaart."""
from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.dependencies import fetch_order, fetch_boring
from app.order.helpers import templates
from app.order.models import KLICLeiding, TracePunt
from app.geo.pdok_urls import genereer_pdok_url
from app.geo.waterschap import bepaal_waterschap, waterschap_kaart_url

router = APIRouter()


@router.get("/{order_id}/boringen/{volgnr}/trace", response_class=HTMLResponse)
def trace_form(
    request: Request,
    order_id: str,
    volgnr: int,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)
    punten_wgs84 = []
    try:
        from app.geo.coords import rd_to_wgs84
        for p in boring.trace_punten:
            if getattr(p, 'variant', 0) != 0:
                continue
            lat, lon = rd_to_wgs84(p.RD_x, p.RD_y)
            punten_wgs84.append({
                "label": p.label, "lat": lat, "lon": lon,
                "type": p.type, "rd_x": p.RD_x, "rd_y": p.RD_y,
                "rh": p.Rh_m or "",
            })
    except Exception:
        pass

    # KLIC leidingen als GeoJSON voor kaartoverlay
    klic_geojson = []
    try:
        from app.geo.coords import rd_to_wgs84 as _r2w
        from shapely import from_wkt
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
            KLIC_KLEUREN = {
                "LAAGSPANNING": "#BE9600", "MIDDENSPANNING": "#00823C",
                "HOOGSPANNING": "#DC0000", "LD-GAS": "#A05000",
                "WATERLEIDING": "#0055AA", "RIOOL-VRIJVERVAL": "#7030A0",
                "PERSRIOOL": "#7030A0",
            }
            for l in klic_leidingen:
                if not l.geometrie_wkt:
                    continue
                try:
                    geom = from_wkt(l.geometrie_wkt)
                    if hasattr(geom, 'coords') and len(list(geom.coords)) >= 2:
                        wgs_coords = [list(_r2w(c[0], c[1])) for c in geom.coords]
                        klic_geojson.append({
                            "coords": wgs_coords,
                            "kleur": KLIC_KLEUREN.get(l.dxf_laag, "#999"),
                            "label": f"{l.beheerder or ''} - {l.leidingtype or ''}",
                        })
                except Exception:
                    continue
    except Exception:
        pass

    return templates.TemplateResponse(
        "order/trace.html",
        {
            "request": request,
            "order": order,
            "boring": boring,
            "punten_wgs84": punten_wgs84,
            "klic_geojson": klic_geojson,
            "user": user,
        },
    )


@router.post("/{order_id}/boringen/{volgnr}/trace")
def trace_opslaan(
    order_id: str,
    volgnr: int,
    RD_x_list: str = Form(...),
    RD_y_list: str = Form(...),
    type_list: str = Form(...),
    label_list: str = Form(...),
    Rh_list: str = Form(""),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)

    try:
        xs = [float(v.strip()) for v in RD_x_list.split(",") if v.strip()]
        ys = [float(v.strip()) for v in RD_y_list.split(",") if v.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Ongeldige RD-coordinaten")

    types = [v.strip() for v in type_list.split(",") if v.strip()]
    labels = [v.strip() for v in label_list.split(",") if v.strip()]
    rhs = [v.strip() for v in Rh_list.split(",")] if Rh_list else [""] * len(xs)

    # Alleen hoofdvariant (0) verwijderen, alternatieven bewaren
    for punt in boring.trace_punten:
        if getattr(punt, 'variant', 0) == 0:
            db.delete(punt)
    db.flush()

    for i, (x, y, t, label) in enumerate(zip(xs, ys, types, labels)):
        rh_val = rhs[i] if i < len(rhs) else ""
        try:
            rh = float(rh_val) if rh_val else None
        except ValueError:
            rh = None
        punt = TracePunt(
            boring_id=boring.id,
            volgorde=i,
            type=t,
            RD_x=x,
            RD_y=y,
            label=label,
            Rh_m=rh,
        )
        db.add(punt)

    # Auto-genereer PDOK + waterschap URLs op basis van intree-punt
    intree_idx = next((i for i, t in enumerate(types) if t == "intree"), None)
    if intree_idx is not None and intree_idx < len(xs):
        order = fetch_order(order_id, db)
        ix, iy = xs[intree_idx], ys[intree_idx]
        order.pdok_url = genereer_pdok_url(ix, iy)
        try:
            from app.geo.coords import rd_to_wgs84 as _r2w
            _lat, _lon = _r2w(ix, iy)
            order.google_maps_url = f"https://www.google.com/maps/@{_lat:.6f},{_lon:.6f},17z"
        except Exception:
            pass
        ws_naam = bepaal_waterschap(ix, iy)
        ws_url = waterschap_kaart_url(ws_naam)
        if ws_url:
            order.waterkering_url = ws_url

    db.commit()
    return RedirectResponse(f"/orders/{order_id}/boringen/{volgnr}", status_code=303)
