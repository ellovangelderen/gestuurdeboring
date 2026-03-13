# HDD Ontwerp Platform

Een digitaal platform voor de voorbereiding van gestuurde boringen (HDD).

Beheerd door [Inodus](https://inodus.nl) · Bereikbaar op **hdd.inodus.nl**

---

## Wat doet dit platform

Engineers en werkvoorbereiders gebruiken dit platform om gestuurde boringen voor te bereiden. Het platform genereert automatisch een boringtracé op basis van locatiedata, bestaande kabels en leidingen (KLIC) en de eisen van de vergunningverlener.

De applicatie draait in de cloud — geen installatie nodig. Inloggen op `hdd.inodus.nl` en je kunt direct aan de slag.

**Altijd als output:**
- PDF tekening — situatietekening + lengteprofiel, klaar voor vergunningsindiening
- DWG tekening — met lagenstructuur, direct te openen in AutoCAD

**Later beschikbaar (volgende versie):**
- Werkplan / boorplan automatisch gegenereerd
- Technische berekeningen (intrekkracht, sterkte)

De scope is uitsluitend de **engineeringvoorbereiding**. De boring zelf wordt door een aannemer uitgevoerd en valt buiten dit systeem.

---

## Workflow

```
1. Project intake     Naam · opdrachtgever · locatie · type leiding
        ↓
2. Brondata           KLIC GML uploaden · start- en eindpunt op kaart aanwijzen
        ↓
3. Eisen laden        Te kruisen object selecteren · eisenprofiel kiezen
        ↓
4. Ontwerp            Boorcurve automatisch berekend · conflicten gemarkeerd
        ↓
5. Review             Bovenaanzicht + lengteprofiel · parameters aanpassen indien nodig
        ↓
6. Output             PDF + DWG downloaden · werkplan invullen
        ↓
   Oplevering aan aannemer
```

---

## Gebruikers

Iedereen met een account heeft toegang tot de applicatie. Accountbeheer loopt via Inodus.

---

## Wat de engineer zelf doet (versie 1)

- KLIC aanvragen bij het Kadaster en de GML-bestanden uploaden
- Ontwerp beoordelen en eventueel parameters aanpassen
- Werkplan invullen op basis van de parameters die het systeem aanlevert

---

## Versieplan

| | Nu (versie 1) | Volgende versie |
|---|---|---|
| Project beheren | ✓ | |
| KLIC upload + kaart | ✓ | |
| Eisenprofiel selecteren | ✓ | |
| Ontwerp berekenen | ✓ | |
| PDF + DWG downloaden | ✓ | |
| BGT automatisch ophalen | | ✓ |
| Werkplan automatisch genereren | | ✓ |
| Technische berekeningen | | ✓ |

---

## Technisch overzicht

| Onderdeel | Details |
|---|---|
| URL | hdd.inodus.nl |
| Hosting | Railway — beheerd door Inodus |
| Backend | Python FastAPI |
| Frontend | React |
| Database | PostgreSQL |
| Kaart | Leaflet + OpenStreetMap |
| PDF output | WeasyPrint |
| DWG output | ezdxf |
| Deployment | Automatisch via GitHub Actions |

---

## Lokaal ontwikkelen

Voor ontwikkeling en testen kun je de applicatie lokaal draaien.

**Vereisten:** Docker + Docker Compose

```bash
git clone https://github.com/inodus/hdd-platform
cd hdd-platform
cp .env.example .env
docker-compose up
```

Applicatie: `http://localhost:3000`
API docs: `http://localhost:8000/docs`

**.env.example:**
```
DATABASE_URL=postgresql://postgres:postgres@db:5432/hdd_platform
SECRET_KEY=lokaal-development-key
STORAGE_BACKEND=local
STORAGE_PATH=./data/files
ENVIRONMENT=development
```

---

## Projectstructuur

```
hdd-platform/
├── CLAUDE.md           LeanAI Architect Agent instructies
├── README.md           Dit bestand
├── docker-compose.yml  Lokaal opstarten
├── docs/               Architectuur en bouwtaken
├── backend/            Python FastAPI
│   └── app/
│       ├── core/       Auth, config, database
│       ├── project/    Projectbeheer
│       ├── geo/        KLIC import + kaartweergave
│       ├── rules/      Eisenprofielen per beheerder
│       ├── design/     HDD ontwerp engine
│       ├── documents/  PDF + DWG generatie
│       └── api/        Routes
└── frontend/           React applicatie
```

---

## Domeinkennis

**HDD (Horizontal Directional Drilling):** Kabels en leidingen aanleggen zonder te graven. Een boormachine boort een stuurbaar gat onder obstakels door — wegen, water, spoor, waterkeringen.

**KLIC:** Overzicht van bestaande kabels en leidingen in de ondergrond. Aangevraagd bij het Kadaster, opgeleverd als GML-bestanden. Bevat elektriciteit, gas, telecom, water en riool.

**Eisenprofielen:** Elke vergunningverlener stelt eigen eisen aan de boring. Rijkswaterstaat: minimaal 3 m onder de fundering van een rijksweg. Waterschap: 5–10 m onder de dijkkern.

---

## Beheer en ondersteuning

De applicatie wordt beheerd door Inodus. Voor vragen en ondersteuning: [info@inodus.nl](mailto:info@inodus.nl)

---

*Gebouwd met LeanAI Platform · Inodus · 2026*
