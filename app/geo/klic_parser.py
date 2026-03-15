"""KLIC IMKL 2.0 GML parser — backlog item 1.

Pakt een KLIC ZIP uit, parseert het GML-bestand en slaat leidingen op als
KLICLeiding-records. Alle coördinaten zijn RD New (EPSG:28992) — geen projectie nodig.
"""
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

# IMKL thema-URL suffix → DXF-laag
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

# Feature-type naam → default thema als Utiliteitsnet onbekend is
FEATURETYPE_TO_THEMA: dict[str, str] = {
    "Elektriciteitskabel":         "laagspanning",
    "OlieGasChemicalienPijpleiding": "gasLageDruk",
    "Waterleiding":                "water",
    "Rioolleiding":                "rioolVrijverval",
    "Telecommunicatiekabel":       "datatransport",
    "Mantelbuis":                  "datatransport",
}


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
    """Bouwt een dict van UtilityLink gml:id → WKT geometrie."""
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
    """Bouwt een dict van Utiliteitsnet gml:id → {thema, bronhouder}."""
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
    """Bouwt een dict van bronhoudercode → organisatienaam."""
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


def _parse_gml_file(
    xml_data: bytes,
    project_id: str,
    klic_upload_id: str,
    db: Session,
) -> dict:
    """
    Parseert één GML/XML bestand en slaat leidingen op in de database.
    Geeft terug: {count_primair, count_totaal, beheerders_set, alle_beheerders_set, fout}.
    """
    from app.project.models import KLICLeiding

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

    count_primair = 0
    count_totaal = 0
    beheerders: set[str] = set()

    for fm in root.iter(_tag(NS_GML, "featureMember")):
        for feature in fm:
            feature_type = feature.tag.split("}")[-1]
            if feature_type not in LEIDING_FEATURE_NAMEN:
                continue

            gml_id = feature.get(_tag(NS_GML, "id"), "")

            # Bepaal netwerk → thema + bronhouder
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

            # Sleufloze detectie: Mantelbuis + diepte NULL + netwerk heeft profielschets PDF
            is_mantelbuis = feature_type == "Mantelbuis"
            netwerk_heeft_pdf = network_href in network_pdf_set
            sleufloze = is_mantelbuis and netwerk_heeft_pdf

            # PDF URL voor bron_pdf_url (eerste PDF van dit netwerk)
            bron_pdf_url = None
            if sleufloze:
                # Zoek eerste ExtraDetailinfo PDF van dit netwerk
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

            leiding = KLICLeiding(
                project_id=project_id,
                klic_upload_id=klic_upload_id,
                beheerder=beheerder_naam,
                leidingtype=feature_type,
                thema=thema,
                dxf_laag=dxf_laag,
                geometrie_wkt=geometrie_wkt,
                diepte_m=None,
                diepte_override_m=None,
                sleufloze_techniek=sleufloze,
                bron_pdf_url=bron_pdf_url,
                imkl_feature_id=gml_id,
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
        "fout": None,
    }


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
    from app.project.models import KLICLeiding, KLICUpload

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

            for gml_naam in gml_namen:
                gml_pad = Path(tmpdir) / gml_naam
                if not gml_pad.exists():
                    continue
                xml_data = gml_pad.read_bytes()
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

        # aantal_beheerders = alle Beheerder-entiteiten in de levering
        # (inclusief beheerders die alleen een brief hebben, zonder kabels)
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
