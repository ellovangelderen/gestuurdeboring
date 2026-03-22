"""Exports: CSV GPS, AutoCAD .scr, DXF, PDF downloads."""
import csv
import io
import math

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.dependencies import fetch_order, fetch_boring

router = APIRouter()


@router.get("/{order_id}/boringen/{volgnr}/csv")
def download_csv_gps(
    order_id: str,
    volgnr: int,
    interval: float = Query(1.0),
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """CSV export van boorlijn punten (per meter of aangepast interval)."""
    from app.geo.profiel import trace_totale_afstand

    order = fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)

    trace = [p for p in boring.trace_punten if getattr(p, 'variant', 0) == 0]
    trace = sorted(trace, key=lambda p: p.volgorde)

    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output, delimiter=";")

    writer.writerow(["# SENSORPUNTEN"])
    writer.writerow(["Label", "RD_X", "RD_Y", "Type"])
    for p in trace:
        writer.writerow([p.label, f"{p.RD_x:.2f}", f"{p.RD_y:.2f}", p.type])
    writer.writerow([])

    writer.writerow([f"# BOORLIJN (elke {interval}m)"])
    writer.writerow(["Afstand_m", "RD_X", "RD_Y"])

    if len(trace) >= 2:
        coords = [(p.RD_x, p.RD_y) for p in trace]
        cumul = 0.0
        writer.writerow([f"{0.0:.2f}", f"{coords[0][0]:.2f}", f"{coords[0][1]:.2f}"])
        for i in range(1, len(coords)):
            x0, y0 = coords[i - 1]
            x1, y1 = coords[i]
            seg_len = math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)
            if seg_len < 0.001:
                continue
            d = interval - (cumul % interval) if cumul > 0 else interval
            while d <= seg_len:
                t = d / seg_len
                sx = x0 + t * (x1 - x0)
                sy = y0 + t * (y1 - y0)
                writer.writerow([f"{cumul + d:.2f}", f"{sx:.2f}", f"{sy:.2f}"])
                d += interval
            cumul += seg_len
        writer.writerow([f"{cumul:.2f}", f"{coords[-1][0]:.2f}", f"{coords[-1][1]:.2f}"])

    ordernr = order.ordernummer or order.id[:8]
    naam = boring.naam or f"HDD{boring.volgnummer}"
    filename = f"{ordernr}-{naam}-GPS.csv"

    csv_bytes = output.getvalue().encode("utf-8")
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{order_id}/boringen/{volgnr}/scr")
def download_autocad_script(
    order_id: str,
    volgnr: int,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Genereer AutoCAD .scr script voor de boorlijn."""
    order = fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)

    trace = [p for p in boring.trace_punten if getattr(p, 'variant', 0) == 0]
    trace = sorted(trace, key=lambda p: p.volgorde)

    lines = []
    lines.append("; AutoCAD script — gegenereerd door HDD Platform")
    lines.append(f"; Order: {order.ordernummer} Boring: {boring.naam or boring.volgnummer}")
    lines.append("")

    if trace:
        lines.append("_LAYER _Set BOORLIJN ")
        lines.append("")

        coords_str = " ".join(f"{p.RD_x:.2f},{p.RD_y:.2f}" for p in trace)
        lines.append(f"_PLINE {coords_str} ")
        lines.append("")

        lines.append("_LAYER _Set ATTRIBUTEN ")
        lines.append("")
        for p in trace:
            if p.label:
                lines.append(f"_TEXT {p.RD_x:.2f},{p.RD_y:.2f} 2.0 0 {p.label}")
                lines.append("")

        intree = next((p for p in trace if p.type == "intree"), None)
        uittree = next((p for p in trace if p.type == "uittree"), None)
        if intree:
            lines.append(f"_INSERT Aboorgat3x1 {intree.RD_x:.2f},{intree.RD_y:.2f} 1 1 0")
            lines.append("")
        if uittree:
            lines.append(f"_INSERT Bboorgat3x1 {uittree.RD_x:.2f},{uittree.RD_y:.2f} 1 1 0")
            lines.append("")

    ordernr = order.ordernummer or order.id[:8]
    naam = boring.naam or f"HDD{boring.volgnummer}"
    filename = f"{ordernr}-{naam}.scr"

    scr_content = "\n".join(lines)
    return StreamingResponse(
        io.BytesIO(scr_content.encode("utf-8")),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
    rev = boring.revisie or 0
    naam = boring.naam or f"HDD{boring.volgnummer}"
    filename = f"{ordernr}-{boring.volgnummer:02d} {naam}-rev.{rev}.dxf"
    from fastapi.responses import Response as Resp
    return Resp(
        content=dxf_bytes,
        media_type="application/dxf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
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
    rev = boring.revisie or 0
    naam = boring.naam or f"HDD{boring.volgnummer}"
    locatie = order.locatie or ""
    filename = f"{ordernr}-{boring.volgnummer:02d} {naam} {locatie}-rev.{rev}.pdf"
    from fastapi.responses import Response as Resp
    return Resp(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
