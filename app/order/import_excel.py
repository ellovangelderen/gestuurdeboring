"""Excel import voor HDD orders — leest 'Vergunning' sheet uit order overview.

Kolommen (rij 2 = headers):
A=Date, B=Order name, C=Client, D=Status, E=Date requested, F=Date of delivery,
G=Type1, H=Amt, I=Type2, J=Amt, K=Permit required, L=Note,
M=KLIC, N=Google Maps, O=PDOK, P=Waterkering, Q=Oppervlaktewater, R=Peil,
S-W=EV1-5, X-AC=Email1-6
"""
from datetime import datetime, timezone, date
from uuid import uuid4

from sqlalchemy.orm import Session

from app.order.models import Order, Boring, EVPartij, EmailContact


# Excel status → app status
STATUS_MAP = {
    "Order received": "order_received",
    "In progress": "in_progress",
    "Delivered": "delivered",
    "Waiting for approval": "waiting_for_approval",
    "Done": "done",
    "Cancelled": "cancelled",
}

# Vergunning mapping
VERGUNNING_MAP = {
    "-": "-",
    "P": "P",
    "W": "W",
    "R": "R",
    None: "-",
    "": "-",
}


def parse_date(val):
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.replace(tzinfo=timezone.utc)
    if isinstance(val, date):
        return datetime(val.year, val.month, val.day, tzinfo=timezone.utc)
    for fmt in ["%Y-%m-%d", "%d-%m-%Y"]:
        try:
            return datetime.strptime(str(val).strip(), fmt).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            pass
    return None


def import_vergunning_sheet(db: Session, ws, workspace_id: str = "gbt-workspace-001") -> dict:
    """Importeer de 'Vergunning' sheet.

    Args:
        db: SQLAlchemy session
        ws: openpyxl worksheet
        workspace_id: workspace voor alle orders

    Returns:
        dict met stats: orders, boringen, overgeslagen, fouten
    """
    stats = {"orders": 0, "boringen": 0, "overgeslagen": 0, "fouten": 0}

    # Rij 2 = headers, data begint bij rij 3
    for row_idx in range(3, ws.max_row + 1):
        try:
            order_name = ws.cell(row=row_idx, column=2).value
            if not order_name or str(order_name).strip() == "":
                continue

            order_name = str(order_name).strip()

            # Check of order al bestaat
            bestaand = db.query(Order).filter(Order.ordernummer == order_name).first()
            if bestaand:
                stats["overgeslagen"] += 1
                continue

            datum = parse_date(ws.cell(row=row_idx, column=1).value)
            klantcode = str(ws.cell(row=row_idx, column=3).value or "").strip()
            status_raw = str(ws.cell(row=row_idx, column=4).value or "Order received").strip()
            deadline = parse_date(ws.cell(row=row_idx, column=5).value)
            geleverd_op = parse_date(ws.cell(row=row_idx, column=6).value)
            type1 = str(ws.cell(row=row_idx, column=7).value or "").strip()
            amt1 = ws.cell(row=row_idx, column=8).value
            type2 = str(ws.cell(row=row_idx, column=9).value or "").strip()
            amt2 = ws.cell(row=row_idx, column=10).value
            vergunning = str(ws.cell(row=row_idx, column=11).value or "-").strip()
            notitie = ws.cell(row=row_idx, column=12).value
            locatie = str(ws.cell(row=row_idx, column=14).value or "").strip()  # Google Maps kolom = adres

            # URLs
            pdok_url = ws.cell(row=row_idx, column=15).value
            waterkering_url = ws.cell(row=row_idx, column=16).value
            oppervlaktewater_url = ws.cell(row=row_idx, column=17).value
            peil_url = ws.cell(row=row_idx, column=18).value

            # EV partijen (kolom S-W = 19-23)
            ev_namen = []
            for col in range(19, 24):
                val = ws.cell(row=row_idx, column=col).value
                if val and str(val).strip():
                    ev_namen.append(str(val).strip())

            # Email contacten (kolom X-AC = 24-29)
            email_namen = []
            for col in range(24, 30):
                val = ws.cell(row=row_idx, column=col).value
                if val and str(val).strip():
                    email_namen.append(str(val).strip())

            # Status mapping
            status = STATUS_MAP.get(status_raw, "order_received")

            # Maak order aan
            order = Order(
                id=str(uuid4()),
                workspace_id=workspace_id,
                ordernummer=order_name,
                locatie=locatie or None,
                klantcode=klantcode,
                opdrachtgever=klantcode,
                status=status,
                ontvangen_op=datum or datetime.now(timezone.utc),
                deadline=deadline,
                geleverd_op=geleverd_op,
                vergunning=VERGUNNING_MAP.get(vergunning, "-"),
                notitie=str(notitie) if notitie else None,
                google_maps_url=locatie if locatie else None,
                pdok_url=str(pdok_url) if pdok_url else None,
                waterkering_url=str(waterkering_url) if waterkering_url else None,
                oppervlaktewater_url=str(oppervlaktewater_url) if oppervlaktewater_url else None,
                peil_url=str(peil_url) if peil_url else None,
            )
            db.add(order)
            db.flush()
            stats["orders"] += 1

            # Boringen aanmaken op basis van Type1/Amt1 en Type2/Amt2
            boring_nr = 1
            for btype, bamt in [(type1, amt1), (type2, amt2)]:
                if not btype or btype == "":
                    continue
                count = int(bamt) if bamt else 1
                for _ in range(count):
                    boring = Boring(
                        id=str(uuid4()),
                        order_id=order.id,
                        volgnummer=boring_nr,
                        type=btype,
                        naam=f"{btype}{boring_nr}",
                        status="concept",
                    )
                    db.add(boring)
                    stats["boringen"] += 1
                    boring_nr += 1

            # EV partijen
            for idx, naam in enumerate(ev_namen):
                db.add(EVPartij(
                    id=str(uuid4()),
                    order_id=order.id,
                    naam=naam,
                    volgorde=idx + 1,
                ))

            # Email contacten
            for idx, naam in enumerate(email_namen):
                db.add(EmailContact(
                    id=str(uuid4()),
                    order_id=order.id,
                    naam=naam,
                    volgorde=idx + 1,
                ))

            if stats["orders"] % 50 == 0:
                db.commit()

        except Exception as e:
            stats["fouten"] += 1
            continue

    db.commit()
    return stats
