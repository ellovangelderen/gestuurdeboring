# HDD Ontwerp Platform

Een digitaal engineering platform voor de voorbereiding van gestuurde boringen (HDD — Horizontal Directional Drilling).

Gebouwd met de **LeanAI Platform** werkwijze van [Inodus](https://inodus.nl).

---

## Wat doet dit platform

Ingenieurs en werkvoorbereiders gebruiken dit platform om gestuurde boringen voor te bereiden. Het platform genereert automatisch een boringtracé op basis van locatiedata, bestaande kabels en leidingen (KLIC), topografie (BGT) en de eisen van de vergunningverlener.

**Verplichte output:**
- PDF tekening (situatietekening + lengteprofiel)
- DWG tekening (met lagenstructuur voor AutoCAD)

**Optionele output (per project in te stellen):**
- Technische berekeningen (sterkte, intrekkracht, boorvloeistofdruk)
- Werkplan / boorplan (PDF)

De scope van dit platform is uitsluitend de **engineeringvoorbereiding**. De boring zelf wordt door een aannemer uitgevoerd en valt buiten dit systeem.

---

## Gebruikers

| Rol | Taken |
|---|---|
| Werkvoorbereider | Project aanmaken, brondata invoeren, output selecteren |
| Engineer | Ontwerp beoordelen, aanpassen, berekeningen valideren |
| Beheerder | Eisenprofielen, templates en gebruikersbeheer |

---

## Workflow

```
1. Project intake     Naam, opdrachtgever, locatie, type leiding
        ↓
2. Brondata           KLIC GML upload · BGT ophalen · DWG upload (optioneel)
        ↓
3. Eisen laden        Eisenprofiel per beheerder (RWS / waterschap / gemeente)
        ↓
4. Ontwerp genereren  Boorcurve berekenen · conflict check met bestaande leidingen
        ↓
5. Review + aanpassen Kaartweergave · lengteprofiel · handmatig aanpassen
        ↓
6. Berekeningen       Optioneel: trek · sterkte · boorvloeistofdruk
        ↓
7. Output genereren   PDF · DWG · werkplan · berekening
        ↓
   Oplevering aan aannemer
```

---

## Architectuur

```
Frontend (React)
    Intake wizard · Kaart + brondata · Ontwerp review · Output
        ↓
Application API (FastAPI)
    Workflow · Orkestratie · Auth · Versiebeheer
        ↓
┌─────────┬──────────┬──────────┬───────────┬──────────┐
│  Geo &  │  Rule    │   HDD    │  Doc &    │   AI     │
│Brondata │ Engine   │  Design  │ Drawing   │ Assist   │
│ Service │          │  Engine  │Generator  │          │
└─────────┴──────────┴──────────┴───────────┴──────────┘
        ↓
PostgreSQL/PostGIS · File Storage · Async Queue
```

**Volledige architectuurdocumentatie:** zie `docs/architecture.md`

---

## Technische stack

| Laag | Technologie |
|---|---|
| Frontend | React + Vite |
| Kaart | Leaflet / MapLibre GL |
| Backend | Python FastAPI |
| Database | PostgreSQL + PostGIS |
| File storage | S3-compatibel |
| Async jobs | ARQ / Celery |
| DWG output | ezdxf |
| PDF output | WeasyPrint / ReportLab |
| Containers | Docker + GitHub Actions |

---

## Projectstructuur

```
hdd-platform/
├── CLAUDE.md                    LeanAI Architect Agent instructies
├── README.md                    Dit bestand
├── docs/
│   ├── architect-input.md       Requirements en epics (projectinput)
│   ├── architecture.md          Architectuurbeslissingen
│   ├── epics-userstories.md     MoSCoW backlog
│   └── builder-tasks/           Bouwverzoeken voor Builder Agent
├── frontend/                    React applicatie
├── backend/                     FastAPI applicatie
│   ├── app/
│   │   ├── project/             Projectbeheer
│   │   ├── geo/                 KLIC/BGT import en geometrie
│   │   ├── rules/               Eisenprofielen per beheerder
│   │   ├── design/              HDD design engine
│   │   ├── calculations/        Technische berekeningen
│   │   ├── documents/           PDF en DWG generatie
│   │   ├── ai_assist/           AI tekstgeneratie werkplan
│   │   └── api/                 Routes, auth, middleware
│   ├── tests/
│   └── alembic/                 Database migraties
└── docker/
    ├── docker-compose.yml
    └── Dockerfile
```

---

## Lokaal opstarten

### Vereisten
- Docker + Docker Compose
- Python 3.11+
- Node.js 20+

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Database starten
docker-compose up -d db

# Migraties uitvoeren
alembic upgrade head

# API starten
uvicorn app.main:app --reload
```

API draait op: `http://localhost:8000`
API docs: `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend draait op: `http://localhost:5173`

### Alles tegelijk

```bash
docker-compose up
```

---

## Environment variabelen

Maak een `.env` bestand aan in `backend/` op basis van `.env.example`:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/hdd_platform
SECRET_KEY=change-me-in-production
S3_BUCKET=hdd-platform-files
S3_ENDPOINT=http://localhost:9000
BGT_API_URL=https://api.pdok.nl/lv/bgt/ogc/v1_0
```

---

## LeanAI werkwijze

Dit project is gebouwd met de **LeanAI Platform** agent-pipeline:

```
Model Agent  →  Architect Agent  →  Builder Agent  →  Release Agent
Verkennen       Technisch ontwerp   Bouwen per        Valideren en
& modelleren    & bewaken           onderdeel         deployen
```

De **Architect Agent** (`CLAUDE.md`) instrueert Claude Code over architectuurprincipes, scope en werkwijze. De Architect Agent blijft actief gedurende het hele project.

Meer over de LeanAI werkwijze: [inodus.nl](https://inodus.nl)

---

## MVP scope

Release 1 bevat alle Must Have stories uit de epics. Zie `docs/epics-userstories.md`.

**Expliciet buiten scope (alle releases):**
- Calculatiemodule (kostprijs)
- Offertemodule

**Buiten MVP, mogelijk later:**
- Geautomatiseerde KLIC-aanvraag
- Meerdere boringen per project
- 3D visualisatie
- Koppeling financieel pakket

---

## Domeinkennis

### Gestuurde boring (HDD)

Bij HDD worden kabels en leidingen aangelegd zonder te graven. Een gespecialiseerde boormachine boort een stuurbaar gat onder obstakels door — wegen, water, spoorlijnen, waterkeringen. Daarna wordt de leiding door het geboorde gat getrokken.

### KLIC

Via een KLIC-melding bij het Kadaster ontvang je een overzicht van bestaande kabels en leidingen in de ondergrond. De data wordt aangeleverd als GML-bestanden en bevat elektriciteit, gas, telecom, water en riool met geometrie, diepte en beheerdersinformatie.

### BGT

De Basisregistratie Grootschalige Topografie is open topografische data van het Kadaster. Bevat wegen, water, spoor, gebouwen en taluds. Beschikbaar via een open API (PDOK).

### Eisenprofielen

Elke vergunningverlener heeft eigen eisen voor gestuurde boringen. Voorbeelden: Rijkswaterstaat vereist minimaal 3 meter diepte onder de fundering van een rijksweg; waterschappen hanteren 5–10 meter onder de dijkkern afhankelijk van het waterkeringstype.

---

*LeanAI Platform · Inodus · Haarlem · 2026*
