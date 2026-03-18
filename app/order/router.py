import csv
import io
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.dependencies import fetch_order, fetch_boring, get_workspace_id
from app.geo.ahn5 import haal_maaiveld_op
from app.geo.pdok_urls import genereer_pdok_url
from app.geo.waterschap import bepaal_waterschap, waterschap_kaart_url
from app.order.klantcodes import (
    KLANTCODES, ORDER_STATUSES, BORING_TYPES, VERGUNNING_TYPES,
    get_akkoord_contact, get_klant_naam,
)
from app.order.models import (
    Berekening,
    Boring,
    Doorsnede,
    KLICLeiding,
    KLICUpload,
    MaaiveldOverride,
    Order,
    TracePunt,
    WerkplanAfbeelding,
)

router = APIRouter(prefix="/orders")
templates = Jinja2Templates(directory="app/templates")

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def _f(v: str) -> float | None:
    """Converteer leeg Form string-veld naar None (optionele float)."""
    return float(v) if v and v.strip() else None


def _i(v: str) -> int | None:
    """Converteer leeg Form string-veld naar None (optionele int)."""
    return int(v) if v and v.strip() else None


# ── Cockpit helpers ────────────────────────────────────────────────────────

_STATUS_MAP = {s["value"]: s["label"] for s in ORDER_STATUSES}

# Statussen die als "actief" gelden (niet geleverd/afgerond/geannuleerd)
_ACTIEVE_STATUSSEN = {"order_received", "in_progress", "waiting_for_approval"}


def _query_orders(
    db: Session,
    workspace_id: str,
    *,
    filter: str = "alles",
    zoek: str = "",
    sorteer: str = "deadline",
    richting: str = "asc",
    user: str = "",
) -> list[Order]:
    """Bouw een gefilterde, gesorteerde orderlijst voor de cockpit."""
    q = db.query(Order).filter_by(workspace_id=workspace_id)

    # -- filter --
    if filter == "actief":
        q = q.filter(Order.status.in_(_ACTIEVE_STATUSSEN))
    elif filter == "wacht_akkoord":
        q = q.filter(Order.status == "waiting_for_approval")
    elif filter == "geleverd":
        q = q.filter(Order.status.in_({"delivered", "done"}))
    elif filter == "mijn":
        q = q.filter(Order.tekenaar == user)
    # "alles" → geen extra filter

    # -- zoek --
    if zoek:
        like = f"%{zoek}%"
        q = q.filter(
            (Order.ordernummer.ilike(like))
            | (Order.locatie.ilike(like))
            | (Order.klantcode.ilike(like))
            | (Order.opdrachtgever.ilike(like))
        )

    # -- sorteer --
    col_map = {
        "deadline": Order.deadline,
        "datum": Order.ontvangen_op,
        "klant": Order.klantcode,
        "status": Order.status,
    }
    col = col_map.get(sorteer, Order.deadline)
    if richting == "desc":
        q = q.order_by(col.desc().nullslast(), Order.ontvangen_op.desc())
    else:
        q = q.order_by(col.asc().nullslast(), Order.ontvangen_op.desc())

    return q.all()


def _compute_stats(orders: list[Order]) -> dict:
    """Bereken cockpit statistieken uit een lijst orders."""
    now_aware = datetime.now(timezone.utc)
    now_naive = now_aware.replace(tzinfo=None)
    totaal = len(orders)
    over_deadline = 0
    urgent = 0
    in_uitvoering = 0
    wacht_akkoord = 0

    for o in orders:
        if o.deadline:
            # Vergelijk met juiste variant (naive of aware)
            now = now_aware if o.deadline.tzinfo else now_naive
        else:
            now = now_aware
        if o.deadline and o.deadline < now and o.status in _ACTIEVE_STATUSSEN:
            over_deadline += 1
        if o.prio and o.status in _ACTIEVE_STATUSSEN:
            urgent += 1
        if o.status == "in_progress":
            in_uitvoering += 1
        if o.status == "waiting_for_approval":
            wacht_akkoord += 1

    return {
        "totaal": totaal,
        "over_deadline": over_deadline,
        "urgent": urgent,
        "in_uitvoering": in_uitvoering,
        "wacht_akkoord": wacht_akkoord,
    }


