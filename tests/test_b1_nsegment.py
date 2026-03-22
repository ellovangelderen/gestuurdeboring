"""B1 — N-Segment Profiel Engine tests.

Teststrategie: per stap valideren dat nieuw werkt en oud niet gebroken is.
Tests zijn gemarkeerd per stap zodat ze incrementeel groen worden.

Stap 1: ProfielPunt model
Stap 2: N-segment engine (bereken_boorprofiel)
Stap 3: DXF generator
Stap 4: PDF generator
Stap 5: Conflictcheck
Stap 6: UI + Router
"""
import math
import pytest


# ═══════════════════════════════════════════════════════════════════════════
# STAP 1 — ProfielPunt model
# ═══════════════════════════════════════════════════════════════════════════

class TestStap1Model:
    """ProfielPunt model: aanmaken, opslaan, relatie met Boring."""

    def test_profielpunt_aanmaken(self, db):
        """ProfielPunt kan aangemaakt worden met alle velden."""
        from app.core.database import Base, engine
        import app.order.models
        Base.metadata.create_all(bind=engine)

        from app.order.models import ProfielPunt
        pp = ProfielPunt(
            boring_id="test-boring-1",
            volgorde=0,
            afstand_m=50.0,
            NAP_z=-5.0,
            Rv_m=192.0,
        )
        assert pp.afstand_m == 50.0
        assert pp.NAP_z == -5.0
        assert pp.Rv_m == 192.0

    def test_profielpunt_opslaan_en_ophalen(self, db):
        """ProfielPunt kan in DB opgeslagen en opgehaald worden."""
        from app.core.database import Base, engine
        import app.order.models
        Base.metadata.create_all(bind=engine)

        from app.order.models import Boring, Order, ProfielPunt

        order = Order(id="pp-order", workspace_id="test", ordernummer="PP-001")
        db.add(order)
        boring = Boring(id="pp-boring", order_id="pp-order", volgnummer=1, type="B")
        db.add(boring)
        db.flush()

        pp1 = ProfielPunt(boring_id="pp-boring", volgorde=0, afstand_m=40.0, NAP_z=-4.5, Rv_m=192.0)
        pp2 = ProfielPunt(boring_id="pp-boring", volgorde=1, afstand_m=120.0, NAP_z=-6.0, Rv_m=150.0)
        db.add_all([pp1, pp2])
        db.commit()

        punten = db.query(ProfielPunt).filter_by(boring_id="pp-boring").order_by(ProfielPunt.volgorde).all()
        assert len(punten) == 2
        assert punten[0].afstand_m == 40.0
        assert punten[1].NAP_z == -6.0

    def test_profielpunt_relatie_boring(self, db):
        """Boring.profiel_punten geeft de gekoppelde ProfielPunten."""
        from app.core.database import Base, engine
        import app.order.models
        Base.metadata.create_all(bind=engine)

        from app.order.models import Boring, Order, ProfielPunt

        order = Order(id="pp-rel-order", workspace_id="test", ordernummer="PP-REL")
        db.add(order)
        boring = Boring(id="pp-rel-boring", order_id="pp-rel-order", volgnummer=1, type="B")
        db.add(boring)
        db.flush()

        db.add(ProfielPunt(boring_id="pp-rel-boring", volgorde=0, afstand_m=60.0, NAP_z=-5.0, Rv_m=192.0))
        db.commit()

        db.expire_all()
        b = db.get(Boring, "pp-rel-boring")
        assert len(b.profiel_punten) == 1
        assert b.profiel_punten[0].afstand_m == 60.0


# ═══════════════════════════════════════════════════════════════════════════
# STAP 2 — N-segment engine
# ═══════════════════════════════════════════════════════════════════════════

