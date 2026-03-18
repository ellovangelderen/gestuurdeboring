"""KLIC IMKL 2.0 GML parser — backlog items 1 + 3.

Pakt een KLIC ZIP uit, parseert het GML-bestand en slaat leidingen op als
KLICLeiding-records. Alle coordinaten zijn RD New (EPSG:28992) — geen projectie nodig.

Backlog 3 toevoegingen:
- EV-detectie (AanduidingEisVoorzorgsmaatregel)
- Diepte uit tekstvelden (Annotatie / Maatvoering labels)
- Materiaalregel sleufloze techniek
- Formaat B support (enkel GML bestand)
"""
import re
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from lxml import etree
from shapely import from_wkt
from shapely.geometry import LineString, MultiLineString, Polygon
from sqlalchemy.orm import Session

# GML / IMKL XML namespaces
NS_GML = "http://www.opengis.net/gml/3.2"
NS_IMKL = "http://www.geostandaarden.nl/imkl/wibon"
NS_NET = "http://inspire.ec.europa.eu/schemas/net/4.0"
NS_USNET = "http://inspire.ec.europa.eu/schemas/us-net-common/4.0"
NS_USEL = "http://inspire.ec.europa.eu/schemas/us-net-el/4.0"
NS_BASE = "http://inspire.ec.europa.eu/schemas/base/3.3"
NS_XLINK = "http://www.w3.org/1999/xlink"

# IMKL leiding-feature typenamen die worden opgeslagen als KLICLeiding
LEIDING_FEATURE_NAMEN = {
    "Elektriciteitskabel",
    "OlieGasChemicalienPijpleiding",
    "Waterleiding",
    "Rioolleiding",
    "Telecommunicatiekabel",
    "Mantelbuis",
}

# Primaire typen die meetellen voor aantal_leidingen
PRIMAIRE_LEIDING_NAMEN = {
    "Elektriciteitskabel",
    "OlieGasChemicalienPijpleiding",
    "Waterleiding",
    "Rioolleiding",
}

# IMKL thema-URL suffix -> DXF-laag
THEMA_TO_LAYER: dict[str, str] = {
    "laagspanning":     "LAAGSPANNING",
    "middenspanning":   "MIDDENSPANNING",
    "hoogspanning":     "HOOGSPANNING",
    "gasLageDruk":      "LD-GAS",
    "gasHogeDruk":      "LD-GAS",
    "water":            "WATERLEIDING",
    "warmte":           "WATERLEIDING",
    "rioolVrijverval":  "RIOOL-VRIJVERVAL",
    "rioolOnderOverdruk": "RIOOL-VRIJVERVAL",
    "datatransport":    "LAAGSPANNING",
    "overig":           "LAAGSPANNING",
}

# Feature-type naam -> default thema als Utiliteitsnet onbekend is
FEATURETYPE_TO_THEMA: dict[str, str] = {
    "Elektriciteitskabel":         "laagspanning",
    "OlieGasChemicalienPijpleiding": "gasLageDruk",
    "Waterleiding":                "water",
    "Rioolleiding":                "rioolVrijverval",
    "Telecommunicatiekabel":       "datatransport",
    "Mantelbuis":                  "datatransport",
}

# Materialen die op sleufloze techniek wijzen
_SLEUFLOZE_MATERIALEN = {"PE", "HDPE", "PE100", "PE80", "PEX"}
_MOGELIJK_SLEUFLOZE_MATERIALEN = {"staal", "steel"}


def _tag(ns: str, local: str) -> str:
    return f"{{{ns}}}{local}"


def _href_suffix(href: Optional[str]) -> str:
    """Geeft het laatste deel van een xlink:href URL."""
    if not href:
        return ""
    return href.rstrip("/").split("/")[-1]


def _poslist_to_coords(poslist_text: str) -> list[tuple[float, float]]:
    """Zet een GML posList (x y x y ...) om naar (x,y) tuples."""
    vals = poslist_text.split()
    coords = []
    for i in range(0, len(vals) - 1, 2):
        try:
            x = float(vals[i])
            y = float(vals[i + 1])
            coords.append((x, y))
        except ValueError:
            continue
    return coords


