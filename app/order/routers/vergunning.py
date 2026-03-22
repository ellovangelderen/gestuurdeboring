"""Vergunningscheck: links naar portalen + checklist."""
from fastapi import APIRouter, Depends, Form
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.dependencies import fetch_order, fetch_boring
from app.order.helpers import _parse_checklist, templates

router = APIRouter()


@router.get("/{order_id}/boringen/{volgnr}/vergunning", response_class=HTMLResponse)
def vergunningscheck_pagina(
    request: Request,
    order_id: str,
    volgnr: int,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Vergunningscheck: links naar relevante portalen op basis van coördinaten."""
    order = fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)

    links = []
    intree = next((p for p in boring.trace_punten
                   if getattr(p, 'variant', 0) == 0 and p.type == "intree"), None)

    if intree:
        from app.geo.coords import rd_to_wgs84
        lat, lon = rd_to_wgs84(intree.RD_x, intree.RD_y)

        links.append({
            "naam": "Omgevingsloket",
            "omschrijving": "Check welke regels gelden op deze locatie",
            "url": f"https://omgevingswet.overheid.nl/regels-op-de-kaart/viewer/regels?locatie-stelsel=etrs89&locatie-x={lon:.6f}&locatie-y={lat:.6f}",
            "type": "primair",
        })
        links.append({
            "naam": "PDOK Viewer",
            "omschrijving": "Kadastrale kaart, bestemmingsplannen",
            "url": f"https://app.pdok.nl/viewer/#x={intree.RD_x:.2f}&y={intree.RD_y:.2f}&z=12",
            "type": "kaart",
        })
        if order.waterkering_url:
            links.append({
                "naam": "Waterschapskaart",
                "omschrijving": "Waterkering, watergang, beschermingszone",
                "url": order.waterkering_url,
                "type": "waterschap",
            })
        links.append({
            "naam": "Google Maps",
            "omschrijving": "Luchtfoto, streetview, omgeving",
            "url": f"https://www.google.com/maps/@{lat:.6f},{lon:.6f},17z",
            "type": "kaart",
        })
        links.append({
            "naam": "BAG Viewer",
            "omschrijving": "Gebouwen, adressen, bouwjaar",
            "url": f"https://bagviewer.kadaster.nl/lvbag/bag-viewer/#?geometry.x={intree.RD_x:.2f}&geometry.y={intree.RD_y:.2f}&zoomlevel=7",
            "type": "kaart",
        })
        links.append({
            "naam": "Bodemloket",
            "omschrijving": "Bodemverontreinigingen, saneringslocaties",
            "url": f"https://www.bodemloket.nl/kaart?coords={intree.RD_x:.0f},{intree.RD_y:.0f}&zoom=14",
            "type": "kaart",
        })

        try:
            from app.admin.models import KaartLink
            db_links = db.query(KaartLink).order_by(KaartLink.volgorde).all()
            for kl in db_links:
                if any(kl.naam.lower() in l["naam"].lower() for l in links):
                    continue
                links.append({
                    "naam": kl.naam,
                    "omschrijving": kl.omschrijving or "",
                    "url": kl.url,
                    "type": kl.categorie or "kaart",
                })
        except Exception:
            pass

    return templates.TemplateResponse(
        "order/vergunning.html",
        {
            "request": request,
            "order": order,
            "boring": boring,
            "user": user,
            "links": links,
            "intree": intree,
            "vergunning_status": order.vergunning or "-",
            "checklist": _parse_checklist(order.vergunning_checklist),
        },
    )


@router.post("/{order_id}/boringen/{volgnr}/vergunning/checklist")
def vergunning_checklist_opslaan(
    order_id: str,
    volgnr: int,
    omgevingsloket: str = Form(""),
    gemeente: str = Form(""),
    waterschap: str = Form(""),
    provincie: str = Form(""),
    rws: str = Form(""),
    bodemloket: str = Form(""),
    prorail: str = Form(""),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sla vergunning checklist op."""
    import json
    order = fetch_order(order_id, db)
    checklist = {
        "omgevingsloket": omgevingsloket == "on",
        "gemeente": gemeente == "on",
        "waterschap": waterschap == "on",
        "provincie": provincie == "on",
        "rws": rws == "on",
        "bodemloket": bodemloket == "on",
        "prorail": prorail == "on",
    }
    order.vergunning_checklist = json.dumps(checklist)
    db.commit()
    return RedirectResponse(f"/orders/{order_id}/boringen/{volgnr}/vergunning", status_code=303)