class TestStap2EngineRegressie:
    """Bestaand gedrag: zonder profielpunten moet het profiel identiek zijn."""

    def test_standaard_5_segment(self):
        """Zonder profielpunten → 5 segmenten (lijn, arc, lijn, arc, lijn)."""
        from app.geo.profiel import bereken_boorprofiel
        profiel = bereken_boorprofiel(
            L_totaal_m=200.0, MVin_NAP_m=0.5, MVuit_NAP_m=0.3,
            alpha_in_gr=18.0, alpha_uit_gr=22.0, De_mm=160.0,
        )
        assert len(profiel.segmenten) == 5
        types = [s["type"] for s in profiel.segmenten]
        assert types == ["lijn", "arc", "lijn", "arc", "lijn"]

    def test_horizontaal_segment_positief(self):
        """Horizontaal segment heeft positieve lengte bij L=200m."""
        from app.geo.profiel import bereken_boorprofiel
        profiel = bereken_boorprofiel(
            L_totaal_m=200.0, MVin_NAP_m=0.5, MVuit_NAP_m=0.3,
            alpha_in_gr=18.0, alpha_uit_gr=22.0, De_mm=160.0,
        )
        horiz = [s for s in profiel.segmenten if s.get("horizontaal")]
        assert len(horiz) == 1
        assert horiz[0]["lengte"] > 0

    def test_continuiteit(self):
        """Eind van elk segment = begin van volgend segment."""
        from app.geo.profiel import bereken_boorprofiel
        profiel = bereken_boorprofiel(
            L_totaal_m=200.0, MVin_NAP_m=0.5, MVuit_NAP_m=0.3,
            alpha_in_gr=18.0, alpha_uit_gr=22.0, De_mm=160.0,
        )
        for i in range(len(profiel.segmenten) - 1):
            s = profiel.segmenten[i]
            v = profiel.segmenten[i + 1]
            assert s["x_end"] == pytest.approx(v["x_start"], abs=0.1), \
                f"Segment {i} x_end={s['x_end']} != {i+1} x_start={v['x_start']}"
            assert s["z_end"] == pytest.approx(v["z_start"], abs=0.1), \
                f"Segment {i} z_end={s['z_end']} != {i+1} z_start={v['z_start']}"

    def test_rv_berekening(self):
        """Rv = 1200 * De (in meters)."""
        from app.geo.profiel import bereken_Rv
        assert bereken_Rv(160.0) == pytest.approx(192.0)
        assert bereken_Rv(110.0) == pytest.approx(132.0)

    def test_trace_te_kort_past_rv_aan(self):
        """Bij kort tracé wordt Rv verkleind, geen crash."""
        from app.geo.profiel import bereken_boorprofiel
        profiel = bereken_boorprofiel(
            L_totaal_m=50.0, MVin_NAP_m=0.5, MVuit_NAP_m=0.3,
            alpha_in_gr=18.0, alpha_uit_gr=22.0, De_mm=160.0,
        )
        assert profiel.Rv_m < 192.0
        assert len(profiel.segmenten) == 5

    def test_begin_op_maaiveld_eind_op_maaiveld(self):
        """Profiel begint bij MVin en eindigt bij MVuit."""
        from app.geo.profiel import bereken_boorprofiel
        profiel = bereken_boorprofiel(
            L_totaal_m=200.0, MVin_NAP_m=1.0, MVuit_NAP_m=0.5,
            alpha_in_gr=18.0, alpha_uit_gr=22.0, De_mm=160.0,
        )
        assert profiel.segmenten[0]["x_start"] == pytest.approx(0.0)
        assert profiel.segmenten[0]["z_start"] == pytest.approx(1.0)
        assert profiel.segmenten[-1]["x_end"] == pytest.approx(200.0)
        assert profiel.segmenten[-1]["z_end"] == pytest.approx(0.5)

    def test_boogzinker_ongewijzigd(self):
        """Type Z profiel (boogzinker) blijft werken."""
        from app.geo.profiel import bereken_boorprofiel_z
        profiel = bereken_boorprofiel_z(
            L_totaal_m=30.0, MVin_NAP_m=0.5, MVuit_NAP_m=0.3,
            booghoek_gr=7.5, De_mm=110.0,
        )
        assert len(profiel.segmenten) == 1
        assert profiel.segmenten[0]["type"] == "arc"


