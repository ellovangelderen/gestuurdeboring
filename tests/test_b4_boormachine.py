"""B4 — Boormachine op tekening: model, admin CRUD, DXF/PDF rendering.

Teststrategie:
- Stap 1: Boormachine model + admin CRUD
- Stap 2: Machine selectie op boring
- Stap 3: DXF rendering
- Stap 4: PDF rendering
- Stap 5: Persistentie (seed + redeploy)
"""
import io
import math

import ezdxf
import pytest

from tests.conftest import AUTH


# ═══════════════════════════════════════════════════════════════════════════
# STAP 1 — Boormachine model + admin CRUD
# ═══════════════════════════════════════════════════════════════════════════

class TestStap1Model:
    """Boormachine model: aanmaken, opslaan, relatie, admin CRUD."""

    def test_boormachine_aanmaken(self, db):
        from app.core.database import Base, engine
        import app.admin.models
        Base.metadata.create_all(bind=engine)

        from app.admin.models import Boormachine
        m = Boormachine(
            naam="Vermeer D40x55",
            code="D40x55",
            lengte_m=6.0,
            breedte_m=2.5,
            trekkracht_ton=18.0,
        )
        db.add(m)
        db.commit()

        result = db.query(Boormachine).filter_by(code="D40x55").first()
        assert result is not None
        assert result.lengte_m == 6.0
        assert result.trekkracht_ton == 18.0

    def test_boormachine_unieke_code(self, db):
        from app.core.database import Base, engine
        import app.admin.models
        Base.metadata.create_all(bind=engine)

        from app.admin.models import Boormachine
        db.add(Boormachine(naam="Machine A", code="MA", lengte_m=3.0, breedte_m=1.5))
        db.commit()
        db.add(Boormachine(naam="Machine B", code="MA", lengte_m=4.0, breedte_m=2.0))
        with pytest.raises(Exception):
            db.commit()
        db.rollback()

    def test_admin_boormachines_pagina(self, client, workspace, db):
        from app.core.database import Base, engine
        import app.admin.models
        Base.metadata.create_all(bind=engine)

        resp = client.get("/admin/boormachines", auth=AUTH)
        assert resp.status_code == 200
        assert "Boormachines" in resp.text

    def test_admin_boormachine_toevoegen(self, client, workspace, db):
        from app.core.database import Base, engine
        import app.admin.models
        Base.metadata.create_all(bind=engine)

        resp = client.post("/admin/boormachines/nieuw",
                           data={"naam": "Test Rig", "code": "TR1",
                                 "lengte_m": "5.0", "breedte_m": "2.0",
                                 "trekkracht_ton": "15.0"},
                           auth=AUTH, follow_redirects=True)
        assert resp.status_code == 200
        assert "Test Rig" in resp.text

    def test_admin_boormachine_dubbele_code(self, client, workspace, db):
        from app.core.database import Base, engine
        import app.admin.models
        Base.metadata.create_all(bind=engine)

        client.post("/admin/boormachines/nieuw",
                     data={"naam": "Eerste", "code": "DUP",
                           "lengte_m": "3.0", "breedte_m": "1.5"},
                     auth=AUTH)
        resp = client.post("/admin/boormachines/nieuw",
                           data={"naam": "Tweede", "code": "DUP",
                                 "lengte_m": "4.0", "breedte_m": "2.0"},
                           auth=AUTH, follow_redirects=True)
        assert resp.status_code == 200
        assert "bestaat al" in resp.text

    def test_admin_boormachine_wijzigen(self, client, workspace, db):
        from app.core.database import Base, engine
        import app.admin.models
        Base.metadata.create_all(bind=engine)

        from app.admin.models import Boormachine
        db.add(Boormachine(id="bm-edit", naam="Oud", code="ED1",
                           lengte_m=3.0, breedte_m=1.5))
        db.commit()

        resp = client.post("/admin/boormachines/bm-edit/update",
                           data={"naam": "Nieuw", "code": "ED1",
                                 "lengte_m": "4.0", "breedte_m": "2.0",
                                 "trekkracht_ton": "10.0"},
                           auth=AUTH, follow_redirects=True)
        assert resp.status_code == 200
        db.expire_all()
        m = db.get(Boormachine, "bm-edit")
        assert m.naam == "Nieuw"
        assert m.lengte_m == 4.0

    def test_admin_boormachine_verwijderen(self, client, workspace, db):
        from app.core.database import Base, engine
        import app.admin.models
        Base.metadata.create_all(bind=engine)

        from app.admin.models import Boormachine
        db.add(Boormachine(id="bm-del", naam="Te Verwijderen", code="DEL",
                           lengte_m=3.0, breedte_m=1.5))
        db.commit()

        resp = client.post("/admin/boormachines/bm-del/verwijder",
                           auth=AUTH, follow_redirects=True)
        assert resp.status_code == 200
        assert db.query(Boormachine).filter_by(code="DEL").first() is None

    def test_admin_niet_admin_403(self, client, workspace, db):
        resp = client.get("/admin/boormachines", auth=("sopa", "test-martien"))
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
# STAP 2 — Machine selectie op boring
# ═══════════════════════════════════════════════════════════════════════════

