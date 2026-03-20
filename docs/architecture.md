# Architectuur — HDD Ontwerp Platform

## 1. Wat is dit project

Het HDD Ontwerp Platform is een webapplicatie voor het ontwerpen en beheren van gestuurde boringen (Horizontal Directional Drilling). Het platform vervangt losse Excel-sheets en handmatige workflows door een centraal systeem waarin orders, boringen, KLIC-data, trace-ontwerpen, documenten en berekeningen worden beheerd.

Gebruikers (tekenaars/projectleiders) werken via een browser-interface. Het systeem genereert DXF-tekeningen, PDF-rapporten en werkplannen.

---

## 2. Tech stack

| Laag | Technologie |
|------|-------------|
| Backend | FastAPI (Python 3.12) |
| Templates | Jinja2 + HTMX |
| Database | SQLite via SQLAlchemy 2.0 |
| Migraties | Alembic |
| Geo | pyproj, Shapely (RD/WGS84 transformaties) |
| CAD export | ezdxf (DXF generatie) |
| PDF | python-docx (Word/PDF generatie) |
| Excel import | openpyxl |
| KLIC parsing | lxml (XML/GML uit KLIC-leveringen) |
| AI assist | Anthropic API (Claude) |
| Auth | HTTP Basic Authentication |
| Hosting | Railway (Nixpacks) |

---

## 3. Deployment

### Railway (productie)

Deployment gaat via `git push` naar de gekoppelde Railway repository. Railway bouwt automatisch via Nixpacks.

**Start commando** (uit `railway.json`):
```
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Healthcheck**: `GET /health` (timeout 300s)

**Restart policy**: ON_FAILURE, max 3 retries

### Environment variabelen

| Variabele | Beschrijving |
|-----------|-------------|
| `ENV` | `development` of `production` |
| `DATABASE_URL` | SQLite pad, bijv. `sqlite:///./hdd.db` of `sqlite:////data/hdd.db` (Railway volume) |
| `USER_MARTIEN_PASSWORD` | Wachtwoord gebruiker martien |
| `USER_VISSER_PASSWORD` | Wachtwoord gebruiker visser |
| `USER_TEST_PASSWORD` | Wachtwoord testgebruiker (alleen in development) |
| `ANTHROPIC_API_KEY` | API key voor Claude AI-assistentie |

### Lokaal draaien

```bash
cp .env.example .env        # vul wachtwoorden in
pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

## 4. Projectstructuur

```
hdd-app/
├── app/
│   ├── main.py              # FastAPI app, routers, startup
│   ├── core/
│   │   ├── config.py        # Settings (pydantic-settings, .env)
│   │   ├── database.py      # SQLAlchemy engine, session, Base
│   │   ├── auth.py          # HTTP Basic auth
│   │   ├── dependencies.py  # Gedeelde dependencies (fetch_order, fetch_boring, etc.)
│   │   └── models.py        # Workspace model
│   ├── order/
│   │   ├── router.py        # Alle order/boring endpoints (/orders/...)
│   │   ├── models.py        # Order, Boring, TracePunt, KLICUpload, etc.
│   │   ├── klantcodes.py    # Klantcodes, statussen, boring types (dropdown data)
│   │   └── import_excel.py  # Excel import logica
│   ├── project/
│   │   ├── router.py        # Legacy project endpoints (/api/v1/projecten/...)
│   │   └── models.py        # Legacy Project model
│   ├── documents/
│   │   ├── router.py        # DXF, PDF, werkplan download endpoints
│   │   ├── dxf_generator.py # DXF tekening generatie
│   │   ├── pdf_generator.py # PDF rapport generatie
│   │   └── werkplan_generator.py  # Werkplan generatie
│   ├── geo/                 # Geo-functies (AHN5 maaiveld, PDOK URLs, waterschap)
│   ├── calculations/        # Technische berekeningen (intrekkracht, etc.)
│   ├── design/              # Ontwerp-logica
│   ├── rules/
│   │   └── models.py        # EisenProfiel, ProjectEisenProfiel
│   ├── ai_assist/           # Claude AI integratie
│   ├── drive/               # Bestandsbeheer
│   └── templates/           # Jinja2 HTML templates
├── static/                  # CSS, JS, afbeeldingen
├── alembic/                 # Database migraties
├── scripts/                 # Hulpscripts
├── tests/                   # Pytest tests
├── werkplan/                # Werkplan templates/assets
├── docs/                    # Documentatie
├── requirements.txt
├── railway.json             # Railway deployment config
├── Procfile                 # Alternatief start commando
└── alembic.ini              # Alembic configuratie
```

---

## 5. Datamodel

### Kernobjecten en relaties

```
Workspace (1)
  └── Order (n)
        ├── Boring (n)
        │     ├── TracePunt (n)         — punten van het boortrace (intree/tussenpunt/uittree)
        │     ├── MaaiveldOverride (1)  — handmatige/AHN5 maaiveld correcties
        │     ├── Doorsnede (n)         — grondopbouw doorsneden langs het trace
        │     ├── Berekening (1)        — intrekkracht berekening resultaat
        │     ├── AsBuiltPunt (n)       — werkelijke meetpunten na uitvoering
        │     ├── WerkplanAfbeelding (n)— luchtfoto's, KLIC screenshots, etc.
        │     └── BoringKLIC (n:m)      — koppeling boring ↔ KLIC upload
        ├── KLICUpload (n)
        │     ├── KLICLeiding (n)       — geparsede leidingen uit KLIC levering
        │     └── BoringKLIC (n:m)
        ├── EVPartij (n)               — eisvoorzorgsmaatregelen partijen
        ├── EVZone (n)                 — EV zones uit KLIC
        └── EmailContact (n)          — contactpersonen per order