class TestStap2EngineNSegment:
    """N-segment: profielpunten voor tussenliggende dieptepunten."""

    def test_1_tussenpunt_meer_segmenten(self):
        """1 tussenpunt genereert meer dan 5 segmenten."""
        from app.geo.profiel import bereken_boorprofiel, ProfielPunt
        profiel = bereken_boorprofiel(
            L_totaal_m=200.0, MVin_NAP_m=0.5, MVuit_NAP_m=0.3,
            alpha_in_gr=18.0, alpha_uit_gr=22.0, De_mm=160.0,
            profiel_punten=[
                ProfielPunt(afstand_m=100.0, NAP_z=-6.0, Rv_m=192.0),
            ],
        )
        assert len(profiel.segmenten) > 5

    def test_1_tussenpunt_continuiteit(self):
        """Alle segmenten sluiten op elkaar aan met 1 tussenpunt."""
        from app.geo.profiel import bereken_boorprofiel, ProfielPunt
        profiel = bereken_boorprofiel(
            L_totaal_m=200.0, MVin_NAP_m=0.5, MVuit_NAP_m=0.3,
            alpha_in_gr=18.0, alpha_uit_gr=22.0, De_mm=160.0,
            profiel_punten=[
                ProfielPunt(afstand_m=100.0, NAP_z=-6.0, Rv_m=192.0),
            ],
        )
        for i in range(len(profiel.segmenten) - 1):
            s = profiel.segmenten[i]
            v = profiel.segmenten[i + 1]
            assert s["x_end"] == pytest.approx(v["x_start"], abs=0.5), \
                f"Segment {i} x gap: {s['x_end']} vs {v['x_start']}"
            assert s["z_end"] == pytest.approx(v["z_start"], abs=0.5), \
                f"Segment {i} z gap: {s['z_end']} vs {v['z_start']}"

    def test_1_tussenpunt_begin_eind_maaiveld(self):
        """Profiel begint nog steeds bij MVin en eindigt bij MVuit."""
        from app.geo.profiel import bereken_boorprofiel, ProfielPunt
        profiel = bereken_boorprofiel(
            L_totaal_m=200.0, MVin_NAP_m=0.5, MVuit_NAP_m=0.3,
            alpha_in_gr=18.0, alpha_uit_gr=22.0, De_mm=160.0,
            profiel_punten=[
                ProfielPunt(afstand_m=100.0, NAP_z=-6.0, Rv_m=192.0),
            ],
        )
        assert profiel.segmenten[0]["z_start"] == pytest.approx(0.5)
        assert profiel.segmenten[-1]["z_end"] == pytest.approx(0.3)

    def test_2_tussenpunten(self):
        """2 tussenpunten: profiel passeert beide dieptepunten."""
        from app.geo.profiel import bereken_boorprofiel, ProfielPunt
        profiel = bereken_boorprofiel(
            L_totaal_m=300.0, MVin_NAP_m=0.5, MVuit_NAP_m=0.3,
            alpha_in_gr=18.0, alpha_uit_gr=22.0, De_mm=160.0,
            profiel_punten=[
                ProfielPunt(afstand_m=100.0, NAP_z=-5.0, Rv_m=192.0),
                ProfielPunt(afstand_m=200.0, NAP_z=-7.0, Rv_m=150.0),
            ],
        )
        assert len(profiel.segmenten) > 5
        # Diepste punt moet -7.0 of dieper zijn
        min_z = min(s["z_start"] for s in profiel.segmenten)
        min_z = min(min_z, min(s["z_end"] for s in profiel.segmenten))
        assert min_z <= -7.0 + 0.5  # tolerantie voor boog

    def test_per_boog_eigen_rv(self):
        """Elke arc kan eigen Rv hebben."""
        from app.geo.profiel import bereken_boorprofiel, ProfielPunt
        profiel = bereken_boorprofiel(
            L_totaal_m=300.0, MVin_NAP_m=0.5, MVuit_NAP_m=0.3,
            alpha_in_gr=18.0, alpha_uit_gr=22.0, De_mm=160.0,
            profiel_punten=[
                ProfielPunt(afstand_m=150.0, NAP_z=-6.0, Rv_m=150.0),
            ],
        )
        arcs = [s for s in profiel.segmenten if s["type"] == "arc"]
        radii = set(s["radius"] for s in arcs)
        # Er moeten minstens 2 verschillende radii zijn
        assert len(radii) >= 2

    def test_diepte_nap_is_diepste_punt(self):
        """profiel.diepte_NAP_m is het diepste punt van alle segmenten."""
        from app.geo.profiel import bereken_boorprofiel, ProfielPunt
        profiel = bereken_boorprofiel(
            L_totaal_m=300.0, MVin_NAP_m=0.5, MVuit_NAP_m=0.3,
            alpha_in_gr=18.0, alpha_uit_gr=22.0, De_mm=160.0,
            profiel_punten=[
                ProfielPunt(afstand_m=150.0, NAP_z=-8.0, Rv_m=192.0),
            ],
        )
        # diepte_NAP_m moet het diepste punt zijn
        assert profiel.diepte_NAP_m <= -8.0 + 0.5

    def test_tussenpunt_ondieper_dan_standaard(self):
        """Tussenpunt dat ondieper is dan standaard dekking: profiel komt omhoog."""
        from app.geo.profiel import bereken_boorprofiel, ProfielPunt
        # Standaard diepte bij dekking 3.0m zou ca -2.5 NAP zijn
        profiel = bereken_boorprofiel(
            L_totaal_m=200.0, MVin_NAP_m=0.5, MVuit_NAP_m=0.3,
            alpha_in_gr=18.0, alpha_uit_gr=22.0, De_mm=160.0,
            profiel_punten=[
                ProfielPunt(afstand_m=100.0, NAP_z=-2.0, Rv_m=192.0),
            ],
        )
        # Moet niet crashen, profiel moet het punt benaderen
        assert len(profiel.segmenten) > 0

    def test_lege_profielpunten_is_standaard(self):
        """Lege lijst profielpunten = zelfde als zonder profielpunten."""
        from app.geo.profiel import bereken_boorprofiel
        p1 = bereken_boorprofiel(
            L_totaal_m=200.0, MVin_NAP_m=0.5, MVuit_NAP_m=0.3,
            alpha_in_gr=18.0, alpha_uit_gr=22.0, De_mm=160.0,
        )
        p2 = bereken_boorprofiel(
            L_totaal_m=200.0, MVin_NAP_m=0.5, MVuit_NAP_m=0.3,
            alpha_in_gr=18.0, alpha_uit_gr=22.0, De_mm=160.0,
            profiel_punten=[],
        )
        assert len(p1.segmenten) == len(p2.segmenten)
        assert p1.diepte_NAP_m == pytest.approx(p2.diepte_NAP_m)


