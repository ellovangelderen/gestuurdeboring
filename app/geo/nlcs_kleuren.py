"""NLCS kleurcodes voor K&L leidingtypen — centrale definitie.

Gebruikt door: PDF generator, DXF generator, trace kaart overlay, legenda.
"""

# Hex kleuren (voor web/SVG)
NLCS_HEX: dict[str, str] = {
    "LAAGSPANNING": "#BE9600",
    "MIDDENSPANNING": "#00823C",
    "HOOGSPANNING": "#DC0000",
    "LD-GAS": "#A05000",
    "WATERLEIDING": "#0055AA",
    "RIOOL-VRIJVERVAL": "#7030A0",
    "PERSRIOOL": "#7030A0",
}

# RGB tuples (voor PIL/Pillow)
NLCS_RGB: dict[str, tuple[int, int, int]] = {
    "LAAGSPANNING": (190, 150, 0),
    "MIDDENSPANNING": (0, 130, 60),
    "HOOGSPANNING": (220, 0, 0),
    "LD-GAS": (160, 80, 0),
    "WATERLEIDING": (0, 85, 170),
    "RIOOL-VRIJVERVAL": (112, 48, 160),
    "PERSRIOOL": (112, 48, 160),
}

# Labels voor legenda
NLCS_LABELS: dict[str, str] = {
    "LAAGSPANNING": "Laagspanning",
    "MIDDENSPANNING": "Middenspanning",
    "HOOGSPANNING": "Hoogspanning",
    "LD-GAS": "Gas",
    "WATERLEIDING": "Water",
    "RIOOL-VRIJVERVAL": "Riool",
    "PERSRIOOL": "Riool (pers)",
}

DEFAULT_HEX = "#999999"
DEFAULT_RGB = (150, 150, 150)