```

### Order statussen

| Status | Label |
|--------|-------|
| `order_received` | Ontvangen |
| `in_progress` | In uitvoering |
| `delivered` | Geleverd |
| `waiting_for_approval` | Wacht op akkoord |
| `done` | Afgerond |
| `cancelled` | Geannuleerd |

### Boring types

| Code | Type |
|------|------|
| `B` | Gestuurde boring |
| `N` | Nano boring |
| `Z` | Boogzinker (BZ) |
| `C` | Calculatie (Sigma) |

### Legacy: Project

Het `Project` model (in `app/project/models.py`) is de oude structuur. Nieuwe functionaliteit gebruikt het `Order → Boring` model. Project-routes staan onder `/api/v1/projecten/` en blijven beschikbaar voor backward compatibility.

---

## 6. Routes overzicht

### Orders (`/orders`)

| Method | Route | Beschrijving |
|--------|-------|-------------|
| GET | `/orders/` | Orderlijst (dashboard) |
| GET | `/orders/export/csv` | CSV export van alle orders |
| GET | `/orders/statusmail` | Statusmail overzicht |
| GET | `/orders/nieuw` | Nieuwe order formulier |
| POST | `/orders/nieuw` | Order aanmaken |
| GET | `/orders/import` | Excel import pagina |
| POST | `/orders/import` | Excel import uitvoeren |
| GET | `/orders/{id}` | Order detail |
| POST | `/orders/{id}/update` | Order bijwerken |
| POST | `/orders/{id}/klic` | KLIC upload voor order |

### Boringen (`/orders/{id}/boringen/{volgnr}`)

| Method | Route | Beschrijving |
|--------|-------|-------------|
| GET | `.../boringen/{volgnr}` | Boring detail |
| POST | `.../boringen/{volgnr}/update` | Boring bijwerken |
| GET/POST | `.../boringen/{volgnr}/trace` | Trace punten beheren |
| GET | `.../boringen/{volgnr}/brondata` | Brondata overzicht (maaiveld, KLIC, doorsneden) |
| POST | `.../boringen/{volgnr}/maaiveld` | Maaiveld handmatig instellen |
| POST | `.../boringen/{volgnr}/maaiveld/ahn5` | Maaiveld ophalen via AHN5 |
| POST | `.../boringen/{volgnr}/doorsneden` | Doorsneden opslaan |
| POST | `.../boringen/{volgnr}/intrekkracht` | Intrekkracht berekenen |
| GET | `.../boringen/{volgnr}/sonderingen` | Sonderingen overzicht |
| GET/POST | `.../boringen/{volgnr}/asbuilt` | As-built punten |
| GET | `.../boringen/{volgnr}/vergunning` | Vergunning pagina |
| GET | `.../boringen/{volgnr}/varianten` | Trace varianten |
| POST | `.../boringen/{volgnr}/varianten/nieuw` | Nieuwe variant |
| POST | `.../boringen/{volgnr}/varianten/{vnr}/verwijder` | Variant verwijderen |
| GET | `.../boringen/{volgnr}/sleufloze` | Sleufloze technieken |
| GET | `.../boringen/{volgnr}/gwsw` | GWSW data |
| GET | `.../boringen/{volgnr}/topotijdreis` | Topotijdreis |
| GET | `.../boringen/{volgnr}/conflictcheck` | Conflict check |
| GET | `.../boringen/{volgnr}/dxf` | DXF download |
| GET | `.../boringen/{volgnr}/pdf` | PDF download |
| POST | `.../boringen/{volgnr}/werkplan-afbeelding` | Werkplan afbeelding uploaden |
| POST | `.../boringen/{volgnr}/werkplan-afbeelding/{id}/delete` | Afbeelding verwijderen |

### Documenten (`/api/v1`)

| Method | Route | Beschrijving |
|--------|-------|-------------|
| GET | `/api/v1/projecten/{id}/dxf` | Legacy DXF download |
| GET | `/api/v1/projecten/{id}/pdf` | Legacy PDF download |
| GET | `/api/v1/orders/{id}/boringen/{volgnr}/werkplan` | Werkplan preview |
| POST | `/api/v1/orders/{id}/boringen/{volgnr}/werkplan` | Werkplan genereren |

### Projecten — legacy (`/api/v1/projecten`)

| Method | Route | Beschrijving |
|--------|-------|-------------|
| GET | `/api/v1/` | Projectenlijst |
| GET/POST | `/api/v1/projecten/nieuw` | Project aanmaken |
| GET | `/api/v1/projecten/{id}` | Project detail |
| POST | `/api/v1/projecten/{id}/update` | Project bijwerken |
| GET/POST | `/api/v1/projecten/{id}/trace` | Trace beheren |
| GET | `/api/v1/projecten/{id}/brondata` | Brondata |
| POST | `/api/v1/projecten/{id}/maaiveld` | Maaiveld |
| POST | `/api/v1/projecten/{id}/maaiveld/ahn5` | AHN5 ophalen |
| POST | `/api/v1/projecten/{id}/klic` | KLIC upload |
| POST | `/api/v1/projecten/{id}/klic/{uid}/verwerken` | KLIC verwerken |
| GET | `/api/v1/projecten/{id}/klic/status` | KLIC status |
| POST | `/api/v1/projecten/{id}/doorsneden` | Doorsneden |
| POST | `/api/v1/projecten/{id}/intrekkracht` | Intrekkracht |
| GET/POST | `/api/v1/projecten/{id}/eisen` | Eisenprofiel |
| GET | `/api/v1/projecten/{id}/review` | Review |
| GET | `/api/v1/projecten/{id}/output` | Output |

### Overig

| Method | Route | Beschrijving |
|--------|-------|-------------|
| GET | `/` | Redirect naar `/orders/` |
| GET | `/health` | Healthcheck |
| GET | `/orders/{id}/factuur` | Factuur overzicht |

---

## 7. Excel import

### Hoe het werkt

1. Ga naar `/orders/import`
2. Upload een Excel-bestand (`.xlsx`) met een sheet genaamd **"Vergunning"**
3. Optioneel: vink "Wissen" aan om alle bestaande data te verwijderen voor de import

### Sheet formaat (Vergunning)

Rij 2 bevat headers, data begint bij rij 3:

| Kolom | Veld |
|-------|------|
| A | Datum ontvangen |
| B | Ordernaam (ordernummer) |
| C | Klantcode |
| D | Status (bijv. "Order received", "In progress") |
| E | Deadline |
| F | Leverdatum |
| G/H | Boring type 1 + aantal |
| I/J | Boring type 2 + aantal |
| K | Vergunning (P/W/R/-) |
| L | Notitie |
| M | KLIC |
| N | Google Maps URL |
| O | PDOK URL |
| P | Waterkering URL |
| Q | Oppervlaktewater URL |
| R | Peil URL |
| S-W | EV partijen (1-5) |
| X-AC | Email contacten (1-6) |

### Gedrag

- Orders die al bestaan (zelfde ordernummer) worden **overgeslagen**
- Status wordt gemapt van Engelse Excel-waarden naar interne codes
- Boringen worden aangemaakt op basis van type + aantal (kolommen G-J)
- Bij "Wissen" worden alle tabellen in de juiste volgorde geleegd (cascading deletes)

---

## 8. Gebruikers

Het systeem gebruikt HTTP Basic Authentication. Er zijn geen gebruikerstabellen in de database — accounts zijn geconfigureerd via environment variabelen.

| Gebruiker | Variabele | Rol |
|-----------|-----------|-----|
| `martien` | `USER_MARTIEN_PASSWORD` | Tekenaar / hoofdgebruiker |
| `visser` | `USER_VISSER_PASSWORD` | Tekenaar |
| `test` | `USER_TEST_PASSWORD` | Testgebruiker (alleen in development) |

Alle gebruikers zitten in dezelfde workspace (`gbt-workspace-001`). Er is geen rolgebaseerde autorisatie — alle gebruikers hebben dezelfde rechten.

---

## 9. Backup & herstel

### Database

De database is een enkel SQLite-bestand (standaard `hdd.db`, op Railway typisch `/data/hdd.db`). Backup = kopie van dit bestand.

### Herstel via Excel re-import

Omdat de Excel order overview het bronbestand is, kan de volledige orderdataset hersteld worden:

1. Ga naar `/orders/import`
2. Vink **"Wissen"** aan (verwijdert alle bestaande orders, boringen en gerelateerde data)
3. Upload het Excel-bestand
4. De import herstelt alle orders met boringen, EV-partijen en emailcontacten

**Let op**: trace-punten, doorsneden, maaiveld-overrides, berekeningen, KLIC-data, as-built punten en werkplan-afbeeldingen worden **niet** hersteld via Excel-import. Deze moeten opnieuw worden ingevoerd.

### Alembic migraties

Database schema-wijzigingen worden beheerd via Alembic:

```bash
alembic upgrade head      # migraties toepassen
alembic revision --autogenerate -m "beschrijving"  # nieuwe migratie
```

Bij startup maakt de app ook automatisch ontbrekende tabellen aan via `Base.metadata.create_all()`.