# ═══════════════════════════════════════════════════════════════════════════
# STAP 3 — DXF generator
# ═══════════════════════════════════════════════════════════════════════════

class TestStap3DXF:
    """DXF generator met N-segment profiel."""

    def _maak_boring_met_profiel(self, profiel_punten=None):
        from app.order.models import Boring, Order, TracePunt, MaaiveldOverride
        order = Order(id="dxf-n-order", workspace_id="test", ordernummer="DXF-N-TEST", locatie="Test")
        boring = Boring(
            id="dxf-n-boring", order_id="dxf-n-order", volgnummer=1, type="B",
            De_mm=160.0, Dg_mm=240.0, intreehoek_gr=18.0, uittreehoek_gr=22.0,
        )
        boring.trace_punten = [
            TracePunt(boring_id="dxf-n-boring", volgorde=0, type="intree", label="A", RD_x=100000.0, RD_y=400000.0),
            TracePunt(boring_id="dxf-n-boring", volgorde=1, type="uittree", label="B", RD_x=100300.0, RD_y=400000.0),
        ]
        boring.maaiveld_override = MaaiveldOverride(boring_id="dxf-n-boring", MVin_NAP_m=0.5, MVuit_NAP_m=0.3)
        boring.doorsneden = []
        boring.berekening = None

        if profiel_punten is not None:
            boring.profiel_punten = profiel_punten
        else:
            boring.profiel_punten = []

        return order, boring

    def test_dxf_standaard_2_arcs(self):
        """DXF zonder profielpunten: 2 ARCs op LP-BOORLIJN (regressie)."""
        import ezdxf
        import io
        from app.documents.dxf_generator import generate_dxf
        order, boring = self._maak_boring_met_profiel()
        dxf_bytes = generate_dxf(boring, order)
        doc = ezdxf.read(io.StringIO(dxf_bytes.decode("utf-8")))
        msp = doc.modelspace()
        arcs = [e for e in msp if e.dxftype() == "ARC" and e.dxf.layer == "LP-BOORLIJN"]
        assert len(arcs) == 2

    def test_dxf_met_tussenpunt_meer_arcs(self):
        """DXF met 1 tussenpunt: meer dan 2 ARCs."""
        import ezdxf
        import io
        from app.order.models import ProfielPunt
        from app.documents.dxf_generator import generate_dxf
        pp = [ProfielPunt(boring_id="dxf-n-boring", volgorde=0, afstand_m=150.0, NAP_z=-6.0, Rv_m=150.0)]
        order, boring = self._maak_boring_met_profiel(profiel_punten=pp)
        dxf_bytes = generate_dxf(boring, order)
        doc = ezdxf.read(io.StringIO(dxf_bytes.decode("utf-8")))
        msp = doc.modelspace()
        arcs = [e for e in msp if e.dxftype() == "ARC" and e.dxf.layer == "LP-BOORLIJN"]
        assert len(arcs) > 2

    def test_dxf_geen_crash_zonder_maaiveld(self):
        """DXF zonder maaiveld crasht niet (regressie)."""
        from app.order.models import Boring, Order, TracePunt
        from app.documents.dxf_generator import generate_dxf
        order = Order(id="dxf-nomv", workspace_id="test", ordernummer="DXF-NOMV")
        boring = Boring(id="dxf-nomv-b", order_id="dxf-nomv", volgnummer=1, type="B", De_mm=160.0, Dg_mm=240.0)
        boring.trace_punten = [
            TracePunt(boring_id="dxf-nomv-b", volgorde=0, type="intree", label="A", RD_x=100000.0, RD_y=400000.0),
            TracePunt(boring_id="dxf-nomv-b", volgorde=1, type="uittree", label="B", RD_x=100200.0, RD_y=400000.0),
        ]
        boring.maaiveld_override = None
        boring.doorsneden = []
        boring.berekening = None
        boring.profiel_punten = []
        dxf_bytes = generate_dxf(boring, order)
        assert isinstance(dxf_bytes, bytes)
        assert len(dxf_bytes) > 0


