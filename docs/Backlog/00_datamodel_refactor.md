# Builder Task — Backlog 0: Datamodel Refactor Order → Boring[]
**HDD Ontwerp Platform · Fundament voor alle volgende features**
Versie: 1.0 | 2026-03-17

---

## Doel

Refactor het datamodel van 1-project-1-boring naar Order → Boring[]. Dit is het fundament voor cockpit, meerdere boringen per order, boringtypen B/N/Z/C, statusbeheer, en alle volgende backlog items.

**Database**: Schone start. Oude hdd.db verwijderen, nieuwe aanmaken. Geen datamigratie.

**Definitie of done**: Order aanmaken met meerdere boringen (B + Z), tracé per boring, brondata per boring, DXF + PDF genereren per boring met correcte bestandsnaam. Alle tests groen.

---

## Wat je NIET doet in deze taak

- Geen cockpit UI (dat is backlog 2)
- Geen KLIC parser (backlog 3)
- Geen werkplan generator (backlog 1)
- Geen boogzinker profielgeometrie (backlog 8) — type Z wordt aangemaakt maar profiel is nog handmatig
- Geen kaart-klik invoer (backlog 2) — handmatige RD-invoer blijft

---

## Stap 1 — Models: Order + Boring

### Bestanden

```
app/project/models.py → app/order/models.py (rename + rewrite)
app/order/__init__.py
app/core/models.py (workspace blijft)
```

### Order model

```python
class Order(Base):
    __tablename__ = "orders"

    id              = Column(String, primary_key=True, default=lambda: str(uuid4()))
    workspace_id    = Column(String, ForeignKey("workspaces.id"), nullable=False)
    ordernummer     = Column(String, nullable=False)       # "3D26V810"
    locatie         = Column(String)                        # "Velsen-Noord, Verkeersplein N197"
    klantcode       = Column(String)                        # "3D"
    opdrachtgever   = Column(String)                        # "3D-Drilling BV"
    status          = Column(String, default="order_received")
    # Enum: order_received / in_progress / delivered / waiting_for_approval / done / cancelled
    ontvangen_op    = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    deadline        = Column(DateTime, nullable=True)
    geleverd_op     = Column(DateTime, nullable=True)
    vergunning      = Column(String, default="-")           # P / W / R / -
    prio            = Column(Boolean, default=False)
    notitie         = Column(Text, nullable=True)
    tekenaar        = Column(String, default="martien")
    akkoord_contact = Column(String, nullable=True)         # "Michel Visser"
    # URLs
    google_maps_url     = Column(String, nullable=True)
    pdok_url            = Column(String, nullable=True)
    waterkering_url     = Column(String, nullable=True)
    oppervlaktewater_url = Column(String, nullable=True)
    peil_url            = Column(String, nullable=True)

    # Relaties
    boringen        = relationship("Boring", back_populates="order", cascade="all, delete-orphan")
    klic_uploads    = relationship("KLICUpload", back_populates="order", cascade="all, delete-orphan")
    ev_partijen     = relationship("EVPartij", back_populates="order", cascade="all, delete-orphan")
    email_contacten = relationship("EmailContact", back_populates="order", cascade="all, delete-orphan")
```

### Boring model