def _extract_geometry_wkt(ul_element) -> Optional[str]:
    """Geeft WKT voor de geometrie van een UtilityLink of ExtraDetailinfo element."""
    # GML LineString
    linestring = ul_element.find(f".//{_tag(NS_GML, 'LineString')}")
    if linestring is not None:
        poslist = linestring.find(_tag(NS_GML, "posList"))
        if poslist is not None and poslist.text:
            coords = _poslist_to_coords(poslist.text.strip())
            if len(coords) >= 2:
                return LineString(coords).wkt

    # GML Polygon
    polygon = ul_element.find(f".//{_tag(NS_GML, 'Polygon')}")
    if polygon is not None:
        poslist = polygon.find(f".//{_tag(NS_GML, 'posList')}")
        if poslist is not None and poslist.text:
            coords = _poslist_to_coords(poslist.text.strip())
            if len(coords) >= 3:
                return Polygon(coords).wkt

    return None


def _build_utility_link_index(root) -> dict[str, str]:
    """Bouwt een dict van UtilityLink gml:id -> WKT geometrie."""
    index: dict[str, str] = {}
    for fm in root.iter(_tag(NS_GML, "featureMember")):
        for child in fm:
            if child.tag == _tag(NS_USNET, "UtilityLink"):
                gml_id = child.get(_tag(NS_GML, "id"))
                if gml_id:
                    wkt = _extract_geometry_wkt(child)
                    if wkt:
                        index[gml_id] = wkt
    return index


def _build_network_index(root) -> dict[str, dict]:
    """Bouwt een dict van Utiliteitsnet gml:id -> {thema, bronhouder}."""
    index: dict[str, dict] = {}
    for fm in root.iter(_tag(NS_GML, "featureMember")):
        for child in fm:
            if child.tag == _tag(NS_IMKL, "Utiliteitsnet"):
                gml_id = child.get(_tag(NS_GML, "id"))
                thema_el = child.find(_tag(NS_IMKL, "thema"))
                thema_href = thema_el.get(_tag(NS_XLINK, "href"), "") if thema_el is not None else ""
                thema = _href_suffix(thema_href)
                lokaal = child.find(f".//{_tag(NS_IMKL, 'lokaalID')}")
                bronhouder = lokaal.text.split(".")[0] if lokaal is not None and lokaal.text else ""
                if gml_id:
                    index[gml_id] = {"thema": thema, "bronhouder": bronhouder}
    return index


def _build_beheerder_index(root) -> dict[str, str]:
    """Bouwt een dict van bronhoudercode -> organisatienaam."""
    index: dict[str, str] = {}
    for fm in root.iter(_tag(NS_GML, "featureMember")):
        for child in fm:
            if child.tag == _tag(NS_IMKL, "Beheerder"):
                bcode_el = child.find(_tag(NS_IMKL, "bronhoudercode"))
                naam_el = child.find(f".//{_tag(NS_IMKL, 'naam')}")
                if bcode_el is not None and bcode_el.text:
                    index[bcode_el.text] = naam_el.text if naam_el is not None else bcode_el.text
    return index


def _build_network_pdf_index(root) -> set[str]:
    """Geeft set van network_ids die een profielschets PDF bevatten."""
    netwerken_met_pdf: set[str] = set()
    for fm in root.iter(_tag(NS_GML, "featureMember")):
        for child in fm:
            if child.tag == _tag(NS_IMKL, "ExtraDetailinfo"):
                info_type = child.find(_tag(NS_IMKL, "extraInfoType"))
                in_network = child.find(_tag(NS_IMKL, "inNetwork"))
                bestand = child.find(_tag(NS_IMKL, "bestandLocatie"))
                if info_type is not None and in_network is not None and bestand is not None:
                    type_href = info_type.get(_tag(NS_XLINK, "href"), "")
                    if "profielschets" in type_href and bestand.text:
                        if bestand.text.lower().endswith(".pdf"):
                            net_href = in_network.get(_tag(NS_XLINK, "href"), "")
                            if net_href:
                                netwerken_met_pdf.add(net_href)
    return netwerken_met_pdf


def _get_spanning_thema(feature_element, default_thema: str) -> str:
    """Leest nominalVoltage voor Elektriciteitskabel en verfijnt thema."""
    voltage_el = feature_element.find(_tag(NS_USEL, "nominalVoltage"))
    if voltage_el is not None and voltage_el.text:
        try:
            voltage = float(voltage_el.text)
            if voltage > 50000:
                return "hoogspanning"
            elif voltage > 1000:
                return "middenspanning"
            else:
                return "laagspanning"
        except ValueError:
            pass
    return default_thema


