# Builder Task — Walking Skeleton
**HDD Ontwerp Platform · Eerste oplevering**
Versie: 1.0 | 2026-03-14

---

## Doel

Bouw een volledig werkend end-to-end systeem. Martien kan er direct mee werken. Complexe stappen zijn handmatig invulbaar (overrides). Alle output — DWG en PDF — wordt gegenereerd.

**Definitie of done:** Martien logt in, maakt een project aan, voert een tracé in, uploadt een KLIC-bestand, vult overrides in, en downloadt een DWG + PDF tekening.

---

## Wat je NIET bouwt in deze taak

Alles wat niet in de onderstaande modulelijst staat is buiten scope. Signaleer als je in de verleiding komt om iets extra's toe te voegen.

- Geen KLIC GML parser (placeholder leidingen)
- Geen AHN5 API (handmatig NAP invoeren)
- Geen GEF parser (dropdown grondtype)
- Geen boorprofiel geometrie algoritme (handmatige hoeken)
- Geen NEN 3651 berekening (handmatig intrekkracht invoeren)
- Geen Google Drive API (downloadknop)
- Geen Docker, geen PostgreSQL, geen React, geen JWT

---

## Stack

```
Python FastAPI
SQLite + SQLAlchemy (bestand: hdd.db)
Jinja2 templates (server-side HTML)
HTMX (formulieren zonder pagina-reload)
Alpine.js (kleine client-side interacties)
Leaflet + OpenStreetMap (kaart)
pyproj (RD↔WGS84)
WeasyPrint (PDF)
ezdxf (DXF)
FastAPI HTTPBasic (.env wachtwoorden)
Railway nixpacks autodeploy
```

---

## Modules — bouw in deze volgorde

### Module 1 — Core (auth + config + database)

**Bestanden:**
```
app/core/config.py
app/core/database.py
app/core/auth.py
scripts/init_db.py
scripts/seed.py
.env.example
requirements.txt
```

**Config (`app/core/config.py`):**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ENV: str = "development"
    DATABASE_URL: str = "sqlite:///./hdd.db"
    USER_MARTIEN_PASSWORD: str
    USER_VISSER_PASSWORD: str
    USER_TEST_PASSWORD: str = ""
    ANTHROPIC_API_KEY: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
```

**Auth (`app/core/auth.py`):**
```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

security = HTTPBasic()

def get_users():
    users = {
        "martien": settings.USER_MARTIEN_PASSWORD,
        "visser":  settings.USER_VISSER_PASSWORD,
    }
    if settings.ENV == "development" and settings.USER_TEST_PASSWORD:
        users["test"] = settings.USER_TEST_PASSWORD
    return users

