"""Klantcodes en default akkoord-contactpersonen.

Gebruikt als dropdown-data in de UI.
Volledige bedrijfsnamen bij sommige klanten nog opvragen bij Martien.
"""

KLANTCODES = [
    {"code": "3D", "naam": "3D-Drilling BV",        "akkoord_contact": "Michel Visser",     "logo": "Logo3D.jpg"},
    {"code": "RD", "naam": "R&D Drilling",           "akkoord_contact": "Marcel van Hoolwerff", "logo": ""},
    {"code": "IE", "naam": "Infra Elite",            "akkoord_contact": "Erik Heijnekamp",   "logo": ""},
    {"code": "KB", "naam": "Kappert Infra",          "akkoord_contact": "Alice Kappert",     "logo": ""},
    {"code": "BT", "naam": "BTL Drilling",           "akkoord_contact": "Patricia",          "logo": ""},
    {"code": "TM", "naam": "TM Infra",              "akkoord_contact": ""},
    {"code": "QG", "naam": "QG Infra",              "akkoord_contact": ""},
    {"code": "MM", "naam": "MM Infra",              "akkoord_contact": ""},
    {"code": "HS", "naam": "HS Infra",              "akkoord_contact": ""},
    {"code": "VB", "naam": "VB Infra",              "akkoord_contact": ""},
    {"code": "VG", "naam": "VG Infra",              "akkoord_contact": ""},
    {"code": "EN", "naam": "EN Infra",              "akkoord_contact": ""},
    {"code": "PZ", "naam": "PZ Infra",              "akkoord_contact": ""},
    {"code": "MT", "naam": "MT Infra",              "akkoord_contact": ""},
    {"code": "TI", "naam": "TI Infra",              "akkoord_contact": ""},
    {"code": "NR", "naam": "NR Infra",              "akkoord_contact": ""},
]

ORDER_STATUSES = [
    {"value": "order_received",        "label": "Ontvangen"},
    {"value": "in_progress",           "label": "In uitvoering"},
    {"value": "delivered",             "label": "Geleverd"},
    {"value": "waiting_for_approval",  "label": "Wacht op akkoord"},
    {"value": "done",                  "label": "Afgerond"},
    {"value": "cancelled",            "label": "Geannuleerd"},
]

BORING_TYPES = [
    {"value": "B", "label": "Gestuurde boring"},
    {"value": "N", "label": "Nano boring"},
    {"value": "Z", "label": "Boogzinker (BZ)"},
    {"value": "C", "label": "Calculatie (Sigma)"},
]

VERGUNNING_TYPES = [
    {"value": "-", "label": "Geen"},
    {"value": "P", "label": "Provincie"},
    {"value": "W", "label": "Waterschap"},
    {"value": "R", "label": "Rijkswaterstaat"},
    {"value": "PR", "label": "ProRail"},
    {"value": "G", "label": "Gemeente"},
    {"value": "AO", "label": "Asset owner / beheerder"},
]


def get_akkoord_contact(klantcode: str) -> str:
    """Geeft de default akkoord-contactpersoon voor een klantcode."""
    for kc in KLANTCODES:
        if kc["code"] == klantcode:
            return kc["akkoord_contact"]
    return ""


def get_klant_naam(klantcode: str) -> str:
    """Geeft de bedrijfsnaam voor een klantcode."""
    for kc in KLANTCODES:
        if kc["code"] == klantcode:
            return kc["naam"]
    return klantcode


def get_klant_logo(klantcode: str) -> str:
    """Geeft het logo-bestandsnaam voor een klantcode (of lege string)."""
    for kc in KLANTCODES:
        if kc["code"] == klantcode:
            return kc.get("logo", "")
    return ""