# ═══════════════════════════════════════════════════════════════════════════
# STAP 4 — PDF generator
# ═══════════════════════════════════════════════════════════════════════════

class TestStap4PDF:
    """PDF generator met N-segment profiel."""

    def test_pdf_standaard_profiel(self):
        """PDF met standaard profiel genereert geldig PDF bestand."""
        from app.order.models import Boring, Order, TracePunt, MaaiveldOverride
        from app.documents.pdf_generator import generate_pdf
        order = Order(id="pdf-n-order", workspace_id="test", ordernummer="PDF-N", locatie="Test")
        boring = Boring(
            id="pdf-n-boring", order_id="pdf-n-order", volgnummer=1, type="B",
            SDR=11, De_mm=160.0, Dg_mm=240.0, intreehoek_gr=18.0, uittreehoek_gr=22.0,
        )
        boring.trace_punten = [
            TracePunt(boring_id="pdf-n-boring", volgorde=0, type="intree", label="A", RD_x=100000.0, RD_y=400000.0),
            TracePunt(boring_id="pdf-n-boring", volgorde=1, type="uittree", label="B", RD_x=100200.0, RD_y=400000.0),
        ]
        boring.maaiveld_override = MaaiveldOverride(boring_id="pdf-n-boring", MVin_NAP_m=0.5, MVuit_NAP_m=0.3)
        boring.doorsneden = []
        boring.berekening = None
        boring.profiel_punten = []

        pdf_bytes = generate_pdf(boring, order)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"

    def test_pdf_met_tussenpunt(self):
        """PDF met N-segment profiel genereert zonder crash."""
        from app.order.models import Boring, Order, TracePunt, MaaiveldOverride, ProfielPunt
        from app.documents.pdf_generator import generate_pdf
        order = Order(id="pdf-np-order", workspace_id="test", ordernummer="PDF-NP", locatie="Test")
        boring = Boring(
            id="pdf-np-boring", order_id="pdf-np-order", volgnummer=1, type="B",
            SDR=11, De_mm=160.0, Dg_mm=240.0, intreehoek_gr=18.0, uittreehoek_gr=22.0,
        )
        boring.trace_punten = [
            TracePunt(boring_id="pdf-np-boring", volgorde=0, type="intree", label="A", RD_x=100000.0, RD_y=400000.0),
            TracePunt(boring_id="pdf-np-boring", volgorde=1, type="uittree", label="B", RD_x=100300.0, RD_y=400000.0),
        ]
        boring.maaiveld_override = MaaiveldOverride(boring_id="pdf-np-boring", MVin_NAP_m=0.5, MVuit_NAP_m=0.3)
        boring.doorsneden = []
        boring.berekening = None
        boring.profiel_punten = [
            ProfielPunt(boring_id="pdf-np-boring", volgorde=0, afstand_m=150.0, NAP_z=-6.0, Rv_m=150.0),
        ]

        pdf_bytes = generate_pdf(boring, order)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"