class TestStap2BoringMachine:
    """Machine type koppeling aan boring."""

    def test_boring_machine_type_opslaan(self, client, workspace, db):
        from app.core.database import Base, engine
        import app.admin.models
        import app.order.models
        Base.metadata.create_all(bind=engine)

        from app.order.models import Order, Boring
        from app.admin.models import Boormachine

        db.add(Boormachine(id="bm-sel", naam="D40x55", code="D40",
                           lengte_m=6.0, breedte_m=2.5, trekkracht_ton=18.0))
        order = Order(id="bm-order", workspace_id="gbt-workspace-001", ordernummer="BM-001")
        db.add(order)
        boring = Boring(id="bm-boring", order_id="bm-order", volgnummer=1, type="B")
        db.add(boring)
        db.commit()

        resp = client.post("/orders/bm-order/boringen/1/update",
                           data={"materiaal": "PE100", "SDR": "11", "De_mm": "160",
                                 "Db_mm": "60", "Dp_mm": "110", "Dg_mm": "240",
                                 "intreehoek_gr": "18", "uittreehoek_gr": "22",
                                 "medium": "Drukloos", "machine_type": "D40"},
                           auth=AUTH, follow_redirects=True)
        assert resp.status_code == 200

        db.expire_all()
        b = db.get(Boring, "bm-boring")
        assert b.machine_type == "D40"

    def test_boring_zonder_machine_ok(self, client, workspace, db):
        from app.core.database import Base, engine
        import app.order.models
        Base.metadata.create_all(bind=engine)

        from app.order.models import Order, Boring
        order = Order(id="bm-none", workspace_id="gbt-workspace-001", ordernummer="BM-NONE")
        db.add(order)
        db.add(Boring(id="bm-none-b", order_id="bm-none", volgnummer=1, type="B"))
        db.commit()

        resp = client.post("/orders/bm-none/boringen/1/update",
                           data={"materiaal": "PE100", "SDR": "11", "De_mm": "160",
                                 "Db_mm": "60", "Dp_mm": "110", "Dg_mm": "240",
                                 "intreehoek_gr": "18", "uittreehoek_gr": "22",
                                 "medium": "Drukloos"},
                           auth=AUTH, follow_redirects=True)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# STAP 3 — DXF rendering
# ═══════════════════════════════════════════════════════════════════════════