```python
class Boring(Base):
    __tablename__ = "boringen"

    id              = Column(String, primary_key=True, default=lambda: str(uuid4()))
    order_id        = Column(String, ForeignKey("orders.id"), nullable=False)
    volgnummer      = Column(Integer, nullable=False)       # 1, 2, 3...
    type            = Column(String, nullable=False)         # B / N / Z / C
    naam            = Column(String, nullable=True)          # "HDD29", "BZ2"
    # Leidingparameters (alleen B/N/Z, niet C)
    materiaal       = Column(String, default="PE100")
    SDR             = Column(Integer, default=11)
    De_mm           = Column(Float, default=160.0)
    dn_mm           = Column(Float, nullable=True)
    medium          = Column(String, default="Drukloos")
    Db_mm           = Column(Float, default=60.0)
    Dp_mm           = Column(Float, default=110.0)
    Dg_mm           = Column(Float, default=240.0)
    # Hoeken (alleen B/N)
    intreehoek_gr   = Column(Float, default=18.0)
    uittreehoek_gr  = Column(Float, default=22.0)
    # Boogzinker params (alleen Z)
    booghoek_gr     = Column(Float, nullable=True)          # 5 / 7.5 / 10
    stand           = Column(Integer, nullable=True)         # 1-10
    # Meta
    status          = Column(String, default="concept")
    aangemaakt_door = Column(String, nullable=True)
    aangemaakt_op   = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relaties
    order           = relationship("Order", back_populates="boringen")
    trace_punten    = relationship("TracePunt", back_populates="boring", order_by="TracePunt.volgorde", cascade="all, delete-orphan")
    maaiveld_override = relationship("MaaiveldOverride", back_populates="boring", uselist=False, cascade="all, delete-orphan")
    doorsneden      = relationship("Doorsnede", back_populates="boring", order_by="Doorsnede.volgorde", cascade="all, delete-orphan")
    berekening      = relationship("Berekening", back_populates="boring", uselist=False, cascade="all, delete-orphan")
    boring_klics    = relationship("BoringKLIC", back_populates="boring", cascade="all, delete-orphan")

    # Properties (zelfde als oude Project)
    @property
    def dn_berekend(self) -> float:
        return round(self.De_mm / self.SDR, 1)

    @property
    def dn_effectief(self) -> float:
        return self.dn_mm if self.dn_mm else self.dn_berekend

    @property
    def Di_mm(self) -> float:
        return round(self.De_mm - 2 * self.dn_effectief, 2)

    @property
    def intreehoek_pct(self) -> float:
        return round(math.tan(math.radians(self.intreehoek_gr)) * 100, 1)

    @property
    def uittreehoek_pct(self) -> float:
        return round(math.tan(math.radians(self.uittreehoek_gr)) * 100, 1)
```

### KLICUpload (op order-niveau + versioning)

```python
class KLICUpload(Base):
    __tablename__ = "klic_uploads"

    id              = Column(String, primary_key=True, default=lambda: str(uuid4()))
    order_id        = Column(String, ForeignKey("orders.id"), nullable=False)
    meldingnummer   = Column(String)                        # "26O0185752"
    versie          = Column(Integer, default=1)
    type            = Column(String, nullable=True)          # orientatie / graaf / hermelding
    bestandsnaam    = Column(String)
    bestandspad     = Column(String)
    upload_datum    = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    verwerkt        = Column(Boolean, default=False)
    aantal_leidingen  = Column(Integer, nullable=True)
    aantal_beheerders = Column(Integer, nullable=True)
    verwerk_fout    = Column(String, nullable=True)
    verwerkt_op     = Column(DateTime, nullable=True)

    order           = relationship("Order", back_populates="klic_uploads")
    boring_klics    = relationship("BoringKLIC", back_populates="klic_upload", cascade="all, delete-orphan")
    leidingen       = relationship("KLICLeiding", back_populates="klic_upload", cascade="all, delete-orphan")
```

### BoringKLIC (koppeltabel)

```python
class BoringKLIC(Base):
    __tablename__ = "boring_klics"

    boring_id       = Column(String, ForeignKey("boringen.id"), primary_key=True)
    klic_upload_id  = Column(String, ForeignKey("klic_uploads.id"), primary_key=True)

    boring          = relationship("Boring", back_populates="boring_klics")
    klic_upload     = relationship("KLICUpload", back_populates="boring_klics")
```

### EVPartij + EmailContact

```python
class EVPartij(Base):
    __tablename__ = "ev_partijen"

    id          = Column(String, primary_key=True, default=lambda: str(uuid4()))
    order_id    = Column(String, ForeignKey("orders.id"), nullable=False)
    naam        = Column(String)                            # "Liander: HS"
    volgorde    = Column(Integer)                            # 1-5

    order       = relationship("Order", back_populates="ev_partijen")


class EmailContact(Base):
    __tablename__ = "email_contacten"

    id          = Column(String, primary_key=True, default=lambda: str(uuid4()))
    order_id    = Column(String, ForeignKey("orders.id"), nullable=False)
    naam        = Column(String)                            # "Gem. Ermelo"
    volgorde    = Column(Integer)                            # 1-6

    order       = relationship("Order", back_populates="email_contacten")
```

### Bestaande models — foreign key wijziging

Deze models bestaan al maar krijgen `boring_id` i.p.v. `project_id`:

- `TracePunt.project_id` → `TracePunt.boring_id`
- `MaaiveldOverride.project_id` → `MaaiveldOverride.boring_id`
- `Doorsnede.project_id` → `Doorsnede.boring_id`
- `Berekening.project_id` → `Berekening.boring_id`
- `KLICLeiding.project_id` verwijderen (gaat via `klic_upload_id` → `KLICUpload.order_id`)