# ═══════════════════════════════════════════════════════════════════════════
# STAP 5 — Conflictcheck
# ═══════════════════════════════════════════════════════════════════════════

class TestStap5Conflictcheck:
    """Conflictcheck met N-segment profiel."""

    def test_boor_z_op_x_standaard(self):
        """_boor_z_op_x werkt met standaard 5-segment profiel op het horizontale segment."""
        from app.geo.profiel import bereken_boorprofiel
        from app.geo.conflictcheck import _boor_z_op_x
        profiel = bereken_boorprofiel(
            L_totaal_m=200.0, MVin_NAP_m=0.5, MVuit_NAP_m=0.3,
            alpha_in_gr=18.0, alpha_uit_gr=22.0, De_mm=160.0,
        )
        # Horizontaal segment: z moet op diepte_NAP liggen
        horiz = [s for s in profiel.segmenten if s.get("horizontaal")]
        assert len(horiz) == 1
        x_mid = (horiz[0]["x_start"] + horiz[0]["x_end"]) / 2
        z_mid = _boor_z_op_x(profiel, x_mid)
        assert z_mid == pytest.approx(profiel.diepte_NAP_m, abs=0.1)

    def test_boor_z_op_x_n_segment(self):
        """_boor_z_op_x werkt met N-segment profiel op lijn-segmenten."""
        from app.geo.profiel import bereken_boorprofiel, ProfielPunt
        from app.geo.conflictcheck import _boor_z_op_x
        profiel = bereken_boorprofiel(
            L_totaal_m=300.0, MVin_NAP_m=0.5, MVuit_NAP_m=0.3,
            alpha_in_gr=18.0, alpha_uit_gr=22.0, De_mm=160.0,
            profiel_punten=[
                ProfielPunt(afstand_m=150.0, NAP_z=-6.0, Rv_m=192.0),
            ],
        )
        # Zoek een horizontaal lijn-segment en test daarop
        lijn_segs = [s for s in profiel.segmenten if s["type"] == "lijn" and s.get("horizontaal")]
        if lijn_segs:
            s = lijn_segs[0]
            x_mid = (s["x_start"] + s["x_end"]) / 2
            z = _boor_z_op_x(profiel, x_mid)
            assert z is not None
            assert z < 0.0

    def test_boor_z_op_x_geen_gaten(self):
        """N-segment profiel heeft geen gaten op lijn-segmenten."""
        from app.geo.profiel import bereken_boorprofiel, ProfielPunt
        from app.geo.conflictcheck import _boor_z_op_x
        profiel = bereken_boorprofiel(
            L_totaal_m=300.0, MVin_NAP_m=0.5, MVuit_NAP_m=0.3,
            alpha_in_gr=18.0, alpha_uit_gr=22.0, De_mm=160.0,
            profiel_punten=[
                ProfielPunt(afstand_m=100.0, NAP_z=-5.0, Rv_m=192.0),
                ProfielPunt(afstand_m=200.0, NAP_z=-7.0, Rv_m=150.0),
            ],
        )
        # Check alle lijn-segmenten — z moet een waarde geven
        for seg in profiel.segmenten:
            if seg["type"] == "lijn" and seg["x_end"] > seg["x_start"] + 0.1:
                x_mid = (seg["x_start"] + seg["x_end"]) / 2
                z = _boor_z_op_x(profiel, x_mid)
                assert z is not None, f"Gat in profiel op x={x_mid}"


