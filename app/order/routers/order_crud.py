"""Order CRUD: aanmaken, detail, update, import, factuur."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.dependencies import fetch_order, get_workspace_id
from app.order.helpers import MAX_EXCEL_SIZE, _STATUS_MAP, _i, templates
from app.order.klantcodes import (
    BORING_TYPES, KLANTCODES, ORDER_STATUSES, VERGUNNING_TYPES,
    get_akkoord_contact, get_klant_naam,
)
from app.order.models import Boring, Order

router = APIRouter()


@router.get("/nieuw", response_class=HTMLResponse)
def order_nieuw_form(
    request: Request,
    user: str = Depends(get_current_user),
):
    return templates.TemplateResponse(
        "order/create.html",
        {
            "request": request,
            "user": user,
            "klantcodes": KLANTCODES,
            "vergunning_types": VERGUNNING_TYPES,
            "boring_types": BORING_TYPES,
        },
    )


@router.post("/nieuw")
def order_nieuw_opslaan(
    request: Request,
    ordernummer: str = Form(...),
    locatie: str = Form(""),
    klantcode: str = Form(""),
    opdrachtgever: str = Form(""),
    vergunning: str = Form("-"),
    tekenaar: str = Form("martien"),
    akkoord_contact: str = Form(""),
    deadline: str = Form(""),
    type_1: str = Form(""),
    aantal_1: str = Form("1"),
    type_2: str = Form(""),
    aantal_2: str = Form("0"),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not ordernummer or not ordernummer.strip():
        raise HTTPException(status_code=400, detail="Ordernummer is verplicht")

    workspace_id = get_workspace_id(user)

    contact = akkoord_contact.strip() if akkoord_contact else ""
    if not contact and klantcode:
        contact = get_akkoord_contact(klantcode)

    deadline_dt = None
    if deadline and deadline.strip():
        try:
            deadline_dt = datetime.strptime(deadline.strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    order = Order(
        workspace_id=workspace_id,
        ordernummer=ordernummer.strip(),
        locatie=locatie.strip() or None,
        klantcode=klantcode or None,
        opdrachtgever=opdrachtgever.strip() or None,
        vergunning=vergunning,
        tekenaar=tekenaar.strip() or "martien",
        akkoord_contact=contact or None,
        deadline=deadline_dt,
    )
    db.add(order)
    db.flush()

    volgnr = 1
    for btype, aantal_str in [(type_1, aantal_1), (type_2, aantal_2)]:
        if not btype:
            continue
        aantal = _i(aantal_str) or 0
        for _ in range(aantal):
            boring = Boring(
                order_id=order.id,
                volgnummer=volgnr,
                type=btype,
                aangemaakt_door=user,
            )
            db.add(boring)
            volgnr += 1

    db.commit()
    db.refresh(order)
    return RedirectResponse(f"/orders/{order.id}", status_code=303)


# ── Excel Import (moet BOVEN /{order_id} staan) ──────────────────────────

@router.get("/import", response_class=HTMLResponse)
async def import_pagina(request: Request):
    return templates.TemplateResponse("import.html", {"request": request})


@router.post("/import")
async def import_uitvoeren(
    request: Request,
    bestand: UploadFile = File(...),
    wissen: str = Form(""),
    db: Session = Depends(get_db),
):
    """Upload en importeer een Excel order overview."""
    import openpyxl
    from io import BytesIO
    from app.order.import_excel import import_vergunning_sheet

    gewist = False
    if wissen == "ja":
        from app.order.models import (
            AsBuiltPunt, WerkplanAfbeelding, Berekening, Doorsnede,
            MaaiveldOverride, TracePunt, BoringKLIC, KLICLeiding,
            KLICUpload, EVZone, EVPartij, EmailContact, Boring, Order,
        )
        for model in [
            AsBuiltPunt, WerkplanAfbeelding, Berekening, Doorsnede,
            MaaiveldOverride, TracePunt, BoringKLIC, KLICLeiding,
            KLICUpload, EVZone, EVPartij, EmailContact, Boring, Order,
        ]:
            db.query(model).delete()
        db.commit()
        gewist = True

    content = await bestand.read()
    if len(content) > MAX_EXCEL_SIZE:
        raise HTTPException(status_code=413, detail=f"Bestand te groot (max {MAX_EXCEL_SIZE // 1024 // 1024}MB)")
    wb = openpyxl.load_workbook(BytesIO(content), data_only=True)

    stats = {"orders": 0, "boringen": 0, "overgeslagen": 0, "fouten": 0}

    if "Vergunning" in wb.sheetnames:
        result = import_vergunning_sheet(db, wb["Vergunning"])
        for k in stats:
            stats[k] += result.get(k, 0)

    return templates.TemplateResponse("import.html", {
        "request": request,
        "resultaat": stats,
        "bestandsnaam": bestand.filename,
        "gewist": gewist,
    })


# ── Order detail ────────────────────────────────────────────────────────────

@router.get("/{order_id}", response_class=HTMLResponse)
def order_detail(
    request: Request,
    order_id: str,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = fetch_order(order_id, db)
    boringen = sorted(order.boringen, key=lambda b: b.volgnummer)
    return templates.TemplateResponse(
        "order/detail.html",
        {
            "request": request,
            "order": order,
            "boringen": boringen,
            "user": user,
            "statuses": {s["value"]: s["label"] for s in ORDER_STATUSES},
            "klantcodes": KLANTCODES,
            "vergunning_types": VERGUNNING_TYPES,
        },
    )


@router.post("/{order_id}/update")
def order_update(
    order_id: str,
    ordernummer: str = Form(...),
    locatie: str = Form(""),
    klantcode: str = Form(""),
    opdrachtgever: str = Form(""),
    vergunning: list = Form([]),
    tekenaar: str = Form("martien"),
    akkoord_contact: str = Form(""),
    deadline: str = Form(""),
    status: str = Form(""),
    notitie: str = Form(""),
    prio: str = Form(""),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not ordernummer or not ordernummer.strip():
        raise HTTPException(status_code=400, detail="Ordernummer is verplicht")
    order = fetch_order(order_id, db)
    order.ordernummer = ordernummer.strip()
    order.locatie = locatie.strip() or None
    order.klantcode = klantcode or None
    order.opdrachtgever = opdrachtgever.strip() or None
    order.vergunning = ",".join(vergunning) if vergunning else "-"
    order.tekenaar = tekenaar.strip() or "martien"
    order.akkoord_contact = akkoord_contact.strip() or None
    if deadline and deadline.strip():
        try:
            order.deadline = datetime.strptime(deadline.strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    else:
        order.deadline = None
    if status:
        order.status = status
    order.notitie = notitie.strip() or None
    order.prio = prio == "on"
    db.commit()
    return RedirectResponse(f"/orders/{order_id}", status_code=303)


# ── Facturatie (concept) ───────────────────────────────────────────────────

@router.get("/{order_id}/factuur", response_class=HTMLResponse)
def factuur_concept(
    request: Request,
    order_id: str,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Concept-factuur voor een order."""
    order = fetch_order(order_id, db)
    klant_naam = get_klant_naam(order.klantcode or "")

    regels = []
    for b in sorted(order.boringen, key=lambda b: b.volgnummer):
        type_label = {"B": "Gestuurde boring", "N": "Nano boring",
                      "Z": "Boogzinker", "C": "Calculatie"}.get(b.type, b.type)

        lengte = ""
        if b.trace_punten:
            from app.geo.profiel import trace_totale_afstand
            coords = [(p.RD_x, p.RD_y) for p in b.trace_punten
                      if getattr(p, 'variant', 0) == 0]
            if len(coords) >= 2:
                lengte = f"{trace_totale_afstand(coords):.1f}m"

        regels.append({
            "omschrijving": f"{type_label} {order.ordernummer}-{b.volgnummer:02d}"
                           f"{' — ' + order.locatie if order.locatie else ''}"
                           f"{' (' + lengte + ')' if lengte else ''}",
            "aantal": 1,
            "eenheid": "stuk",
            "prijs": "",
        })

    if any(b.type == "B" for b in order.boringen):
        regels.append({
            "omschrijving": f"Werkplan {order.ordernummer} — {order.locatie or ''}",
            "aantal": 1,
            "eenheid": "stuk",
            "prijs": "",
        })

    factuurnummer = f"F-{order.ordernummer}" if order.ordernummer else ""
    from datetime import date
    datum_vandaag = date.today().strftime("%d-%m-%Y")

    return templates.TemplateResponse(
        "order/factuur.html",
        {
            "request": request,
            "order": order,
            "user": user,
            "klant_naam": klant_naam,
            "regels": regels,
            "factuurnummer": factuurnummer,
            "datum_vandaag": datum_vandaag,
        },
    )