def _build_alle_beheerder_codes(root) -> set[str]:
    """Geeft alle bronhoudercodes uit Beheerder-features terug."""
    codes: set[str] = set()
    for fm in root.iter(_tag(NS_GML, "featureMember")):
        for child in fm:
            if child.tag == _tag(NS_IMKL, "Beheerder"):
                bcode_el = child.find(_tag(NS_IMKL, "bronhoudercode"))
                if bcode_el is not None and bcode_el.text:
                    codes.add(bcode_el.text)
    return codes


# ── Backlog 3: EV-detectie ──────────────────────────────────────────────────

def _build_ev_index(root, beheerder_index: dict[str, str]) -> tuple[dict[str, dict], list[dict], list[dict]]:
    """Parse AanduidingEisVoorzorgsmaatregel en Belanghebbende elementen.

    Returns:
        - ev_network_index: {netwerk_href: {ev_verplicht, contactgegevens}}
        - ev_partijen: [{beheerder, contactgegevens}] voor order-level weergave
        - ev_zone_data: [{geometrie_wkt, netwerk_href, beheerder}] voor EVZone records
    """
    # Stap 1: Verzamel contactgegevens + geometrie uit AanduidingEisVoorzorgsmaatregel
    ev_contacts: dict[str, str] = {}  # netwerk_href -> contactgegevens
    ev_zone_data: list[dict] = []
    for fm in root.iter(_tag(NS_GML, "featureMember")):
        for child in fm:
            if child.tag == _tag(NS_IMKL, "AanduidingEisVoorzorgsmaatregel"):
                in_network = child.find(_tag(NS_IMKL, "inNetwork"))
                if in_network is None:
                    continue
                net_href = in_network.get(_tag(NS_XLINK, "href"), "")
                if not net_href:
                    continue

                contact_el = child.find(f".//{_tag(NS_IMKL, 'contactVoorzorgsmaatregel')}")
                naam = ""
                telefoon = ""
                email = ""
                if contact_el is not None:
                    naam_el = contact_el.find(f".//{_tag(NS_IMKL, 'naam')}")
                    tel_el = contact_el.find(f".//{_tag(NS_IMKL, 'telefoon')}")
                    email_el = contact_el.find(f".//{_tag(NS_IMKL, 'email')}")
                    naam = naam_el.text if naam_el is not None and naam_el.text else ""
                    telefoon = tel_el.text if tel_el is not None and tel_el.text else ""
                    email = email_el.text if email_el is not None and email_el.text else ""

                ev_contacts[net_href] = " | ".join(filter(None, [naam, telefoon, email]))

                # Extraheer geometrie voor EV-zone
                wkt = _extract_geometry_wkt(child)
                if wkt:
                    # Bronhouder code uit netwerk_href
                    bronhouder_code = ""
                    net_id = _href_suffix(net_href)
                    if net_id:
                        parts = net_id.replace("nl.imkl-", "").split(".")
                        if parts:
                            bronhouder_code = parts[0]
                    beheerder_naam = beheerder_index.get(bronhouder_code, bronhouder_code)
                    ev_zone_data.append({
                        "geometrie_wkt": wkt,
                        "netwerk_href": net_href,
                        "beheerder": beheerder_naam,
                    })

    # Stap 2: Verzamel netwerken met EV uit Belanghebbende
    ev_network_index: dict[str, dict] = {}
    ev_partijen: list[dict] = []

    for fm in root.iter(_tag(NS_GML, "featureMember")):
        for child in fm:
            if child.tag == _tag(NS_IMKL, "Belanghebbende"):
                ev_el = child.find(_tag(NS_IMKL, "indicatieEisVoorzorgsmaatregel"))
                if ev_el is None or ev_el.text != "true":
                    continue

                net_el = child.find(_tag(NS_IMKL, "utiliteitsnet"))
                net_href = net_el.get(_tag(NS_XLINK, "href"), "") if net_el is not None else ""

                # Bronhouder code uit het gml:id (bijv. nl.imkl-KL1012._Belanghebbende_...)
                gml_id = child.get(_tag(NS_GML, "id"), "")
                bronhouder_code = ""
                if gml_id:
                    parts = gml_id.replace("nl.imkl-", "").split(".")
                    if parts:
                        bronhouder_code = parts[0]

                beheerder_naam = beheerder_index.get(bronhouder_code, bronhouder_code)
                contactgegevens = ev_contacts.get(net_href, "")

                if net_href:
                    ev_network_index[net_href] = {
                        "ev_verplicht": True,
                        "contactgegevens": contactgegevens,
                    }

                ev_partijen.append({
                    "beheerder": beheerder_naam,
                    "contactgegevens": contactgegevens,
                })

    # Voeg ook EV-netwerken toe die alleen in AanduidingEisVoorzorgsmaatregel staan
    for net_href, contactgegevens in ev_contacts.items():
        if net_href not in ev_network_index:
            ev_network_index[net_href] = {
                "ev_verplicht": True,
                "contactgegevens": contactgegevens,
            }

    return ev_network_index, ev_partijen, ev_zone_data