# ── Cockpit (orderlijst) ──────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def order_lijst(
    request: Request,
    filter: str = Query("alles"),
    zoek: str = Query(""),
    sorteer: str = Query("deadline"),
    richting: str = Query("asc"),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workspace_id = get_workspace_id(user)

    # Alle orders voor stats (ongeacht filter)
    alle_orders = db.query(Order).filter_by(workspace_id=workspace_id).all()
    stats = _compute_stats(alle_orders)

    # Gefilterde orders voor tabel
    orders = _query_orders(
        db, workspace_id,
        filter=filter, zoek=zoek, sorteer=sorteer, richting=richting, user=user,
    )

    return templates.TemplateResponse(
        "order/list.html",
        {
            "request": request,
            "orders": orders,
            "user": user,
            "statuses": _STATUS_MAP,
            "stats": stats,
            "filter": filter,
            "zoek": zoek,
            "sorteer": sorteer,
            "richting": richting,
            "now": datetime.now(timezone.utc).replace(tzinfo=None),
        },
    )


# ── CSV export ─────────────────────────────────────────────────────────────

@router.get("/export/csv")
def export_csv(
    filter: str = Query("alles"),
    zoek: str = Query(""),
    sorteer: str = Query("deadline"),
    richting: str = Query("asc"),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workspace_id = get_workspace_id(user)
    orders = _query_orders(
        db, workspace_id,
        filter=filter, zoek=zoek, sorteer=sorteer, richting=richting, user=user,
    )

    output = io.StringIO()
    output.write("\ufeff")  # UTF-8 BOM voor Excel
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "Ordernummer", "Locatie", "Klant", "Boringen", "Status",
        "Deadline", "Tekenaar", "Prio", "EV-partijen",
    ])
    for o in orders:
        boring_types = " ".join(b.type for b in sorted(o.boringen, key=lambda b: b.volgnummer))
        ev = ", ".join(ep.naam for ep in o.ev_partijen) if o.ev_partijen else ""
        writer.writerow([
            o.ordernummer,
            o.locatie or "",
            o.klantcode or "",
            boring_types,
            _STATUS_MAP.get(o.status, o.status),
            o.deadline.strftime("%d-%m-%Y") if o.deadline else "",
            o.tekenaar or "",
            "Ja" if o.prio else "Nee",
            ev,
        ])

    csv_bytes = output.getvalue().encode("utf-8")
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=orders_export.csv"},
    )


# ── Order aanmaken ──────────────────────────────────────────────────────────

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

    # Bepaal akkoord_contact: formulier-waarde, of default uit klantcodes
    contact = akkoord_contact.strip() if akkoord_contact else ""
    if not contact and klantcode:
        contact = get_akkoord_contact(klantcode)

    # Parse deadline date string
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
    db.flush()  # order.id beschikbaar

    # Boringen aanmaken
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
    vergunning: str = Form("-"),
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
    order.vergunning = vergunning
    order.tekenaar = tekenaar.strip() or "martien"
    order.akkoord_contact = akkoord_contact.strip() or None
    # Parse deadline
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