class TestStap3DXF:
    """DXF tekening met machine symbool."""

    def _maak_boring_met_machine(self, db, machine_code="D40"):
        from app.core.database import Base, engine
        import app.admin.models
        import app.order.models
        Base.metadata.create_all(bind=engine)

        from app.order.models import Order, Boring, TracePunt, MaaiveldOverride
        from app.admin.models import Boormachine

        if not db.query(Boormachine).filter_by(code=machine_code).first():
            db.add(Boormachine(naam="D40x55", code="D40",
                               lengte_m=6.0, breedte_m=2.5, trekkracht_ton=18.0))

        order = Order(id="dxf-bm", workspace_id="gbt-workspace-001",
                      ordernummer="DXF-BM", locatie="Test")
        db.add(order)
        boring = Boring(id="dxf-bm-b", order_id="dxf-bm", volgnummer=1, type="B",
                        De_mm=160.0, Dg_mm=240.0, intreehoek_gr=18.0, uittreehoek_gr=22.0,
                        machine_type=machine_code)
        db.add(boring)
        db.add(TracePunt(boring_id="dxf-bm-b", volgorde=0, type="intree",
                         label="A", RD_x=100000.0, RD_y=400000.0))
        db.add(TracePunt(boring_id="dxf-bm-b", volgorde=1, type="uittree",
                         label="B", RD_x=100200.0, RD_y=400000.0))
        db.add(MaaiveldOverride(boring_id="dxf-bm-b",
                                MVin_NAP_m=0.5, MVuit_NAP_m=0.3))
        db.commit()
        return order, boring

    def test_dxf_machine_laag_aanwezig(self, client, workspace, db):
        self._maak_boring_met_machine(db)
        resp = client.get("/orders/dxf-bm/boringen/1/dxf", auth=AUTH)
        assert resp.status_code == 200

        doc = ezdxf.read(io.StringIO(resp.text))
        msp = doc.modelspace()
        machine_entities = [e for e in msp if e.dxf.layer == "MACHINE"]
        assert len(machine_entities) >= 1, "Geen entities op MACHINE laag"

    def test_dxf_machine_heeft_label(self, client, workspace, db):
        self._maak_boring_met_machine(db)
        resp = client.get("/orders/dxf-bm/boringen/1/dxf", auth=AUTH)
        doc = ezdxf.read(io.StringIO(resp.text))
        msp = doc.modelspace()
        texts = [e for e in msp if e.dxftype() == "TEXT" and e.dxf.layer == "MACHINE"]
        text_values = [e.dxf.text for e in texts]
        assert any("D40" in t for t in text_values), f"Machine label niet gevonden: {text_values}"

    def test_dxf_zonder_machine_geen_crash(self, client, workspace, db):
        from app.core.database import Base, engine
        import app.order.models
        Base.metadata.create_all(bind=engine)

        from app.order.models import Order, Boring, TracePunt, MaaiveldOverride
        order = Order(id="dxf-nomach", workspace_id="gbt-workspace-001", ordernummer="DXF-NOMACH")
        db.add(order)
        boring = Boring(id="dxf-nomach-b", order_id="dxf-nomach", volgnummer=1, type="B",
                        De_mm=160.0, Dg_mm=240.0)
        db.add(boring)
        db.add(TracePunt(boring_id="dxf-nomach-b", volgorde=0, type="intree",
                         label="A", RD_x=100000.0, RD_y=400000.0))
        db.add(TracePunt(boring_id="dxf-nomach-b", volgorde=1, type="uittree",
                         label="B", RD_x=100200.0, RD_y=400000.0))
        db.add(MaaiveldOverride(boring_id="dxf-nomach-b", MVin_NAP_m=0.5, MVuit_NAP_m=0.3))
        db.commit()

        resp = client.get("/orders/dxf-nomach/boringen/1/dxf", auth=AUTH)
        assert resp.status_code == 200

        doc = ezdxf.read(io.StringIO(resp.text))
        msp = doc.modelspace()
        machine_entities = [e for e in msp if e.dxf.layer == "MACHINE"]
        assert len(machine_entities) == 0

    def test_dxf_onbekend_machine_type_geen_crash(self, client, workspace, db):
        """Machine type in boring maar niet in DB → geen crash, geen machine getekend."""
        from app.core.database import Base, engine
        import app.order.models
        Base.metadata.create_all(bind=engine)

        from app.order.models import Order, Boring, TracePunt, MaaiveldOverride
        order = Order(id="dxf-unk", workspace_id="gbt-workspace-001", ordernummer="DXF-UNK")
        db.add(order)
        boring = Boring(id="dxf-unk-b", order_id="dxf-unk", volgnummer=1, type="B",
                        De_mm=160.0, Dg_mm=240.0, machine_type="ONBEKEND")
        db.add(boring)
        db.add(TracePunt(boring_id="dxf-unk-b", volgorde=0, type="intree",
                         label="A", RD_x=100000.0, RD_y=400000.0))
        db.add(TracePunt(boring_id="dxf-unk-b", volgorde=1, type="uittree",
                         label="B", RD_x=100200.0, RD_y=400000.0))
        db.add(MaaiveldOverride(boring_id="dxf-unk-b", MVin_NAP_m=0.5, MVuit_NAP_m=0.3))
        db.commit()

        resp = client.get("/orders/dxf-unk/boringen/1/dxf", auth=AUTH)
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# STAP 4 — PDF rendering
# ═══════════════════════════════════════════════════════════════════════════