# ── Backlog 3: Diepte uit tekstvelden ───────────────────────────────────────

# Regex patronen voor diepte extractie uit vrije tekst
_DIEPTE_REGEX_NAP = re.compile(
    r"([+-]?\d+[.,]\d+)\s*m?\s*-?\s*[Nn][Aa][Pp]"
)
_DIEPTE_REGEX_GENERIC = re.compile(
    r"diepte.*?([+-]?\d+[.,]\d+)", re.IGNORECASE
)


def _extract_diepte_uit_tekst(tekst: str) -> tuple[Optional[float], Optional[str]]:
    """Probeer diepte uit vrije tekst te extraheren.

    Returns: (diepte_float, "tekstveld_onzeker") bij match, anders (None, None).
    """
    if not tekst:
        return None, None

    # Probeer NAP-patroon eerst
    match = _DIEPTE_REGEX_NAP.search(tekst)
    if match:
        try:
            val = float(match.group(1).replace(",", "."))
            return val, "tekstveld_onzeker"
        except ValueError:
            pass

    # Probeer generiek diepte-patroon
    match = _DIEPTE_REGEX_GENERIC.search(tekst)
    if match:
        try:
            val = float(match.group(1).replace(",", "."))
            return val, "tekstveld_onzeker"
        except ValueError:
            pass

    return None, None


def _build_label_index(root) -> dict[str, list[str]]:
    """Bouwt index van netwerk_href -> [label teksten] uit Annotatie en Maatvoering elementen."""
    index: dict[str, list[str]] = {}

    for fm in root.iter(_tag(NS_GML, "featureMember")):
        for child in fm:
            tag_local = child.tag.split("}")[-1]
            if tag_local not in ("Annotatie", "Maatvoering"):
                continue

            in_network = child.find(_tag(NS_IMKL, "inNetwork"))
            if in_network is None:
                continue
            net_href = in_network.get(_tag(NS_XLINK, "href"), "")
            if not net_href:
                continue

            label_el = child.find(_tag(NS_IMKL, "label"))
            if label_el is not None and label_el.text:
                if net_href not in index:
                    index[net_href] = []
                index[net_href].append(label_el.text)

    return index


# ── Backlog 3: Materiaalregel sleufloze techniek ────────────────────────────

def _detect_materiaal_sleufloze(feature) -> tuple[bool, bool]:
    """Detecteer sleufloze techniek op basis van buismateriaalType.

    Returns: (sleufloze_techniek, mogelijk_sleufloze)
    """
    mat_el = feature.find(_tag(NS_IMKL, "buismateriaalType"))
    if mat_el is None:
        return False, False

    mat_href = mat_el.get(_tag(NS_XLINK, "href"), "")
    mat_val = _href_suffix(mat_href).upper()

    # Ook check op element text als href leeg is
    if not mat_val and mat_el.text:
        mat_val = mat_el.text.strip().upper()

    if mat_val in _SLEUFLOZE_MATERIALEN:
        return True, False
    if mat_val.lower() in _MOGELIJK_SLEUFLOZE_MATERIALEN:
        return False, True

    return False, False


# ── Hoofdparser ─────────────────────────────────────────────────────────────

