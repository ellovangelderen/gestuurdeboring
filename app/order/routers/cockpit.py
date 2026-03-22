"""Cockpit: orderlijst, CSV export, statusmail."""
import csv
import io
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.requests import Request
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.dependencies import get_workspace_id
from app.order.helpers import _ACTIEVE_STATUSSEN, _STATUS_MAP, templates
from app.order.klantcodes import get_akkoord_contact, get_klant_naam
from app.order.models import Order

router = APIRouter()


def _query_orders(
    db: Session,
    workspace_id: str,
    *,
    filter: str = "alles",
    zoek: str = "",
    sorteer: str = "deadline",
    richting: str = "asc",
    user: str = "",
) -> list:
    """Bouw een gefilterde, gesorteerde orderlijst voor de cockpit."""
    q = db.query(Order).filter_by(workspace_id=workspace_id)

    if filter == "actief":
        q = q.filter(Order.status.in_(_ACTIEVE_STATUSSEN))
    elif filter == "wacht_akkoord":
        q = q.filter(Order.status == "waiting_for_approval")
    elif filter == "geleverd":
        q = q.filter(Order.status.in_({"delivered", "done"}))
    elif filter == "mijn":
        q = q.filter(Order.tekenaar == user)

    if zoek:
        like = f"%{zoek}%"
        q = q.filter(
            (Order.ordernummer.ilike(like))
            | (Order.locatie.ilike(like))
            | (Order.klantcode.ilike(like))
            | (Order.opdrachtgever.ilike(like))
        )

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


def _compute_stats(orders: list) -> dict:
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


# ── Statusmail helpers ────────────────────────────────────────────────────

_STATUSMAIL_STATUSSEN = {"order_received", "in_progress", "waiting_for_approval", "delivered"}


def _genereer_statusmail_concepten(orders: list) -> list:
    """Groepeer orders per klant en genereer conceptmail-teksten."""
    klant_orders = defaultdict(list)
    for o in orders:
        if o.status in _STATUSMAIL_STATUSSEN:
            klant = o.klantcode or "Onbekend"
            klant_orders[klant].append(o)

    concepten = []
    for klant, order_lijst in sorted(klant_orders.items()):
        klant_naam = get_klant_naam(klant)
        contact = get_akkoord_contact(klant)

        wacht = [o for o in order_lijst if o.status == "waiting_for_approval"]
        geleverd = [o for o in order_lijst if o.status == "delivered"]
        in_uitvoering = [o for o in order_lijst if o.status == "in_progress"]
        ontvangen = [o for o in order_lijst if o.status == "order_received"]

        aanhef = contact or klant_naam
        onderwerp = "Statusoverzicht openstaande orders — GestuurdeBoringTekening.nl"

        regels = []
        regels.append(f"Hallo {aanhef},")
        regels.append("")
        regels.append("Hierbij een overzicht van de openstaande orders:")
        regels.append("")

        if wacht:
            regels.append("Klaar voor akkoord:")
            for o in wacht:
                loc = f" — {o.locatie}" if o.locatie else ""
                regels.append(f"  - {o.ordernummer}{loc}")
            regels.append("")

        if geleverd:
            regels.append("Geleverd, bevestiging ontvangen?")
            for o in geleverd:
                loc = f" — {o.locatie}" if o.locatie else ""
                datum = f" (geleverd {o.geleverd_op.strftime('%d-%m-%Y')})" if o.geleverd_op else ""
                regels.append(f"  - {o.ordernummer}{loc}{datum}")
            regels.append("")

        if in_uitvoering:
            regels.append("In uitvoering:")
            for o in in_uitvoering:
                loc = f" — {o.locatie}" if o.locatie else ""
                regels.append(f"  - {o.ordernummer}{loc}")
            regels.append("")

        if ontvangen:
            regels.append("Ontvangen, wordt opgepakt:")
            for o in ontvangen:
                loc = f" — {o.locatie}" if o.locatie else ""
                regels.append(f"  - {o.ordernummer}{loc}")
            regels.append("")

        regels.append("Laat gerust weten als er vragen zijn.")
        regels.append("")
        regels.append("Met vriendelijke groet,")
        regels.append("")
        regels.append("Martien Luijben")
        regels.append("GestuurdeBoringTekening.nl")

        concepten.append({
            "klantcode": klant,
            "klant_naam": klant_naam,
            "contact": contact,
            "onderwerp": onderwerp,
            "wacht_akkoord": wacht,
            "geleverd": geleverd,
            "in_uitvoering": in_uitvoering,
            "ontvangen": ontvangen,
            "totaal": len(order_lijst),
            "mailtekst": "\n".join(regels),
        })

    return concepten


# ── Routes ────────────────────────────────────────────────────────────────

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
    alle_orders = db.query(Order).filter_by(workspace_id=workspace_id).all()
    stats = _compute_stats(alle_orders)
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
    output.write("\ufeff")
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


@router.get("/statusmail", response_class=HTMLResponse)
def statusmail_overzicht(
    request: Request,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    workspace_id = get_workspace_id(user)
    orders = db.query(Order).filter_by(workspace_id=workspace_id).all()
    concepten = _genereer_statusmail_concepten(orders)

    return templates.TemplateResponse(
        "order/statusmail.html",
        {
            "request": request,
            "concepten": concepten,
            "user": user,
            "totaal_klanten": len(concepten),
            "totaal_orders": sum(c["totaal"] for c in concepten),
        },
    )