# ═══════════════════════════════════════════════════════════════════════════
# STAP 6 — UI + Router
# ═══════════════════════════════════════════════════════════════════════════

class TestStap6Router:
    """Router: profielpunten opslaan en laden via HTTP."""

    def test_brondata_pagina_laadt(self, client, workspace, db):
        """Brondata pagina laadt zonder crash met profielpunten."""
        from app.core.database import Base, engine
        import app.order.models
        Base.metadata.create_all(bind=engine)

        from app.order.models import Order, Boring
        from tests.conftest import AUTH

        order = Order(id="rt-pp-order", workspace_id="gbt-workspace-001", ordernummer="RT-PP")
        db.add(order)
        boring = Boring(id="rt-pp-boring", order_id="rt-pp-order", volgnummer=1, type="B")
        db.add(boring)
        db.commit()

        resp = client.get("/orders/rt-pp-order/boringen/1/brondata", auth=AUTH)
        assert resp.status_code == 200

    def test_profielpunten_opslaan(self, client, workspace, db):
        """POST profielpunten slaat ze op in DB."""
        from app.core.database import Base, engine
        import app.order.models
        Base.metadata.create_all(bind=engine)

        from app.order.models import Order, Boring, ProfielPunt
        from tests.conftest import AUTH

        order = Order(id="rt-pp-save", workspace_id="gbt-workspace-001", ordernummer="RT-SAVE")
        db.add(order)
        boring = Boring(id="rt-pp-save-b", order_id="rt-pp-save", volgnummer=1, type="B")
        db.add(boring)
        db.commit()

        resp = client.post(
            "/orders/rt-pp-save/boringen/1/profielpunten",
            data={
                "afstand_list": "50.0,150.0",
                "NAP_z_list": "-5.0,-7.0",
                "Rv_list": "192.0,150.0",
            },
            auth=AUTH,
            follow_redirects=True,
        )
        assert resp.status_code == 200

        db.expire_all()
        punten = db.query(ProfielPunt).filter_by(boring_id="rt-pp-save-b").order_by(ProfielPunt.volgorde).all()
        assert len(punten) == 2
        assert punten[0].afstand_m == 50.0
        assert punten[1].NAP_z == -7.0


# ═══════════════════════════════════════════════════════════════════════════
# Helper
# ═══════════════════════════════════════════════════════════════════════════

def _weasyprint_available():
    try:
        import weasyprint  # noqa: F401
        return True
    except ImportError:
        return False