def _parse_gml_file(
    xml_data: bytes,
    project_id: str,
    klic_upload_id: str,
    db: Session,
) -> dict:
    """
    Parseert een GML/XML bestand en slaat leidingen op in de database.
    Geeft terug: {count_primair, count_totaal, beheerders_set, alle_beheerders_set, fout}.
    """
    from app.order.models import KLICLeiding

    try:
        root = etree.fromstring(xml_data)
    except etree.XMLSyntaxError as exc:
        return {"count_primair": 0, "count_totaal": 0, "beheerders_set": set(), "fout": str(exc)}

    # Controleer IMKL namespace aanwezig
    nsmap_values = list(root.nsmap.values()) if root.nsmap else []
    if NS_IMKL not in nsmap_values and NS_GML not in nsmap_values:
        return {"count_primair": 0, "count_totaal": 0, "beheerders_set": set(),
                "alle_beheerders_set": set(), "fout": None}

    ul_index = _build_utility_link_index(root)
    network_index = _build_network_index(root)
    beheerder_index = _build_beheerder_index(root)
    network_pdf_set = _build_network_pdf_index(root)
    alle_beheerder_codes = _build_alle_beheerder_codes(root)
    ev_index, ev_partijen, ev_zone_data = _build_ev_index(root, beheerder_index)
    label_index = _build_label_index(root)

    count_primair = 0
    count_totaal = 0
    beheerders: set[str] = set()

    for fm in root.iter(_tag(NS_GML, "featureMember")):
        for feature in fm:
            feature_type = feature.tag.split("}")[-1]
            if feature_type not in LEIDING_FEATURE_NAMEN:
                continue

            gml_id = feature.get(_tag(NS_GML, "id"), "")

            # Bepaal netwerk -> thema + bronhouder
            in_network_el = feature.find(_tag(NS_NET, "inNetwork"))
            network_href = (
                in_network_el.get(_tag(NS_XLINK, "href"), "")
                if in_network_el is not None
                else ""
            )
            net_info = network_index.get(network_href, {})
            thema = net_info.get("thema") or FEATURETYPE_TO_THEMA.get(feature_type, "overig")
            bronhouder_code = net_info.get("bronhouder", "")

            # Verfijn thema voor elektriciteit via spanning
            if feature_type == "Elektriciteitskabel":
                thema = _get_spanning_thema(feature, thema)

            dxf_laag = THEMA_TO_LAYER.get(thema, "LAAGSPANNING")

            # Beheerder naam opzoeken
            beheerder_naam = beheerder_index.get(bronhouder_code, bronhouder_code)
            if bronhouder_code:
                beheerders.add(bronhouder_code)

            # Geometrie ophalen via UtilityLink
            link_el = feature.find(_tag(NS_NET, "link"))
            link_href = link_el.get(_tag(NS_XLINK, "href"), "") if link_el is not None else ""
            geometrie_wkt = ul_index.get(link_href)

            # Sleufloze detectie: Mantelbuis + netwerk heeft profielschets PDF (bestaand)
            is_mantelbuis = feature_type == "Mantelbuis"
            netwerk_heeft_pdf = network_href in network_pdf_set
            sleufloze = is_mantelbuis and netwerk_heeft_pdf

            # Materiaalregel sleufloze techniek (backlog 3)
            mat_sleufloze, mat_mogelijk = _detect_materiaal_sleufloze(feature)
            if mat_sleufloze:
                sleufloze = True

            # PDF URL voor bron_pdf_url (eerste PDF van dit netwerk)
            bron_pdf_url = None
            if sleufloze:
                for fm2 in root.iter(_tag(NS_GML, "featureMember")):
                    for edi in fm2:
                        if edi.tag == _tag(NS_IMKL, "ExtraDetailinfo"):
                            edi_net = edi.find(_tag(NS_IMKL, "inNetwork"))
                            edi_bestand = edi.find(_tag(NS_IMKL, "bestandLocatie"))
                            if (edi_net is not None and edi_bestand is not None
                                    and edi_net.get(_tag(NS_XLINK, "href"), "") == network_href
                                    and edi_bestand.text and edi_bestand.text.lower().endswith(".pdf")):
                                bron_pdf_url = edi_bestand.text
                                break
                    if bron_pdf_url:
                        break

            # EV-detectie (backlog 3)
            ev_info = ev_index.get(network_href, {})
            ev_verplicht = ev_info.get("ev_verplicht", False)
            ev_contactgegevens = ev_info.get("contactgegevens", None)

            # Label teksten voor dit netwerk (backlog 3)
            labels = label_index.get(network_href, [])
            label_tekst = "\n".join(labels) if labels else None

            # Diepte: probeer uit IMKL structuur (niet beschikbaar in huidige data),
            # val terug op tekstveldextractie (backlog 3)
            diepte_m = None
            diepte_bron = None

            if label_tekst:
                diepte_m, diepte_bron = _extract_diepte_uit_tekst(label_tekst)

            leiding = KLICLeiding(
                klic_upload_id=klic_upload_id,
                beheerder=beheerder_naam,
                leidingtype=feature_type,
                thema=thema,
                dxf_laag=dxf_laag,
                geometrie_wkt=geometrie_wkt,
                diepte_m=diepte_m,
                diepte_bron=diepte_bron,
                diepte_override_m=None,
                sleufloze_techniek=sleufloze,
                mogelijk_sleufloze=mat_mogelijk,
                bron_pdf_url=bron_pdf_url,
                imkl_feature_id=gml_id,
                ev_verplicht=ev_verplicht,
                ev_contactgegevens=ev_contactgegevens,
                label_tekst=label_tekst,
                toelichting_tekst=None,
            )
            db.add(leiding)

            count_totaal += 1
            if feature_type in PRIMAIRE_LEIDING_NAMEN:
                count_primair += 1

    db.flush()
    return {
        "count_primair": count_primair,
        "count_totaal": count_totaal,
        "beheerders_set": beheerders,
        "alle_beheerders_set": alle_beheerder_codes,
        "ev_partijen": ev_partijen,
        "ev_zone_data": ev_zone_data,
        "fout": None,
    }


