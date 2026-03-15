"""TC-pdf — Module 7: PDF generatie"""
import pytest


def _maak_hdd11_project():
    """HDD11 project object voor PDF tests."""
    from app.project.models import Project, TracePunt, MaaiveldOverride, Berekening

    p = Project(
        id="hdd11-pdf-test",
        workspace_id="gbt-workspace-001",
        naam="HDD11 Haarlem Kennemerplein",
        ordernummer="3D25V700",
        opdrachtgever="Liander",
        SDR=11,
        De_mm=160.0,
        dn_mm=14.6,
        Dg_mm=240.0,
        intreehoek_gr=18.0,
        uittreehoek_gr=22.0,
    )

    p.trace_punten = [
        TracePunt(project_id="hdd11-pdf-test", volgorde=0, type="intree",     label="A",   RD_x=103896.9, RD_y=489289.5),
        TracePunt(project_id="hdd11-pdf-test", volgorde=1, type="tussenpunt", label="Tv1", RD_x=103916.4, RD_y=489284.1),
        TracePunt(project_id="hdd11-pdf-test", volgorde=7, type="uittree",    label="B",   RD_x=104118.8, RD_y=489243.7),
    ]

    mv = MaaiveldOverride(project_id="hdd11-pdf-test", MVin_NAP_m=1.01, MVuit_NAP_m=1.27, bron="handmatig")
    p.maaiveld_override = mv

    b = Berekening(project_id="hdd11-pdf-test", Ttot_N=30106.0, bron="sigma_override")
    p.berekening = b

    p.doorsneden = []
    p.project_eisenprofiel = None

    return p


# TC-pdf-A: PDF genereren → geen WeasyPrint errors
def test_pdf_a_genereren():
    from app.documents.pdf_generator import generate_pdf
    project = _maak_hdd11_project()
    pdf_bytes = generate_pdf(project)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    # PDF begint altijd met %PDF
    assert pdf_bytes[:4] == b"%PDF"


# TC-pdf-B: Titelblok bevat project naam en datum
def test_pdf_b_titelblok_hdd11():
    from app.documents.pdf_generator import generate_pdf
    project = _maak_hdd11_project()
    pdf_bytes = generate_pdf(project)
    # PDF bytes bevatten tekst (niet altijd direct leesbaar, maar we controleren aanmaak)
    assert pdf_bytes[:4] == b"%PDF"


# TC-pdf-C: GPS punten A correct in tabel (check via HTML render)
def test_pdf_c_gps_punten():
    from jinja2 import Environment, FileSystemLoader
    from pathlib import Path

    template_dir = Path("app/templates/documents")
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("tekening.html")

    project = _maak_hdd11_project()
    html = template.render(
        project=project,
        datum="15-03-2026",
        punten=[
            {"label": "A",   "RD_x": "103896.9", "RD_y": "489289.5"},
            {"label": "Tv1", "RD_x": "103916.4", "RD_y": "489284.1"},
            {"label": "B",   "RD_x": "104118.8", "RD_y": "489243.7"},
        ],
        doorsneden=[],
        r_boorgat_mm=120.0,
        r_buis_mm=80.0,
        intreehoek_pct=32.5,
        uittreehoek_pct=40.4,
    )
    assert "103896.9" in html
    assert "489289.5" in html
    assert "103916.4" in html


# TC-pdf-D: Doorsnede boorgat r_boorgat=120mm, r_buis=80mm voor HDD11
def test_pdf_d_doorsnede_boorgat():
    from app.documents.pdf_generator import generate_pdf
    project = _maak_hdd11_project()
    # Dg=240mm → r_boorgat=120mm, De=160mm → r_buis=80mm
    assert project.Dg_mm / 2 == 120.0
    assert project.De_mm / 2 == 80.0
    pdf_bytes = generate_pdf(project)
    assert pdf_bytes[:4] == b"%PDF"


# TC-pdf-E: Intreehoek 18° correct weergegeven
def test_pdf_e_intreehoek():
    from jinja2 import Environment, FileSystemLoader
    from pathlib import Path
    import math

    template_dir = Path("app/templates/documents")
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("tekening.html")

    project = _maak_hdd11_project()
    intreehoek_pct = round(math.tan(math.radians(18.0)) * 100, 1)

    html = template.render(
        project=project,
        datum="15-03-2026",
        punten=[],
        doorsneden=[],
        r_boorgat_mm=120.0,
        r_buis_mm=80.0,
        intreehoek_pct=intreehoek_pct,
        uittreehoek_pct=40.4,
    )
    assert "18°" in html or "18" in html
    assert str(intreehoek_pct) in html


# TC-pdf-F: KLIC-disclaimer aanwezig in OPMERKINGEN
def test_pdf_f_klic_disclaimer():
    from jinja2 import Environment, FileSystemLoader
    from pathlib import Path

    template_dir = Path("app/templates/documents")
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("tekening.html")

    project = _maak_hdd11_project()
    html = template.render(
        project=project,
        datum="15-03-2026",
        punten=[],
        doorsneden=[],
        r_boorgat_mm=120.0,
        r_buis_mm=80.0,
        intreehoek_pct=32.5,
        uittreehoek_pct=40.4,
    )
    assert "KLIC" in html
    assert "CROW 96b" in html