### Testcases stap 1

```
TC-model-A  init_db.py maakt alle tabellen aan zonder errors
TC-model-B  Order aanmaken met 1 Boring → opgeslagen in DB
TC-model-C  Order aanmaken met 3 Boringen (B + B + Z) → volgnummers correct
TC-model-D  Boring.dn_berekend: SDR=11, De=160 → 14.5
TC-model-E  Boring.Di_mm: SDR=11, De=160 → 131.0
TC-model-F  KLICUpload op order-niveau, koppelen aan boring via BoringKLIC
```

---

## Stap 2 — Seed data uitbreiden

### Bestanden

```
scripts/seed.py (uitbreiden)
```

### Nieuwe seed data

```python
KLANTCODES = [
    {"code": "3D", "naam": "3D-Drilling BV", "akkoord_contact": "Michel Visser"},
    {"code": "RD", "naam": "R&D Drilling", "akkoord_contact": "Marcel van Hoolwerff"},
    {"code": "IE", "naam": "Infra Elite", "akkoord_contact": "Erik Heijnekamp"},
    {"code": "KB", "naam": "Kappert Infra", "akkoord_contact": "Alice Kappert"},
    {"code": "BT", "naam": "BTL Drilling", "akkoord_contact": "Patricia"},
    {"code": "TM", "naam": "TM Infra"},
    {"code": "QG", "naam": "QG Infra"},
    {"code": "MM", "naam": "MM Infra"},
    {"code": "HS", "naam": "HS Infra"},
    {"code": "VB", "naam": "VB Infra"},
    {"code": "VG", "naam": "VG Infra"},
    {"code": "EN", "naam": "EN Infra"},
    {"code": "PZ", "naam": "PZ Infra"},
    {"code": "MT", "naam": "MT Infra"},
    {"code": "TI", "naam": "TI Infra"},
    {"code": "NR", "naam": "NR Infra"},
]
# NB: volledige namen opvragen bij Martien. Bovenstaande zijn placeholders.
```

Eisenprofielen: blijven ongewijzigd (5 stuks).

### Testcases stap 2

```
TC-seed-A  Seed draait zonder errors
TC-seed-B  ≥16 klantcodes aanwezig na seed
TC-seed-C  5 eisenprofielen aanwezig na seed
TC-seed-D  Seed twee keer draaien → geen duplicaten (idempotent)
TC-seed-E  Klantcode "3D" → akkoord_contact="Michel Visser"
```

---

## Stap 3 — Routes: Order CRUD

### Bestanden

```
app/project/router.py → app/order/router.py (rename + rewrite)
app/order/schemas.py (nieuw, optioneel voor validatie)
app/main.py (import aanpassen)
```

### Routes

```
GET  /                              → redirect naar /orders/
GET  /orders/                       → orderlijst
GET  /orders/nieuw                  → aanmaakformulier
POST /orders/nieuw                  → order + boringen opslaan
GET  /orders/{id}                   → orderdetail met boringen
POST /orders/{id}/update            → order bijwerken
GET  /orders/{id}/boringen/{volgnr} → boring detail (tracé/brondata/output)
```

### Testcases stap 3

```
TC-route-A  GET /orders/ met auth → 200, orderlijst
TC-route-B  GET /orders/ zonder auth → 401
TC-route-C  POST /orders/nieuw → order aangemaakt, redirect
TC-route-D  Order met 3 boringen → alle 3 zichtbaar op detail
TC-route-E  GET /orders/{id}/boringen/01 → boring detail
```

---

## Stap 4 — Templates: Order + Boring UI

### Bestanden

```
app/templates/project/ → app/templates/order/ (rename)
    list.html           → orderlijst
    create.html         → order + boringen aanmaken
    detail.html         → order met boring-overzicht
    boring_detail.html  → per boring: tracé/brondata/output tabs
app/templates/base.html (navigatie aanpassen)
```

### Testcases stap 4

```
TC-ui-A  Orderlijst toont ordernummer, klant, status, type badges
TC-ui-B  Aanmaakformulier: boringtype selectie (B/N/Z/C)
TC-ui-C  Orderdetail: boringen als rijen met volgnummer + type
TC-ui-D  Boring detail: tabs voor tracé, brondata, output
```