# ── Formaat B: enkel GML bestand ────────────────────────────────────────────

def _store_ev_partijen(order_id: str, ev_partijen: list[dict], db: Session) -> None:
    """Sla EV-partijen op als EVPartij records op de order."""
    from app.order.models import EVPartij
    # Verwijder bestaande EV-partijen (idempotent)
    db.query(EVPartij).filter_by(order_id=order_id).delete()
    db.flush()
    for i, ev in enumerate(ev_partijen):
        partij = EVPartij(
            order_id=order_id,
            naam=f"{ev['beheerder']} — {ev['contactgegevens']}" if ev.get("contactgegevens") else ev["beheerder"],
            volgorde=i,
        )
        db.add(partij)
    db.flush()


def _store_ev_zones(order_id: str, klic_upload_id: str, ev_zone_data: list[dict], db: Session) -> None:
    """Sla EV-zones op als EVZone records."""
    from app.order.models import EVZone
    # Verwijder bestaande EV-zones voor deze order (idempotent)
    db.query(EVZone).filter_by(order_id=order_id).delete()
    db.flush()
    for zd in ev_zone_data:
        zone = EVZone(
            order_id=order_id,
            klic_upload_id=klic_upload_id,
            beheerder=zd.get("beheerder", ""),
            geometrie_wkt=zd["geometrie_wkt"],
            netwerk_href=zd.get("netwerk_href", ""),
        )
        db.add(zone)
    db.flush()


def verwerk_klic_gml(
    gml_pad: str,
    order_id: str,
    klic_upload_id: str,
    db: Session,
) -> None:
    """Verwerk een enkel GML/XML bestand (Formaat B)."""
    from app.order.models import KLICLeiding, KLICUpload

    upload = db.get(KLICUpload, klic_upload_id)
    if not upload:
        return

    # Verwijder eerder geparsede leidingen (idempotent)
    db.query(KLICLeiding).filter_by(klic_upload_id=klic_upload_id).delete()
    db.flush()

    try:
        xml_data = Path(gml_pad).read_bytes()
        resultaat = _parse_gml_file(xml_data, order_id, klic_upload_id, db)

        if resultaat["fout"]:
            upload.verwerkt = False
            upload.verwerk_fout = resultaat["fout"]
            upload.verwerkt_op = datetime.now(timezone.utc)
            db.commit()
            return

        # Sla EV-partijen op
        if resultaat.get("ev_partijen"):
            _store_ev_partijen(order_id, resultaat["ev_partijen"], db)

        # Sla EV-zones op
        if resultaat.get("ev_zone_data"):
            _store_ev_zones(order_id, klic_upload_id, resultaat["ev_zone_data"], db)

        upload.verwerkt = True
        upload.verwerk_fout = None
        upload.aantal_leidingen = resultaat["count_primair"]
        upload.aantal_beheerders = len(resultaat["alle_beheerders_set"])
        upload.verwerkt_op = datetime.now(timezone.utc)
        db.commit()

    except Exception as exc:
        upload.verwerkt = False
        upload.verwerk_fout = f"Verwerkingsfout: {exc}"
        upload.verwerkt_op = datetime.now(timezone.utc)
        db.commit()


