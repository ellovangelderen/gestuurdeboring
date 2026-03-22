"""Brondata: maaiveld, KLIC, doorsneden, intrekkracht, sonderingen, sleufloze, GWSW."""
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.dependencies import fetch_order, fetch_boring
from app.order.helpers import MAX_KLIC_SIZE, UPLOAD_DIR, _f, templates
from app.order.models import (
    Berekening, Doorsnede, KLICLeiding, KLICUpload, MaaiveldOverride,
)
from app.geo.ahn5 import haal_maaiveld_op

router = APIRouter()


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

    klic_samenvatting = []
    diepte_waarschuwing = False
    ev_leidingen = []
    laatste_upload = None
    if order.klic_uploads:
        laatste_upload = sorted(order.klic_uploads, key=lambda u: u.upload_datum)[-1]
        if laatste_upload.verwerkt:
            leidingen = (
                db.query(KLICLeiding)
                .filter_by(klic_upload_id=laatste_upload.id)
                .all()
            )
            agg = {}
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
    """Haal maaiveld op via AHN5 WCS voor intree- en uittree-punt."""
    fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)

    intree = next((p for p in boring.trace_punten if p.type == "intree"), None)
    uittree = next((p for p in boring.trace_punten if p.type == "uittree"), None)

    if intree is None and uittree is None:
        return JSONResponse({
            "status": "fout",
            "melding": "Geen intree- of uittree-punt gevonden — sla eerst het tracé op",
        })

    mv_in = None
    mv_uit = None

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
    response = {
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

    content = await klic_zip.read()
    if len(content) > MAX_KLIC_SIZE:
        raise HTTPException(status_code=413, detail=f"Bestand te groot (max {MAX_KLIC_SIZE // 1024 // 1024}MB)")

    dest_dir = UPLOAD_DIR / order_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = Path(klic_zip.filename).name

    suffix = Path(safe_filename).suffix.lower()
    if suffix not in (".zip", ".xml", ".gml"):
        raise HTTPException(status_code=400, detail="Alleen .zip, .xml of .gml bestanden toegestaan")
    if suffix == ".zip" and not content[:2] == b"PK":
        raise HTTPException(status_code=400, detail="Bestand is geen geldig ZIP-bestand")
    if suffix in (".xml", ".gml") and b"<?xml" not in content[:100] and b"<gml:" not in content[:200]:
        raise HTTPException(status_code=400, detail="Bestand is geen geldig XML/GML-bestand")

    dest_path = dest_dir / safe_filename

    with open(dest_path, "wb") as f:
        f.write(content)

    upload = KLICUpload(
        order_id=order_id,
        bestandsnaam=safe_filename,
        bestandspad=str(dest_path),
        verwerkt=False,
    )
    db.add(upload)
    db.commit()

    from app.geo.klic_parser import verwerk_klic_bestand
    verwerk_klic_bestand(str(dest_path), order_id, upload.id, db)

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


# ── Dinoloket sonderingen ─────────────────────────────────────────────────

@router.get("/{order_id}/boringen/{volgnr}/sonderingen", response_class=HTMLResponse)
def sonderingen_pagina(
    request: Request,
    order_id: str,
    volgnr: int,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Dinoloket sonderingen: links naar BRO/Dinoloket + uploadoptie."""
    order = fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)

    intree = next((p for p in boring.trace_punten
                   if getattr(p, 'variant', 0) == 0 and p.type == "intree"), None)
    uittree = next((p for p in boring.trace_punten
                    if getattr(p, 'variant', 0) == 0 and p.type == "uittree"), None)

    links = []
    if intree:
        from app.geo.coords import rd_to_wgs84
        lat, lon = rd_to_wgs84(intree.RD_x, intree.RD_y)

        links.append({
            "naam": "DINOloket",
            "omschrijving": "Sonderingen, boringen, grondwatermetingen in de buurt van het tracé",
            "url": f"https://www.dinoloket.nl/ondergrondgegevens?coordinates=({lon:.4f},{lat:.4f})&zoom=15",
        })
        links.append({
            "naam": "BRO Bodemkundige boormonsterbeschrijving",
            "omschrijving": "Basisregistratie Ondergrond — geotechnische gegevens",
            "url": f"https://www.broloket.nl/ondergrondgegevens?locatie={lat:.6f},{lon:.6f}",
        })
        links.append({
            "naam": "PDOK BRO Viewer",
            "omschrijving": "Kaart met alle BRO-objecten (sonderingen, boringen)",
            "url": "https://basisregistratieondergrond.nl/inhoud-bro/registratieobjecten/bodem-grondonderzoek/geotechnisch-sondeeronderzoek-cpt/",
        })

    ref_sonderingen = []
    if intree and uittree:
        ref_sonderingen = [
            {"naam": "CPT000000026582 (intrede)", "rd_x": 103851, "rd_y": 489230, "nap": "+4.28"},
            {"naam": "CPT000000026578 (uittrede)", "rd_x": 103923, "rd_y": 489219, "nap": "+4.31"},
        ]

    return templates.TemplateResponse(
        "order/sonderingen.html",
        {
            "request": request,
            "order": order,
            "boring": boring,
            "user": user,
            "links": links,
            "intree": intree,
            "ref_sonderingen": ref_sonderingen,
        },
    )


# ── Sleufloze leidingen ───────────────────────────────────────────────────

@router.get("/{order_id}/boringen/{volgnr}/sleufloze", response_class=HTMLResponse)
def sleufloze_leidingen_pagina(
    request: Request,
    order_id: str,
    volgnr: int,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Overzicht sleufloze leidingen uit KLIC data."""
    order = fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)

    sleufloze = []
    mogelijk = []
    totaal_leidingen = 0

    laatste_upload = None
    if order.klic_uploads:
        uploads = [u for u in order.klic_uploads if u.verwerkt]
        if uploads:
            laatste_upload = sorted(uploads, key=lambda u: u.upload_datum)[-1]

    if laatste_upload:
        leidingen = (
            db.query(KLICLeiding)
            .filter_by(klic_upload_id=laatste_upload.id)
            .all()
        )
        totaal_leidingen = len(leidingen)
        for l in leidingen:
            if l.sleufloze_techniek:
                sleufloze.append(l)
            elif l.mogelijk_sleufloze:
                mogelijk.append(l)

    return templates.TemplateResponse(
        "order/sleufloze.html",
        {
            "request": request,
            "order": order,
            "boring": boring,
            "user": user,
            "sleufloze": sleufloze,
            "mogelijk": mogelijk,
            "totaal_leidingen": totaal_leidingen,
            "heeft_klic": laatste_upload is not None,
        },
    )


# ── GWSW riool BOB ────────────────────────────────────────────────────────

@router.get("/{order_id}/boringen/{volgnr}/gwsw", response_class=HTMLResponse)
def gwsw_riool_pagina(
    request: Request,
    order_id: str,
    volgnr: int,
    user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """GWSW riool BOB data + gemeente-mail generator."""
    from app.geo.gwsw import haal_riooldata_op

    order = fetch_order(order_id, db)
    boring = fetch_boring(order_id, volgnr, db)

    fout = None
    leidingen = []
    gemeente_mail = None

    intree = next((p for p in boring.trace_punten if p.type == "intree"), None)
    if not intree:
        fout = "Geen intree-punt — sla eerst het tracé op."
    else:
        leidingen = haal_riooldata_op(intree.RD_x, intree.RD_y, buffer_m=100.0)

        met_bob = [l for l in leidingen if l.heeft_bob]

        if not leidingen or (leidingen and not met_bob):
            locatie = order.locatie or "de projectlocatie"
            ordernr = order.ordernummer or ""
            gemeente_mail = {
                "onderwerp": f"Verzoek BOB-gegevens riool — {ordernr} {locatie}",
                "tekst": (
                    f"Geachte heer/mevrouw,\n\n"
                    f"Voor het ontwerp van een gestuurde boring op de volgende locatie hebben wij "
                    f"de BOB-gegevens (binnenonderkant buis) van het rioolstelsel nodig:\n\n"
                    f"  Locatie: {locatie}\n"
                    f"  Ordernummer: {ordernr}\n"
                    f"  RD-coördinaten: X={intree.RD_x:.2f}  Y={intree.RD_y:.2f}\n\n"
                    f"Het betreft het riool in de directe omgeving van bovengenoemde coördinaten "
                    f"(straal ca. 100 meter).\n\n"
                    f"Kunt u ons de BOB-waarden en het leidingmateriaal/diameter doorgeven?\n\n"
                    f"Bij voorbaat dank.\n\n"
                    f"Met vriendelijke groet,\n\n"
                    f"Martien Luijben\n"
                    f"GestuurdeBoringTekening.nl"
                ),
            }

    gemeente_kaart_url = None
    if gemeente_mail and intree:
        try:
            from app.documents.werkplan_generator import _generate_werkplan_kaart
            kaart_path = _generate_werkplan_kaart(boring)
            if kaart_path:
                gemeente_kaart_url = f"/static/tmp/{Path(kaart_path).name}"
                static_tmp = Path("static/tmp")
                static_tmp.mkdir(parents=True, exist_ok=True)
                import shutil as _sh
                _sh.copy2(kaart_path, static_tmp / Path(kaart_path).name)
        except Exception:
            pass

    return templates.TemplateResponse(
        "order/gwsw.html",
        {
            "request": request,
            "order": order,
            "boring": boring,
            "user": user,
            "fout": fout,
            "leidingen": leidingen,
            "met_bob": [l for l in leidingen if l.heeft_bob],
            "zonder_bob": [l for l in leidingen if not l.heeft_bob],
            "gemeente_mail": gemeente_mail,
            "gemeente_kaart_url": gemeente_kaart_url,
        },
    )