# ── Boring detail ───────────────────────────────────────────────────────────

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
    return templates.TemplateResponse(
        "order/boring_detail.html",
        {
            "request": request,
            "order": order,
            "boring": boring,
            "user": user,
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
    db.commit()
    return RedirectResponse(f"/orders/{order_id}/boringen/{volgnr}", status_code=303)


# ── Trace ───────────────────────────────────────────────────────────────────

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
            lat, lon = rd_to_wgs84(p.RD_x, p.RD_y)
            punten_wgs84.append({"label": p.label, "lat": lat, "lon": lon})
    except Exception:
        pass
    return templates.TemplateResponse(
        "order/trace.html",
        {
            "request": request,
            "order": order,
            "boring": boring,
            "punten_wgs84": punten_wgs84,
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

    for punt in boring.trace_punten:
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
        # Waterschap bepalen (externe call, falen is OK)
        ws_naam = bepaal_waterschap(ix, iy)
        ws_url = waterschap_kaart_url(ws_naam)
        if ws_url:
            order.waterkering_url = ws_url

    db.commit()
    return RedirectResponse(f"/orders/{order_id}/boringen/{volgnr}", status_code=303)


# ── Brondata ────────────────────────────────────────────────────────────────

@router.get("/{order_id}/boringen/{volgnr}/brondata", response_class=HTMLResponse)
def brondata_form(
    request: Request,
    order_id: str,
    volgnr: int,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)

    # KLIC samenvatting (order-level)
    klic_samenvatting: list[dict] = []
    diepte_waarschuwing = False
    ev_leidingen: list[dict] = []
    laatste_upload = None
    if order.klic_uploads:
        laatste_upload = sorted(order.klic_uploads, key=lambda u: u.upload_datum)[-1]
        if laatste_upload.verwerkt:
            leidingen = (
                db.query(KLICLeiding)
                .filter_by(klic_upload_id=laatste_upload.id)
                .all()
            )
            agg: dict[tuple, dict] = {}
            for l in leidingen:
                key = (l.beheerder or "", l.leidingtype or "")
                if key not in agg:
                    agg[key] = {"beheerder": key[0], "leidingtype": key[1],
                                "aantal": 0, "sleufloze": False}
                agg[key]["aantal"] += 1
                if l.sleufloze_techniek:
                    agg[key]["sleufloze"] = True
            klic_samenvatting = sorted(agg.values(), key=lambda r: (r["beheerder"], r["leidingtype"]))

            total = len(leidingen)
            met_diepte = sum(1 for l in leidingen if l.diepte_m is not None)
            diepte_waarschuwing = total > 0 and met_diepte == 0

            # EV-leidingen: uit EVPartij records op de order
            for ep in order.ev_partijen:
                ev_leidingen.append({
                    "beheerder": ep.naam or "",
                    "contactgegevens": "",
                })

    return templates.TemplateResponse(
        "order/brondata.html",
        {
            "request": request,
            "order": order,
            "boring": boring,
            "user": user,
            "klic_samenvatting": klic_samenvatting,
            "diepte_waarschuwing": diepte_waarschuwing,
            "ev_leidingen": ev_leidingen,
            "laatste_upload": laatste_upload,
        },
    )


@router.post("/{order_id}/boringen/{volgnr}/maaiveld")
def maaiveld_opslaan(
    order_id: str,
    volgnr: int,
    MVin_NAP_m: float = Form(...),
    MVuit_NAP_m: float = Form(...),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)
    if boring.maaiveld_override:
        mv = boring.maaiveld_override
        mv.MVin_NAP_m = MVin_NAP_m
        mv.MVuit_NAP_m = MVuit_NAP_m
        mv.bron = "handmatig"
        mv.MVin_bron = "handmatig"
        mv.MVuit_bron = "handmatig"
    else:
        mv = MaaiveldOverride(
            boring_id=boring.id,
            MVin_NAP_m=MVin_NAP_m,
            MVuit_NAP_m=MVuit_NAP_m,
            bron="handmatig",
            MVin_bron="handmatig",
            MVuit_bron="handmatig",
        )
        db.add(mv)
    db.commit()
    return RedirectResponse(f"/orders/{order_id}/boringen/{volgnr}/brondata", status_code=303)


@router.post("/{order_id}/boringen/{volgnr}/maaiveld/ahn5")
def maaiveld_ahn5_ophalen(
    order_id: str,
    volgnr: int,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Haal maaiveld op via AHN5 WCS voor intree- en uittree-punt van deze boring."""
    fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)

    intree = next((p for p in boring.trace_punten if p.type == "intree"), None)
    uittree = next((p for p in boring.trace_punten if p.type == "uittree"), None)

    if intree is None and uittree is None:
        return JSONResponse({
            "status": "fout",
            "melding": "Geen intree- of uittree-punt gevonden — sla eerst het tracé op",
        })

    mv_in: float | None = None
    mv_uit: float | None = None

    if intree is not None:
        mv_in = haal_maaiveld_op(intree.RD_x, intree.RD_y)
    if uittree is not None:
        mv_uit = haal_maaiveld_op(uittree.RD_x, uittree.RD_y)

    if mv_in is None and mv_uit is None:
        return JSONResponse({
            "status": "fout",
            "melding": "AHN5 service niet bereikbaar — vul handmatig in",
        })

    in_bron = "ahn5" if mv_in is not None else "niet_beschikbaar"
    uit_bron = "ahn5" if mv_uit is not None else "niet_beschikbaar"

    mv = boring.maaiveld_override
    if mv is None:
        mv = MaaiveldOverride(boring_id=boring.id)
        db.add(mv)

    if mv_in is not None:
        mv.MVin_NAP_m = mv_in
        mv.MVin_ahn5_m = mv_in
    if mv_uit is not None:
        mv.MVuit_NAP_m = mv_uit
        mv.MVuit_ahn5_m = mv_uit

    mv.MVin_bron = in_bron
    mv.MVuit_bron = uit_bron
    mv.bron = "ahn5"
    mv.override_datum = datetime.now(timezone.utc)
    db.commit()

    status = "ok" if (mv_in is not None and mv_uit is not None) else "partial"
    response: dict = {
        "status": status,
        "MVin_NAP_m": mv_in,
        "MVuit_NAP_m": mv_uit,
        "MVin_bron": in_bron,
        "MVuit_bron": uit_bron,
    }
    if status == "partial":
        ontbrekend = []
        if mv_in is None:
            ontbrekend.append("intree")
        if mv_uit is None:
            ontbrekend.append("uittree")
        response["melding"] = f"AHN5 niet beschikbaar voor: {', '.join(ontbrekend)}"

    return JSONResponse(response)


@router.post("/{order_id}/klic")
async def klic_upload(
    order_id: str,
    klic_zip: UploadFile = File(...),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = fetch_order(order_id, db)
    dest_dir = UPLOAD_DIR / order_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = Path(klic_zip.filename).name

    # Accepteer .zip, .xml en .gml bestanden
    suffix = Path(safe_filename).suffix.lower()
    if suffix not in (".zip", ".xml", ".gml"):
        raise HTTPException(status_code=400, detail="Alleen .zip, .xml of .gml bestanden toegestaan")

    dest_path = dest_dir / safe_filename

    with open(dest_path, "wb") as f:
        shutil.copyfileobj(klic_zip.file, f)

    upload = KLICUpload(
        order_id=order_id,
        bestandsnaam=safe_filename,
        bestandspad=str(dest_path),
        verwerkt=False,
    )
    db.add(upload)
    db.commit()

    # Auto-verwerken na upload
    from app.geo.klic_parser import verwerk_klic_bestand
    verwerk_klic_bestand(str(dest_path), order_id, upload.id, db)

    # Redirect terug naar de eerste boring's brondata, of order detail
    boringen = sorted(order.boringen, key=lambda b: b.volgnummer)
    if boringen:
        return RedirectResponse(
            f"/orders/{order_id}/boringen/{boringen[0].volgnummer}/brondata",
            status_code=303,
        )
    return RedirectResponse(f"/orders/{order_id}", status_code=303)


@router.post("/{order_id}/boringen/{volgnr}/doorsneden")
def doorsneden_opslaan(
    order_id: str,
    volgnr: int,
    afstand_list: str = Form(...),
    NAP_list: str = Form(...),
    grondtype_list: str = Form(...),
    GWS_list: str = Form(""),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)

    try:
        afstanden = [float(v.strip()) for v in afstand_list.split(",") if v.strip()]
        naps = [float(v.strip()) for v in NAP_list.split(",") if v.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Ongeldige afstanden of NAP-waarden")

    grondtypen = [v.strip() for v in grondtype_list.split(",") if v.strip()]
    gwssen = [v.strip() for v in GWS_list.split(",")] if GWS_list else [""] * len(afstanden)

    for d in boring.doorsneden:
        db.delete(d)
    db.flush()

    for i, (afstand, nap, grondtype) in enumerate(zip(afstanden, naps, grondtypen)):
        gws_val = gwssen[i] if i < len(gwssen) else ""
        try:
            gws = float(gws_val) if gws_val else None
        except ValueError:
            gws = None
        ds = Doorsnede(
            boring_id=boring.id,
            volgorde=i,
            afstand_m=afstand,
            NAP_m=nap,
            grondtype=grondtype,
            GWS_m=gws,
        )
        db.add(ds)
    db.commit()
    return RedirectResponse(f"/orders/{order_id}/boringen/{volgnr}/brondata", status_code=303)


@router.post("/{order_id}/boringen/{volgnr}/intrekkracht")
def intrekkracht_opslaan(
    order_id: str,
    volgnr: int,
    Ttot_N: float = Form(...),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)
    if boring.berekening:
        boring.berekening.Ttot_N = Ttot_N
        boring.berekening.bron = "sigma_override"
    else:
        b = Berekening(boring_id=boring.id, Ttot_N=Ttot_N, bron="sigma_override")
        db.add(b)
    db.commit()
    return RedirectResponse(f"/orders/{order_id}/boringen/{volgnr}/brondata", status_code=303)


# ── DXF + PDF download per boring ─────────────────────────────────────────

@router.get("/{order_id}/boringen/{volgnr}/dxf")
def download_dxf_boring(
    order_id: str,
    volgnr: int,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.documents.dxf_generator import generate_dxf
    order = fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)
    dxf_bytes = generate_dxf(boring, order, db)
    ordernr = order.ordernummer or order.id[:8]
    filename = f"{ordernr}-{boring.volgnummer:02d}-rev.1.dxf"
    from fastapi.responses import Response as Resp
    return Resp(
        content=dxf_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{order_id}/boringen/{volgnr}/pdf")
def download_pdf_boring(
    order_id: str,
    volgnr: int,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.documents.pdf_generator import generate_pdf
    order = fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)
    pdf_bytes = generate_pdf(boring, order, db=db)
    ordernr = order.ordernummer or order.id[:8]
    filename = f"{ordernr}-{boring.volgnummer:02d}-rev.1.pdf"
    from fastapi.responses import Response as Resp
    return Resp(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── Werkplan afbeeldingen ──────────────────────────────────────────────────

AFBEELDING_CATEGORIEEN = [
    "luchtfoto", "topotijdreis_1", "topotijdreis_2", "topotijdreis_3",
    "klic", "rws", "overig",
]


@router.post("/{order_id}/boringen/{volgnr}/werkplan-afbeelding")
async def werkplan_afbeelding_upload(
    order_id: str,
    volgnr: int,
    categorie: str = Form(...),
    bijschrift: str = Form(""),
    afbeelding: UploadFile = File(...),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload een afbeelding voor het werkplan."""
    fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)

    if categorie not in AFBEELDING_CATEGORIEEN:
        raise HTTPException(status_code=400, detail=f"Ongeldige categorie: {categorie}")

    # Opslaan in uploads/werkplan/<boring_id>/
    dest_dir = UPLOAD_DIR / "werkplan" / boring.id
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = Path(afbeelding.filename).name
    # Prefix met categorie voor uniekheid
    dest_path = dest_dir / f"{categorie}_{safe_filename}"

    with open(dest_path, "wb") as f:
        shutil.copyfileobj(afbeelding.file, f)

    # Verwijder bestaande afbeelding in dezelfde categorie (overschrijven)
    bestaande = (
        db.query(WerkplanAfbeelding)
        .filter_by(boring_id=boring.id, categorie=categorie)
        .all()
    )
    for b in bestaande:
        db.delete(b)
    db.flush()

    # Volgorde bepalen
    volgorde_map = {cat: i for i, cat in enumerate(AFBEELDING_CATEGORIEEN)}

    afb = WerkplanAfbeelding(
        boring_id=boring.id,
        categorie=categorie,
        bestandsnaam=safe_filename,
        bestandspad=str(dest_path),
        bijschrift=bijschrift.strip() or None,
        volgorde=volgorde_map.get(categorie, 99),
    )
    db.add(afb)
    db.commit()

    return RedirectResponse(
        f"/api/v1/orders/{order_id}/boringen/{volgnr}/werkplan",
        status_code=303,
    )


@router.post("/{order_id}/boringen/{volgnr}/werkplan-afbeelding/{afb_id}/delete")
def werkplan_afbeelding_verwijder(
    order_id: str,
    volgnr: int,
    afb_id: str,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Verwijder een werkplan afbeelding."""
    fetch_order(order_id, db)
    fetch_boring(order_id, volgnr, db)

    afb = db.query(WerkplanAfbeelding).filter_by(id=afb_id).first()
    if afb:
        # Bestand verwijderen
        try:
            Path(afb.bestandspad).unlink(missing_ok=True)
        except Exception:
            pass
        db.delete(afb)
        db.commit()

    return RedirectResponse(
        f"/api/v1/orders/{order_id}/boringen/{volgnr}/werkplan",
        status_code=303,
    )