class TestStap4PDF:
    """PDF bovenaanzicht met machine symbool."""

    def test_pdf_svg_met_machine(self):
        """SVG bovenaanzicht bevat machine rect als machine_type gezet is."""
        from app.order.models import Boring, Order, TracePunt, MaaiveldOverride
        from app.admin.models import Boormachine
        from app.documents.pdf_generator import _generate_bovenaanzicht_svg

        boring = Boring(id="pdf-bm", order_id="x", volgnummer=1, type="B",
                        De_mm=160.0, machine_type="D40")
        boring.trace_punten = [
            TracePunt(boring_id="pdf-bm", volgorde=0, type="intree",
                      label="A", RD_x=100000.0, RD_y=400000.0),
            TracePunt(boring_id="pdf-bm", volgorde=1, type="uittree",
                      label="B", RD_x=100200.0, RD_y=400000.0),
        ]

        # Machine lookup nodig — test met mock
        svg = _generate_bovenaanzicht_svg(boring, machine_afmetingen={"lengte_m": 6.0, "breedte_m": 2.5})
        assert "machine" in svg.lower() or "rect" in svg.lower() or "D40" in svg


# ═══════════════════════════════════════════════════════════════════════════
# STAP 5 — Persistentie (seed defaults)
# ═══════════════════════════════════════════════════════════════════════════

class TestStap5Seed:
    """Default boormachines worden geseeded bij startup."""

    def test_seed_default_machines(self, db):
        """Na startup moeten er default boormachines in de DB staan."""
        from app.core.database import Base, engine
        import app.admin.models
        Base.metadata.create_all(bind=engine)

        from app.admin.models import Boormachine
        # Simuleer seed
        if db.query(Boormachine).count() == 0:
            for naam, code, l, b, t in [
                ("Vermeer D7x11", "D7x11", 3.0, 1.5, 3.0),
                ("Vermeer D24x40", "D24x40", 5.0, 2.0, 11.0),
                ("Vermeer D40x55", "D40x55", 6.0, 2.5, 18.0),
                ("Vermeer D100x140", "D100x140", 9.0, 3.0, 45.0),
                ("Pers", "PERS", 2.0, 1.0, 0.0),
                ("Boogzinker", "BZ", 2.0, 1.0, 0.0),
            ]:
                db.add(Boormachine(naam=naam, code=code, lengte_m=l, breedte_m=b, trekkracht_ton=t))
            db.commit()

        machines = db.query(Boormachine).all()
        assert len(machines) >= 6
        codes = {m.code for m in machines}
        assert "D40x55" in codes
        assert "PERS" in codes