---

## Stap 5 — Tracé per boring

### Bestanden

```
app/order/router.py (trace routes toevoegen)
app/templates/order/trace.html (boring_id i.p.v. project_id)
static/js/map.js (ongewijzigd)
```

### Routes

```
GET  /orders/{id}/boringen/{volgnr}/trace      → tracé invoer + kaart
POST /orders/{id}/boringen/{volgnr}/trace/punt  → punt toevoegen
```

### Testcases stap 5

```
TC-trace-A  RD (103896.9, 489289.5) → WGS84 correct (HDD11 punt A)
TC-trace-B  Tracépunt toevoegen aan boring 01 → opgeslagen met boring_id
TC-trace-C  Boring 01 en 02 hebben eigen tracépunten (niet gedeeld)
```

---

## Stap 6 — Brondata per boring

### Bestanden

```
app/order/router.py (brondata routes)
app/templates/order/brondata.html
```

### Routes

```
GET  /orders/{id}/boringen/{volgnr}/brondata    → KLIC + overrides
POST /orders/{id}/boringen/{volgnr}/brondata    → opslaan
POST /orders/{id}/klic/upload                   → KLIC op order-niveau
POST /orders/{id}/boringen/{volgnr}/klic/koppel → boring koppelen aan KLIC
```

### Testcases stap 6

```
TC-bron-A  KLIC upload op order-niveau → opgeslagen
TC-bron-B  KLIC koppelen aan boring 01 → BoringKLIC record aangemaakt
TC-bron-C  Maaiveld per boring: MVin=+1.01, MVuit=+1.27
TC-bron-D  Doorsneden per boring: 6 stuks voor boring 01
TC-bron-E  Intrekkracht per boring: Ttot=30106 N
```

---

## Stap 7 — DXF + PDF per boring

### Bestanden

```
app/documents/dxf_generator.py (accepteert Boring i.p.v. Project)
app/documents/pdf_generator.py (accepteert Boring i.p.v. Project)
app/documents/router.py (routes per boring)
```

### Routes

```
GET  /orders/{id}/boringen/{volgnr}/dxf   → DXF download
GET  /orders/{id}/boringen/{volgnr}/pdf   → PDF download
```

### Bestandsnaam

```python
filename = f"{order.ordernummer}-{boring.volgnummer:02d}-rev.1.dxf"
# Voorbeeld: 3D26V810-01-rev.1.dxf
```

### Testcases stap 7

```
TC-dxf-A  DXF genereren voor boring → ezdxf parse zonder errors
TC-dxf-B  Alle 16 lagen aanwezig met juiste ACI-kleur
TC-dxf-C  Bestandsnaam: {ordernummer}-{volgnummer:02d}-rev.1.dxf
TC-dxf-D  BOORLIJN heeft entiteiten
TC-pdf-A  PDF genereren voor boring → geen WeasyPrint errors
TC-pdf-B  Titelblok: ordernummer + boring volgnummer correct
TC-pdf-C  Bestandsnaam: {ordernummer}-{volgnummer:02d}-rev.1.pdf
```

---

## Stap 8 — Alle tests groen

Alle oude tests aanpassen + nieuwe tests. Doel: ≥60 tests, allemaal groen.

Testgroepen:
```
test_core.py        → ongewijzigd (auth, config, seed)
test_order.py       → vervangt test_project.py
test_boring.py      → nieuw (meerdere boringen, typen)
test_trace.py       → boring_id i.p.v. project_id
test_brondata.py    → boring_id i.p.v. project_id
test_rules.py       → ongewijzigd
test_dxf.py         → boring i.p.v. project
test_pdf.py         → boring i.p.v. project
test_nav.py         → nieuwe routes /orders/...
test_ahn5.py        → boring_id i.p.v. project_id
```

---

## Bestandsconventies

```python
# Alle IDs: UUID4 als string
id = Column(String, primary_key=True, default=lambda: str(uuid4()))

# Alle datums: UTC
aangemaakt_op = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# Bestandsnamen
f"{order.ordernummer}-{boring.volgnummer:02d}-rev.{revisie}.dxf"

# Workspace op Order (niet op Boring — Boring erft via Order)
workspace_id = Column(String, ForeignKey("workspaces.id"))
```

---

## Wanneer klaar

Stap 8 groen = Backlog 0 done. Dan kan Backlog 1 (werkplan) of Backlog 2 (cockpit) starten.