def get_current_user(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    users = get_users()
    password = users.get(credentials.username, "")
    if not password or not secrets.compare_digest(
        credentials.password.encode(), password.encode()
    ):
        raise HTTPException(
            status_code=401,
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
```

**Database (`app/core/database.py`):**
SQLAlchemy + SQLite. `Base`, `engine`, `SessionLocal`, `get_db` dependency.

**Seed (`scripts/seed.py`):**
Maakt aan:
- Eén Workspace: `naam="GestuurdeBoringTekening"`, `slug="gbt"`
- Vijf eisenprofielen (zie CLAUDE.md sectie 10)

**Testcases:**
```
TC-core-A  Settings laden uit .env → geen errors
TC-core-B  Auth correct wachtwoord → 200
TC-core-C  Auth fout wachtwoord → 401
TC-core-D  Test-user alleen in ENV=development
TC-core-E  Seed draait twee keer zonder errors (idempotent)
```

---

### Module 2 — Project CRUD

**Bestanden:**
```
app/project/models.py
app/project/schemas.py
app/project/router.py
app/templates/project/
    list.html
    create.html
    detail.html
```

**Model (`app/project/models.py`):**
```python
class Project(Base):
    __tablename__ = "projects"
    id              = Column(String, primary_key=True, default=lambda: str(uuid4()))
    workspace_id    = Column(String, ForeignKey("workspaces.id"))
    naam            = Column(String, nullable=False)
    opdrachtgever   = Column(String)
    ordernummer     = Column(String)
    # Leidingparameters
    materiaal       = Column(String, default="PE100")
    SDR             = Column(Integer, default=11)
    De_mm           = Column(Float, default=160.0)
    dn_mm           = Column(Float)          # auto: De/SDR, overschrijfbaar
    medium          = Column(String, default="Drukloos")
    Db_mm           = Column(Float, default=60.0)   # boorstang
    Dp_mm           = Column(Float, default=110.0)  # pilotboorkop
    Dg_mm           = Column(Float, default=240.0)  # ruimer
    # Meta
    status          = Column(String, default="concept")
    aangemaakt_door = Column(String)
    aangemaakt_op   = Column(DateTime, default=datetime.utcnow)
```

**Afgeleide leidingproperties (berekend, niet opgeslagen):**
```python
@property
def dn_berekend(self) -> float:
    return round(self.De_mm / self.SDR, 1)

@property
def Di_mm(self) -> float:
    dn = self.dn_mm or self.dn_berekend
    return self.De_mm - 2 * dn
```

**Routes:**
```
GET  /                      → projectenlijst (Jinja2)
GET  /projecten/nieuw       → aanmaakformulier
POST /projecten/nieuw       → project opslaan + redirect naar detail
GET  /projecten/{id}        → projectdetail
POST /projecten/{id}/update → project bijwerken
```

**Testcases:**
```
TC-proj-A  Project aanmaken → opgeslagen in DB, redirect naar detail
TC-proj-B  SDR=11, De=160 → dn_berekend=14.5, Di=131.0
TC-proj-C  SDR=11, De=160 (HDD11) → dn=14.6 (conform BerekeningHDD11 p.5)
TC-proj-D  Verplicht veld 'naam' leeg → validatiefout
TC-proj-E  Projectenlijst toont alle projecten van workspace
```

---

### Module 3 — Tracé (locatie + tussenpunten)

**Bestanden:**
```
app/project/models.py      (TracePunt toevoegen)
app/project/router.py      (trace routes)
app/templates/project/trace.html
static/js/map.js           (Leaflet kaart)
```

**Model TracePunt:**
```python
class TracePunt(Base):
    __tablename__ = "trace_punten"
    id          = Column(String, primary_key=True, default=lambda: str(uuid4()))
    project_id  = Column(String, ForeignKey("projects.id"))
    volgorde    = Column(Integer, nullable=False)
    type        = Column(String)    # "intree" / "tussenpunt" / "uittree"
    RD_x        = Column(Float)     # RD New x (m)
    RD_y        = Column(Float)     # RD New y (m)
    Rh_m        = Column(Float)     # horizontale boogstraal (alleen tussenpunten)
    label       = Column(String)    # bijv. "A", "B", "Tv1"
```

**UI:**
- Formulier: RD_x / RD_y invoeren per punt (primair)
- Leaflet kaart naast formulier: toont ingevoerde punten als oriëntatie
- RD→WGS84 conversie via pyproj voor kaartweergave
- Tussenpunten toevoegen/verwijderen met Rh per segment
- Intreehoek + uittreehoek invoeren (in graden)

**Pyproj conversie:**
```python
from pyproj import Transformer

_rd_to_wgs84 = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
_wgs84_to_rd = Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)

def rd_to_wgs84(x: float, y: float) -> tuple[float, float]:
    lon, lat = _rd_to_wgs84.transform(x, y)
    return lat, lon  # Leaflet wil (lat, lon)
```

**Testcases:**
```
TC-trace-A  RD (103896.9, 489289.5) → WGS84 correct (HDD11 punt A)
TC-trace-B  Alle 8 HDD11 GPS punten → correcte WGS84 (±1cm afwijking)
TC-trace-C  Tussenpunt aanmaken met Rh=150m → opgeslagen
TC-trace-D  Volgorde behouden na toevoegen/verwijderen punt
TC-trace-E  HDD28 sensorpunten Tv1(105315,498805) → kaart op juiste locatie
```

---

### Module 4 — Brondata (overrides)

**Bestanden:**
```
app/project/models.py      (MaaiveldOverride, KLICUpload, Doorsnede)
app/project/router.py      (brondata routes)
app/templates/project/brondata.html
```

**KLIC upload (skeleton — geen parsing):**
```python
class KLICUpload(Base):
    __tablename__ = "klic_uploads"
    id          = Column(String, primary_key=True, default=lambda: str(uuid4()))
    project_id  = Column(String, ForeignKey("projects.id"))
    bestandsnaam = Column(String)
    bestandspad  = Column(String)
    upload_datum = Column(DateTime, default=datetime.utcnow)
    verwerkt     = Column(Boolean, default=False)
    # Skeleton: bestand opslaan, geen GML parsing
    # Backlog 1: KLIC IMKL 2.0 parser
```

**Maaiveld (handmatig):**
```python
class MaaiveldOverride(Base):
    __tablename__ = "maaiveld_overrides"
    id          = Column(String, primary_key=True, default=lambda: str(uuid4()))
    project_id  = Column(String, ForeignKey("projects.id"))
    MVin_NAP_m  = Column(Float)     # maaiveld intrede t.o.v. NAP
    MVuit_NAP_m = Column(Float)     # maaiveld uittrede t.o.v. NAP
    bron        = Column(String, default="handmatig")  # later: "AHN5"
    # Backlog 2: AHN5 PDOK WCS automatisch ophalen
```

**Doorsneden (handmatig, 6 stuks voor HDD11):**
```python
class Doorsnede(Base):
    __tablename__ = "doorsneden"
    id              = Column(String, primary_key=True, default=lambda: str(uuid4()))
    project_id      = Column(String, ForeignKey("projects.id"))
    volgorde        = Column(Integer)
    afstand_m       = Column(Float)     # horizontale afstand vanaf intrede
    NAP_m           = Column(Float)     # hart boring t.o.v. NAP
    grondtype       = Column(String, default="Zand")  # Zand/Klei/Veen
    GWS_m           = Column(Float)     # grondwater t.o.v. maaiveld
    phi_graden      = Column(Float, default=35.0)
    E_modulus       = Column(Float, default=75.0)
    override_vlag   = Column(Boolean, default=True)
    # Backlog 9: GEF/CPT parser vervangt handmatige invoer
```

**Intrekkracht override:**
```python
class Berekening(Base):
    __tablename__ = "berekeningen"
    id          = Column(String, primary_key=True, default=lambda: str(uuid4()))
    project_id  = Column(String, ForeignKey("projects.id"))
    Ttot_N      = Column(Float)     # handmatig uit Sigma
    bron        = Column(String, default="sigma_override")
    # Backlog 11: NEN 3651 berekening
```

**Testcases:**
```
TC-bron-A  KLIC ZIP uploaden → bestand opgeslagen, verwerkt=False
TC-bron-B  MVin=+1.01 MVuit=+1.27 (HDD11) → opgeslagen, bron=handmatig
TC-bron-C  6 doorsneden HDD11 invoeren → volgorde correct
TC-bron-D  Ttot=30106 N (HDD11) → opgeslagen als override
```

---

### Module 5 — Eisenprofiel

**Bestanden:**
```
app/rules/models.py
app/rules/router.py
app/templates/rules/select.html
```

**Model:**
```python
class EisenProfiel(Base):
    __tablename__ = "eisenprofielen"
    id              = Column(String, primary_key=True, default=lambda: str(uuid4()))
    workspace_id    = Column(String, nullable=True)  # null = globaal
    naam            = Column(String)
    dekking_weg_m   = Column(Float)
    dekking_water_m = Column(Float)
    Rmin_m          = Column(Float)
    versie_datum    = Column(String)    # tonen in UI

class ProjectEisenProfiel(Base):
    __tablename__ = "project_eisenprofielen"
    project_id      = Column(String, ForeignKey("projects.id"), primary_key=True)
    eisenprofiel_id = Column(String, ForeignKey("eisenprofielen.id"))
    override_eisen  = Column(JSON)      # voor vergunningspecifieke afwijkingen
```

**Seed data (via scripts/seed.py):**
```python
[
    {"naam": "RWS Rijksweg",          "dekking_weg": 3.0, "dekking_water": 5.0,  "Rmin": 150, "versie": "NEN 3651:2020"},
    {"naam": "Waterschap waterkering","dekking_weg": 5.0, "dekking_water": 10.0, "Rmin": 200, "versie": "NEN 3651:2020"},
    {"naam": "Provincie",             "dekking_weg": 2.0, "dekking_water": 3.0,  "Rmin": 120, "versie": "NEN 3651:2020"},
    {"naam": "Gemeente",              "dekking_weg": 1.2, "dekking_water": 1.5,  "Rmin": 100, "versie": "NEN 3651:2020"},
    {"naam": "ProRail spoor",         "dekking_weg": 4.0, "dekking_water": 6.0,  "Rmin": 150, "versie": "NEN 3651:2020"},
]
```

**Testcases:**
```
TC-rules-A  Seed draait → 5 eisenprofielen aanwezig
TC-rules-B  RWS selecteren → dekking_weg=3.0, Rmin=150
TC-rules-C  Override: vergunning eist 3.5m → opgeslagen in override_eisen
```

---

### Module 6 — DXF generatie

**Bestanden:**
```
app/documents/dxf_generator.py
app/documents/router.py
```

**Laagnamen — exact conform HDD28 (gevalideerd):**
```python
LAYERS = {
    "BOORLIJN":         {"color": 1,   "linetype": "Continuous"},
    "BOORGAT":          {"color": 5,   "linetype": "DASHDOT"},
    "MAAIVELD":         {"color": 122, "linetype": "Continuous"},
    "MAATVOERING":      {"color": 170, "linetype": "Continuous"},
    "MAATVOERING-GRIJS":{"color": 251, "linetype": "Continuous"},
    "ATTRIBUTEN":       {"color": 252, "linetype": "Continuous"},
    "TITELBLOK_TEKST":  {"color": 7,   "linetype": "Continuous"},
    "LAAGSPANNING":     {"color": 190, "linetype": "KL-LS-N"},
    "MIDDENSPANNING":   {"color": 130, "linetype": "KL-MS-N"},
    "HOOGSPANNING":     {"color": 10,  "linetype": "KL-HS-N"},
    "LD-GAS":           {"color": 50,  "linetype": "KL-GAS-LD-N"},
    "WATERLEIDING":     {"color": 170, "linetype": "KL-WATER-N"},
    "RIOOL-VRIJVERVAL": {"color": 210, "linetype": "RI-OVERIG"},
    "PERSRIOOL":        {"color": 210, "linetype": "RI-PERS"},
    "KADASTER":         {"color": 150, "linetype": "KG-PERCEEL"},
    "WEGDEK":           {"color": 252, "linetype": "Continuous"},
}

NLCS_LINETYPES = {
    "KL-LS-N":     "ELECTRA LAAGSPANNING VOLGENS NLCS",
    "KL-MS-N":     "ELECTRA MIDDENSPANNING VOLGENS NLCS",
    "KL-HS-N":     "ELECTRA HOOGSPANNING VOLGENS NLCS",
    "KL-GAS-LD-N": "GAS LAGEDRUK VOLGENS NLCS",
    "KL-WATER-N":  "WATERLEIDING VOLGENS NLCS",
    "RI-OVERIG":   "OVERIGE LEIDINGEN",
    "RI-PERS":     "PERSLEIDING",
    "KG-PERCEEL":  "KADASTRALE PERCEELGRENS",
}
```

**DXF output structuur (skeleton):**
```python
def generate_dxf(project: Project, boring: Boring) -> bytes:
    doc = ezdxf.new("R2013")
    msp = doc.modelspace()

    # 1. Lagen aanmaken met NLCS lijntype-definities
    _setup_layers(doc)

    # 2. Boorlijn: LWPolyline van tracépunten op laag BOORLIJN
    #    (skeleton: rechte lijn A→B, geen booggeometrie)
    _draw_boorlijn(msp, project)

    # 3. Boorgat: 2 cirkels op laag BOORGAT
    #    r1 = Dg_mm/2 (boorgat), r2 = De_mm/2 (buis)
    _draw_boorgat(msp, project)

    # 4. Sensorpunt labels op laag ATTRIBUTEN
    #    TEXT entiteiten: "A", "Tv1"... bij RD-coördinaten
    _draw_sensorpunten(msp, boring)

    # 5. Titelblok tekst op laag TITELBLOK_TEKST
    _draw_titelblok(msp, project)

    return _to_bytes(doc)
```

**Testcases:**
```
TC-dxf-A  DXF genereren → ezdxf parse zonder errors
TC-dxf-B  Alle 15 lagen aanwezig met juiste ACI-kleur
TC-dxf-C  NLCS lijntype-definities aanwezig in DXF
TC-dxf-D  BOORLIJN laag heeft entiteiten
TC-dxf-E  BOORGAT: r1=120mm (Dg=240), r2=80mm (De=160) voor HDD11
TC-dxf-F  Sensorpunt label "A" aanwezig op ATTRIBUTEN laag
TC-dxf-G  Bestandsversie = R2013 (AC1027)
```

---

### Module 7 — PDF generatie

**Bestanden:**
```
app/documents/pdf_generator.py
app/templates/documents/
    tekening.html       (WeasyPrint template)
    titelblok.html
    situatie.html
    profiel.html
    doorsnede.html
static/css/tekening.css
static/img/
    Logo3D.jpg
    Logo_Liander.png
    Mook_BV.jpg
```

**Verplichte elementen (bevestigd door Martien):**
```
Bovenaanzicht       schaal 1:4000, Noorden boven, statische kaart
Situatietekening    schaal 1:250, NLCS-kleuren K&L, tracé A→B
Lengteprofiel       schaal 1:250 op NAP, sensorpunt maatvoering
Doorsnede boorgat   Dg=1.5×De enkelbuis / 1.25×omschrijvende cirkel bundel
GPS punten          RD-coördinaten per sensorpunt (label: Tv1/Tv2/Th1...)
Hoeken              intree ° en % · uittree ° en %
Titelblok           project · schaal · datum · getekend · akkoord · revisietabel
Logo's              Logo3D.jpg + opdrachtgever logo (per project)
OPMERKINGEN         KLIC-disclaimer + CROW 96b + walk-over meetsysteem
```

**GPS punten tabel (in PDF):**
```
A:   103896.9  489289.5
Tv1: 103916.4  489284.1
...
B:   104118.8  489243.7
```

**Doorsnede boorgat formule:**
```python
r_boorgat = project.Dg_mm / 2        # 1.5 × De voor enkelbuis
r_buis    = project.De_mm / 2
# SVG cirkel inline in Jinja2 template
```

**Testcases:**
```
TC-pdf-A  PDF genereren → geen WeasyPrint errors
TC-pdf-B  Titelblok: project=HDD11, getekend=M.Luijben, akkoord=M.Visser
TC-pdf-C  GPS punten: A=(103896.9, 489289.5) correct in tabel
TC-pdf-D  Doorsnede boorgat: r_boorgat=120mm, r_buis=80mm (HDD11)
TC-pdf-E  Intreehoek 18° en 32% correct weergegeven
TC-pdf-F  KLIC-disclaimer aanwezig in OPMERKINGEN
```

---

### Module 8 — Download + navigatie

**Bestanden:**
```
app/main.py
app/templates/base.html
app/templates/project/detail.html   (download knoppen)
```

**Routes (overzicht alle routes):**
```
GET  /                          → projectenlijst
GET  /projecten/nieuw           → formulier
POST /projecten/nieuw           → aanmaken
GET  /projecten/{id}            → detail + voortgang
GET  /projecten/{id}/trace      → tracé invoer + kaart
GET  /projecten/{id}/brondata   → KLIC upload + overrides
GET  /projecten/{id}/eisen      → eisenprofiel selectie
GET  /projecten/{id}/review     → kaart + profiel overzicht
GET  /projecten/{id}/output     → download pagina
GET  /projecten/{id}/dxf        → DXF download (response)
GET  /projecten/{id}/pdf        → PDF download (response)
```

**Download response:**
```python
@router.get("/{id}/dxf")
def download_dxf(id: str, user=Depends(get_current_user), db=Depends(get_db)):
    project = get_project_or_404(id, db)
    dxf_bytes = generate_dxf(project)
    filename = f"{project.ordernummer}-rev.1.dxf"
    return Response(
        content=dxf_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
```

**Testcases:**
```
TC-nav-A  GET / zonder auth → 401
TC-nav-B  GET / met auth → 200, projectenlijst
TC-nav-C  Download DXF → Content-Disposition header aanwezig
TC-nav-D  Download PDF → Content-Type: application/pdf
TC-nav-E  Projectdetail toont status van alle stappen (ingevuld/leeg)
```

---

## Volledigheidscheck walking skeleton

Na alle modules moet het volgende werken:

```
✓ Martien logt in op http://localhost:8000
✓ Maakt project aan: "HDD11 Haarlem Kennemerplein", ordernr "3D25V700"
✓ Voert tracépunten in: A=(103896.9, 489289.5) ... B=(104118.8, 489243.7)
✓ Uploadt KLIC ZIP (wordt opgeslagen, niet geparsed)
✓ Vult in: MVin=+1.01m NAP, MVuit=+1.27m NAP
✓ Vult in: grondtype=Zand, Ttot=30106 N
✓ Selecteert eisenprofiel: Gemeente
✓ Downloadt DXF → opent in ezdxf zonder errors, alle lagen aanwezig
✓ Downloadt PDF → titelblok correct, GPS punten correct, doorsnede aanwezig
```

---

## Bestandsconventies

```python
# Alle IDs: UUID4 als string
id = Column(String, primary_key=True, default=lambda: str(uuid4()))

# Alle datums: UTC
aangemaakt_op = Column(DateTime, default=datetime.utcnow)

# Override velden: altijd met bron en datum
bron    = Column(String)    # "handmatig" / "AHN5" / "sigma_override" / "platform"
override_datum = Column(DateTime)

# Workspace op alle entiteiten
workspace_id = Column(String, ForeignKey("workspaces.id"))
```

---

## Wanneer klaar

Vraag akkoord van de Architect Agent wanneer:
1. Alle testcases groen zijn
2. De volledigheidscheck hierboven werkt met HDD11 testdata
3. DXF geopend in ezdxf zonder errors
4. PDF gegenereerd zonder WeasyPrint errors

Dan pas beginnen aan backlog item 1 (KLIC IMKL 2.0 parser).
