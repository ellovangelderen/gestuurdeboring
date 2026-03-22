"""GEF/CPT parser — Geotechnical Exchange Format voor sonderingen.

Publieke API:
    parse_gef(content: str) -> GefSondering
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class GefMeetpunt:
    diepte_m: float       # diepte in meters t.o.v. maaiveld
    qc_MPa: float | None  # conusweerstand (MPa)
    fs_kPa: float | None  # kleefweerstand (kPa)
    Rf_pct: float | None  # wrijvingsgetal (%) = fs/qc * 100


@dataclass
class GefSondering:
    naam: str = ""
    datum: str = ""
    rd_x: float | None = None
    rd_y: float | None = None
    z_nap: float | None = None   # maaiveld NAP hoogte
    meetpunten: list[GefMeetpunt] = field(default_factory=list)
    grondtype_per_laag: list[dict] = field(default_factory=list)

    @property
    def max_diepte(self) -> float:
        return max((m.diepte_m for m in self.meetpunten), default=0.0)

    @property
    def gem_qc(self) -> float | None:
        vals = [m.qc_MPa for m in self.meetpunten if m.qc_MPa is not None]
        return sum(vals) / len(vals) if vals else None


def parse_gef(content: str) -> GefSondering:
    """Parse een GEF-bestand (Geotechnical Exchange Format).

    Ondersteunt GEF 1.x en 2.x formaat.
    """
    sondering = GefSondering()
    lines = content.replace("\r\n", "\n").split("\n")

    # Header info
    in_header = True
    column_info = {}  # kolom nr → type
    col_separator = " "
    data_start = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        if stripped.upper() == "#EOH=":
            in_header = False
            data_start = i + 1
            continue

        if not in_header:
            continue

        # Parse header keywords
        if stripped.startswith("#TESTID="):
            sondering.naam = stripped.split("=", 1)[1].strip().strip(",").strip()
        elif stripped.startswith("#STARTDATE="):
            parts = stripped.split("=", 1)[1].strip().split(",")
            if len(parts) >= 3:
                sondering.datum = f"{parts[0].strip()}-{parts[1].strip()}-{parts[2].strip()}"
        elif stripped.startswith("#XYID="):
            parts = stripped.split("=", 1)[1].strip().split(",")
            if len(parts) >= 3:
                try:
                    sondering.rd_x = float(parts[1].strip())
                    sondering.rd_y = float(parts[2].strip())
                except ValueError:
                    pass
        elif stripped.startswith("#ZID="):
            parts = stripped.split("=", 1)[1].strip().split(",")
            if len(parts) >= 2:
                try:
                    sondering.z_nap = float(parts[1].strip())
                except ValueError:
                    pass
        elif stripped.startswith("#COLUMNINFO="):
            # #COLUMNINFO= kolomnr, eenheid, naam, kolomnr
            parts = stripped.split("=", 1)[1].strip().split(",")
            if len(parts) >= 3:
                try:
                    col_nr = int(parts[0].strip())
                    col_naam = parts[2].strip().lower()
                    column_info[col_nr] = col_naam
                except (ValueError, IndexError):
                    pass
        elif stripped.startswith("#COLUMNSEPARATOR="):
            sep = stripped.split("=", 1)[1].strip()
            if sep:
                col_separator = sep

    # Bepaal kolom indices
    diepte_col = None
    qc_col = None
    fs_col = None

    for col_nr, naam in column_info.items():
        n = naam.lower()
        if "sondeerlengte" in n or "penetration" in n or "diepte" in n:
            diepte_col = col_nr - 1  # 0-indexed
        elif "conusweerstand" in n or "conus" in n or "qc" in n:
            qc_col = col_nr - 1
        elif "kleef" in n or "wrijving" in n or "fs" in n:
            fs_col = col_nr - 1

    # Fallback: standaard GEF kolom volgorde
    if diepte_col is None:
        diepte_col = 0
    if qc_col is None:
        qc_col = 1
    if fs_col is None and len(column_info) >= 3:
        fs_col = 2

    # Parse data
    for i in range(data_start, len(lines)):
        line = lines[i].strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue

        if col_separator == ";":
            parts = line.split(";")
        else:
            parts = line.split()

        try:
            diepte = float(parts[diepte_col]) if diepte_col < len(parts) else None
            if diepte is None or diepte < 0:
                continue

            qc = float(parts[qc_col]) if qc_col is not None and qc_col < len(parts) else None
            fs = float(parts[fs_col]) if fs_col is not None and fs_col < len(parts) else None

            # Filter ongeldig (nodata = 999.999 of -9999)
            if qc is not None and (qc > 900 or qc < -900):
                qc = None
            if fs is not None and (fs > 9000 or fs < -9000):
                fs = None

            Rf = None
            if qc is not None and qc > 0 and fs is not None:
                Rf = round((fs / 1000) / qc * 100, 2)  # fs in kPa, qc in MPa

            sondering.meetpunten.append(GefMeetpunt(
                diepte_m=round(diepte, 3),
                qc_MPa=round(qc, 3) if qc is not None else None,
                fs_kPa=round(fs, 1) if fs is not None else None,
                Rf_pct=Rf,
            ))
        except (ValueError, IndexError):
            continue

    # Simpele grondtype classificatie op basis van qc en Rf (Robertson)
    for m in sondering.meetpunten:
        if m.qc_MPa is not None and m.Rf_pct is not None:
            if m.qc_MPa > 10:
                gt = "Zand (grof)"
            elif m.qc_MPa > 5:
                gt = "Zand"
            elif m.qc_MPa > 2 and m.Rf_pct < 2:
                gt = "Zand (fijn)"
            elif m.qc_MPa > 1 and m.Rf_pct > 3:
                gt = "Klei"
            elif m.Rf_pct > 5:
                gt = "Veen"
            else:
                gt = "Klei/Leem"
        else:
            gt = "Onbekend"
        # Niet per punt opslaan, maar kan later per laag geaggregeerd worden

    return sondering
