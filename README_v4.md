# HDD Ontwerp Platform

Een digitaal platform voor de voorbereiding van gestuurde boringen (HDD).

Beheerd door [Inodus](https://inodus.nl) · Bereikbaar op **hdd.inodus.nl**

---

## Wat doet dit platform

Martien Luijben (GestuurdeBoringTekening.nl) gebruikt dit platform om gestuurde boringen voor te bereiden voor kabels en leidingen. Het platform begeleidt het hele traject van projectaanmaak tot het genereren van een vergunningsklare tekening en werkplan.

**Output van elke boring:**
- DWG tekening — lagenstructuur conform NLCS, direct te openen in AutoCAD
- PDF tekening — situatietekening + lengteprofiel + doorsnede, klaar voor vergunningsindiening

**Later beschikbaar (zie backlog):**
- Werkplan automatisch gegenereerd (Claude API)
- KLIC kabels en leidingen automatisch verwerkt
- Maaiveld automatisch opgehaald via AHN5

De scope is uitsluitend de **engineeringvoorbereiding**. De boring zelf wordt door een aannemer uitgevoerd en valt buiten dit systeem. Calculatie en offerte zijn permanent buiten scope.

---

## Aanpak: walking skeleton + backlog

Het platform is gebouwd via de walking skeleton aanpak: eerst een volledig werkend end-to-end systeem waarbij complexe stappen handmatig worden ingevuld (overrides). Daarna worden overrides één voor één vervangen door automatische modules — in volgorde van waarde, bepaald in overleg met Martien.

```
Walking Skeleton (nu)    Backlog (stap voor stap)
─────────────────────    ────────────────────────────────────────
Project aanmaken         1. KLIC IMKL 2.0 parser
Locatie invoeren         2. AHN5 maaiveld automatisch
KLIC upload (manual)     3. Werkplan generator (Claude API)
NAP handmatig            4. Boorprofiel geometrie (ARCs)
Grondtype dropdown       5. Sleufloze leidingen detectie
Intrekkracht manual      6. GWSW riool BOB + gemeente-mail
DWG genereren            7. Conflictcheck K&L 3D
PDF genereren            8. Dinoloket sonderingen
Drive download           9. GEF/CPT parser
                        10. Tracévarianten vergelijken
                        11. Intrekkrachtberekening NEN 3651
```

---

## Workflow

```
1. Project intake     Naam · opdrachtgever · ordernummer · leidingparameters
        ↓
2. Locatie            RDNAP-coördinaten A/B · tussenpunten · Rh per segment
        ↓
3. Brondata           KLIC uploaden · maaiveld (auto of handmatig) · grondtype
        ↓
4. Eisenprofiel       Te kruisen object · beheerder · NEN 3651 eisen
        ↓
5. Ontwerp            Boorprofiel · sensorpunten · conflictcheck K&L
        ↓
6. Review             Kaart + lengteprofiel · parameters aanpassen
        ↓
7. Output             DWG + PDF downloaden · werkplan genereren
        ↓
   Oplevering aan aannemer / indiening vergunning
```

---

## Gebruikers

Twee vaste gebruikers: Martien Luijben en collega tekenaar M. Visser. Accountbeheer via Inodus (wachtwoorden in Railway environment variables).

---

## Technisch overzicht

| Onderdeel | Details |
|---|---|
| URL | hdd.inodus.nl |
| Hosting | Railway — beheerd door Inodus, autodeploy bij git push |
| Backend | Python FastAPI |
| Frontend | HTMX + Jinja2 + Alpine.js |
| Database | SQLite + SQLAlchemy |
| Kaart | Leaflet + OpenStreetMap + PDOK |
| Coördinaten | pyproj (RD New EPSG:28992 ↔ WGS84) |
| PDF output | WeasyPrint + Jinja2 |
| DWG output | ezdxf (R2013 formaat) |
| Auth | FastAPI HTTPBasic (.env) |
| Deployment | Railway nixpacks autodeploy |

Geen Docker. Geen PostgreSQL. Geen React. Geen JWT. Geen GitHub Actions pipeline.

---

## Lokaal ontwikkelen

```bash
git clone https://github.com/inodus/hdd-platform
cd hdd-platform
cp .env.example .env
# Vul wachtwoorden in in .env
pip install -r requirements.txt
python scripts/init_db.py
python scripts/seed.py
uvicorn app.main:app --reload
```

Applicatie: `http://localhost:8000`

**.env.example:**
```
ENV=development
DATABASE_URL=sqlite:///./hdd.db

USER_MARTIEN_PASSWORD=
USER_VISSER_PASSWORD=
USER_TEST_PASSWORD=

ANTHROPIC_API_KEY=
```

`.env` staat in `.gitignore` — nooit in git. Productiewachtwoorden via Railway dashboard.

---

## Projectstructuur

```
hdd-platform/
├── CLAUDE.md               LeanAI Architect Agent instructies (v4)
├── README.md               Dit bestand
├── requirements.txt
├── app/
│   ├── main.py
│   ├── core/               auth, config, database
│   ├── project/            project CRUD
│   ├── geo/                KLIC parser, geometrie, conflict
│   ├── rules/              eisenprofielen
│   ├── design/             boorprofiel geometrie engine
│   ├── calculations/       LEEG — backlog 11
│   ├── documents/          PDF + DXF generator
│   ├── ai_assist/          LEEG — backlog 3
│   ├── drive/              LEEG — backlog (Drive sync)
│   └── templates/          Jinja2 HTML templates
├── static/                 CSS, JS, Leaflet
├── tests/                  geïsoleerde testcases per module
├── scripts/
│   ├── init_db.py          database aanmaken
│   └── seed.py             workspace + eisenprofielen + gebruikers
└── docs/
    ├── input_data_14maart/ testdata van Martien (HDD11, HDD28, GEF, KLIC...)
    └── backlog/            builder-taakinstructies per backlog item
```

---

## Testdata

Alle testdata staat in `docs/input_data_14maart/`. Twee referentieprojecten:

**HDD11 — Haarlem Kennemerplein**
PE100 SDR11 Ø160mm · 226,58m · 11 netbeheerders in KLIC · BerekeningHDD11 (Ttot=30.106N)

**HDD28 — Velsen-Noord Verkeersplein Noord N197**
DXF met 218 lagen · NLCS laagnamen gevalideerd · GWSW riooldata aanwezig

---

## Domeinkennis

**HDD (Horizontal Directional Drilling):** Kabels en leidingen aanleggen zonder te graven. Een boormachine boort een stuurbaar gat onder obstakels door — wegen, water, spoor, waterkeringen.

**KLIC:** Overzicht van bestaande kabels en leidingen in de ondergrond, aangevraagd bij het Kadaster. Opgeleverd als ZIP met IMKL 2.0 XML. Dieptes zijn altijd indicatief — nooit betrouwbaar als harde waarde.

**NLCS:** Nederlandse standaard voor CAD-laagnamen in de GWW-sector. Verplicht voor DWG-output. Laagnamen gevalideerd uit HDD28 DXF.

**RDNAP:** Coördinatenstelsel voor Nederland. RD New (EPSG:28992) is de standaard voor vergunningsdocumenten. Altijd 2 decimalen (= cm-nauwkeurig).

**Eisenprofielen:** Elke vergunningverlener stelt eigen eisen. RWS: minimaal 3m onder rijksweg. Waterschap: 5–10m onder dijkkern. Conform NEN 3651.

---

## Beheer en ondersteuning

De applicatie wordt beheerd door Inodus. Voor vragen: [info@inodus.nl](mailto:info@inodus.nl)

---

*Gebouwd met LeanAI Platform · Inodus · 2026*