def verwerk_klic_zip(
    zip_pad: str,
    project_id: str,
    klic_upload_id: str,
    db: Session,
) -> None:
    """
    Hoofdfunctie: pakt KLIC ZIP uit, parseert GML, slaat leidingen op.
    Bijwerkt KLICUpload.verwerkt, aantal_leidingen, aantal_beheerders, verwerk_fout.
    Gooit geen exceptions — fouten worden opgeslagen in KLICUpload.verwerk_fout.
    """
    from app.order.models import KLICLeiding, KLICUpload

    upload = db.get(KLICUpload, klic_upload_id)
    if not upload:
        return

    # Verwijder eerder geparsede leidingen (idempotent)
    db.query(KLICLeiding).filter_by(klic_upload_id=klic_upload_id).delete()
    db.flush()

    try:
        with zipfile.ZipFile(zip_pad, "r") as zf:
            namen = zf.namelist()
            gml_namen = [n for n in namen if n.endswith(".xml") or n.endswith(".gml")]

        if not gml_namen:
            upload.verwerkt = False
            upload.verwerk_fout = "Geen GML/XML bestanden gevonden in de ZIP"
            upload.verwerkt_op = datetime.now(timezone.utc)
            db.commit()
            return

        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(zip_pad, "r") as zf:
                zf.extractall(tmpdir)

            totaal_primair = 0
            totaal_count = 0
            alle_beheerders_in_leidingen: set[str] = set()
            alle_beheerders_in_levering: set[str] = set()

            alle_ev_partijen: list[dict] = []
            alle_ev_zone_data: list[dict] = []

            for gml_naam in gml_namen:
                gml_pad_file = Path(tmpdir) / gml_naam
                if not gml_pad_file.exists():
                    continue
                xml_data = gml_pad_file.read_bytes()
                resultaat = _parse_gml_file(xml_data, project_id, klic_upload_id, db)
                if resultaat["fout"]:
                    upload.verwerkt = False
                    upload.verwerk_fout = resultaat["fout"]
                    upload.verwerkt_op = datetime.now(timezone.utc)
                    db.commit()
                    return
                totaal_primair += resultaat["count_primair"]
                totaal_count += resultaat["count_totaal"]
                alle_beheerders_in_leidingen.update(resultaat["beheerders_set"])
                alle_beheerders_in_levering.update(resultaat["alle_beheerders_set"])
                alle_ev_partijen.extend(resultaat.get("ev_partijen", []))
                alle_ev_zone_data.extend(resultaat.get("ev_zone_data", []))

        # Sla EV-partijen op
        if alle_ev_partijen:
            _store_ev_partijen(project_id, alle_ev_partijen, db)

        # Sla EV-zones op
        if alle_ev_zone_data:
            _store_ev_zones(project_id, klic_upload_id, alle_ev_zone_data, db)

        # aantal_beheerders = alle Beheerder-entiteiten in de levering
        upload.verwerkt = True
        upload.verwerk_fout = None
        upload.aantal_leidingen = totaal_primair
        upload.aantal_beheerders = len(alle_beheerders_in_levering)
        upload.verwerkt_op = datetime.now(timezone.utc)
        db.commit()

    except zipfile.BadZipFile as exc:
        upload.verwerkt = False
        upload.verwerk_fout = f"Ongeldig ZIP bestand: {exc}"
        upload.verwerkt_op = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:
        upload.verwerkt = False
        upload.verwerk_fout = f"Verwerkingsfout: {exc}"
        upload.verwerkt_op = datetime.now(timezone.utc)
        db.commit()


def verwerk_klic_bestand(
    bestandspad: str,
    order_id: str,
    klic_upload_id: str,
    db: Session,
) -> None:
    """Dispatch naar juiste parser op basis van bestandstype (ZIP vs GML/XML)."""
    if zipfile.is_zipfile(bestandspad):
        verwerk_klic_zip(bestandspad, order_id, klic_upload_id, db)
    else:
        verwerk_klic_gml(bestandspad, order_id, klic_upload_id, db)
