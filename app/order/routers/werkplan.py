"""Werkplan afbeeldingen: upload + verwijder."""
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.dependencies import fetch_order, fetch_boring
from app.order.helpers import MAX_IMAGE_SIZE, UPLOAD_DIR
from app.order.models import WerkplanAfbeelding

router = APIRouter()

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

    content = await afbeelding.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail=f"Afbeelding te groot (max {MAX_IMAGE_SIZE // 1024 // 1024}MB)")

    dest_dir = UPLOAD_DIR / "werkplan" / boring.id
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = Path(afbeelding.filename).name
    dest_path = dest_dir / f"{categorie}_{safe_filename}"

    with open(dest_path, "wb") as f:
        f.write(content)

    bestaande = (
        db.query(WerkplanAfbeelding)
        .filter_by(boring_id=boring.id, categorie=categorie)
        .all()
    )
    for b in bestaande:
        db.delete(b)
    db.flush()

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
        f"/orders/{order_id}/boringen/{volgnr}",
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
        try:
            Path(afb.bestandspad).unlink(missing_ok=True)
        except Exception:
            pass
        db.delete(afb)
        db.commit()

    return RedirectResponse(
        f"/orders/{order_id}/boringen/{volgnr}",
        status_code=303,
    )
