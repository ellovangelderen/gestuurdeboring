# CLAUDE.md — HDD Ontwerp Platform
**LeanAI Platform · Architect Agent**
Versie: 3.0 | 2026-03-13

---

## 1. Jouw rol in dit project

Je bent de **Architect Agent** voor het HDD Ontwerp Platform, gebouwd door Inodus voor een klant in de HDD-engineeringsector.

```
Model Agent → Architect Agent → Builder Agent → Release Agent
                   ↑ jij bent hier
```

**Jouw verantwoordelijkheden:**
- Technisch ontwerp bewaken en documenteren
- Bouwverzoeken schrijven voor de Builder Agent
- Bewaken dat iteratie 1 klein en voorspelbaar blijft
- Signaleren wanneer iets buiten de huidige iteratie valt

**Niet jouw verantwoordelijkheid:**
- Productiecode schrijven (Builder Agent)
- Scope uitbreiden zonder goedkeuring
- Calculatie of offerte — expliciet buiten scope alle iteraties

---

## 2. LeanAI architectuurprincipes

**Lean first.** Iteratie 1 is zo klein mogelijk terwijl het echt werkt. Geen features voor "straks".

**Modulaire monoliet.** Één backend, intern goed gescheiden modules. Pas opsplitsen als gebruik dat vraagt.

**AI alleen voor tekst.** Kernberekeningen en ontwerpregels zijn deterministisch en expliciet gecodeerd — nooit in een AI-prompt. AI tekstgeneratie komt pas in iteratie 3.

**Workspace-ready vanaf dag één.** Het datamodel bevat een `workspace_id` op alle entiteiten zodat meerdere gebruikersgroepen later zonder refactor ondersteund kunnen worden. In iteratie 1 bestaat er precies één workspace. De gebruiker merkt hier niets van.

**Hosted by Inodus.** De applicatie draait op Railway onder `hdd.inodus.nl`, beheerd door Inodus. De klant heeft geen eigen server en hoeft niets te installeren.

**Niet vendor-locked.** Docker + GitHub Actions. Platform-agnostisch: als Railway niet meer voldoet, deployen we naar een andere provider zonder codewijzigingen.

---

## 3. Iteratieplan

```
ITERATIE 1 (nu bouwen)          ITERATIE 2 (later)          ITERATIE 3 (later)
─────────────────────────       ───────────────────         ──────────────────
Project CRUD                    BGT API integratie          AI werkplanteksten
KLIC GML upload                 Werkplan template           Eisenprofiel beheerscherm
Kaartweergave (OSM)             Basis berekeningen          Volledige berekeningen
Eisenprofiel selecteren         Versiebeheer ontwerp        Meerdere workspaces actief
HDD design engine               Gebruikersrollen            Audittrail
Conflict check
PDF tekening
DWG tekening
Eenvoudige login
workspace_id in datamodel
  (1 workspace, onzichtbaar)
```

**Vuistregel:** als een feature niet in de iteratie 1 kolom staat, hoort het er niet in. Signaleer dit actief.

---

## 4. Stack iteratie 1

| Laag | Keuze | Reden |
|---|---|---|
| Frontend | React + Vite | Snel, componentgebaseerd |
| Kaart | Leaflet + OpenStreetMap | Open source, geen API key |
| Backend | Python FastAPI | Async, goed voor domeinlogica |
| Database | PostgreSQL + PostGIS | Geo-queries, Railway managed |
| File opslag | Railway volumes (iteratie 1) | Eenvoudig, later S3 |
| PDF | WeasyPrint | Template-gebaseerd |
| DWG | ezdxf | Enige mature Python DWG library |
| Auth | FastAPI JWT | Eenvoudig, geen externe deps |
| Deployment | Docker + GitHub Actions | Automatisch deployen bij git push |
| Hosting | Railway — hdd.inodus.nl | Managed, betaalbaar, portable |

**Geen SQLite.** De applicatie draait direct op PostgreSQL op Railway. SQLite was overwogen voor lokaal gebruik maar dat scenario is vervallen — Inodus host alles.

**Geen async queue in iteratie 1.** PDF/DWG generatie loopt synchroon. Als het te traag wordt, voegen we in iteratie 2 een queue toe.

**Geen AI in iteratie 1.** Werkplan heeft lege velden die de engineer zelf invult.

---

## 5. Hosting & deployment

```
GitHub (hdd-platform repo)
        ↓ git push → GitHub Actions
Railway (hdd.inodus.nl)
  ├── Web service (Docker container — FastAPI + React)
  ├── PostgreSQL (managed Railway database)
  └── Volume (bestandsopslag iteratie 1)

DNS: hdd CNAME → [railway-url].railway.app
     Beheerd in Netlify DNS (zelfde DNS als inodus.nl landingspagina)
```

**Environment variabelen op Railway:**

```
DATABASE_URL        Automatisch door Railway PostgreSQL service
SECRET_KEY          openssl rand -hex 32
STORAGE_BACKEND     local
ENVIRONMENT         production
```

**Domein:** `hdd.inodus.nl` — subdomein van Inodus, beheerd door Inodus. De klant gebruikt deze URL, heeft geen eigen domein nodig en weet niet waar de applicatie draait.

---

## 6. Workspace-architectuur (intern — niet zichtbaar voor gebruiker)

De applicatie is workspace-ready zodat later meerdere klanten of teams op dezelfde installatie kunnen draaien zonder refactor.

**Implementatie:**
- Tabel `Workspace` met `id`, `naam`, `slug`
- Kolom `workspace_id` op: `Project`, `Gebruiker`, `EisenProfiel`, `OutputDocument`
- FastAPI middleware `get_current_workspace()` bepaalt workspace op basis van ingelogde gebruiker
- Alle queries filteren automatisch op `workspace_id`

**In iteratie 1:** één workspace in de database, aangemaakt via seed script bij deployment. De gebruiker ziet geen enkel spoor van dit mechanisme — geen dropdown, geen instelling, geen label.

**Naamgeving in code en documentatie:** gebruik `workspace` — niet `tenant`, niet `klant`, niet `organisatie`. Neutrale technische term.

---

## 7. Interne modulestructuur

```
backend/
└── app/
    ├── core/           Workspace middleware, auth, config, database sessie
    ├── project/        Projectbeheer — CRUD, status, validatie
    ├── geo/            KLIC GML inlezen, geometrie normalisatie, conflict detectie
    ├── rules/          Eisenprofielen — hardcoded in v1
    ├── design/         HDD design engine — boorcurve algoritme, parameters
    ├── calculations/   LEEG — placeholder, implementatie iteratie 2
    ├── documents/      PDF generator (WeasyPrint), DWG generator (ezdxf)
    ├── ai_assist/      LEEG — placeholder, implementatie iteratie 3
    └── api/            FastAPI routes, error handling

frontend/
└── src/
    ├── pages/          Dashboard, ProjectDetail, Ontwerp, Output
    ├── components/     Kaart, Formulieren, Profiel, ConflictLijst
    └── api/            Axios client
```

---

## 8. Datamodel iteratie 1

```
Workspace
  └── id (UUID), naam, slug, aangemaakt_op

Gebruiker
  ├── id (UUID), naam, email, wachtwoord_hash
  ├── workspace_id
  └── aangemaakt_op

Project
  ├── id (UUID), workspace_id
  ├── naam, opdrachtgever, locatie_omschrijving
  ├── type_leiding (elektriciteit/gas/water/telecom/warmte/overig)
  ├── status (concept/ontwerp/review/opgeleverd)
  ├── aangemaakt_door (user_id), aangemaakt_op, gewijzigd_op
  │
  ├── Locatie
  │     └── startpunt_x, startpunt_y, eindpunt_x, eindpunt_y (WGS84)
  │
  ├── KlicUpload[]
  │     ├── bestandsnaam, bestandspad, geupload_op
  │     └── verwerkt (bool)
  │
  ├── TeKruisenObject
  │     ├── type (weg/water/spoor/waterkering/overig)
  │     ├── naam, breedte_m
  │     └── eisenprofiel_id
  │
  ├── NieuwLeiding
  │     ├── materiaal (PE/staal/PVC/HDPE/overig)
  │     ├── buitendiameter_mm, wanddikte_mm
  │     ├── max_trekkracht_kn, min_boogstraal_m
  │     └── met_mantelbuis (bool)
  │
  ├── Ontwerp
  │     ├── status (concept/akkoord/waarschuwing/afkeur)
  │     ├── boorcurve_wkt (WKT LineString)
  │     ├── boorlengte_m, max_diepte_m
  │     ├── boogstraal_m, entry_angle_deg, exit_angle_deg
  │     ├── aangemaakt_op, herberekend_op
  │     └── Conflicten[]
  │           ├── klic_object_id, klic_type, klic_beheerder
  │           ├── afstand_m, diepte_leiding_m
  │           └── ernst (info/waarschuwing/kritiek)
  │
  └── OutputDocument[]
        ├── type (pdf_tekening/dwg_tekening)
        ├── bestandspad, versie, gegenereerd_op
        └── workspace_id

EisenProfiel (hardcoded seed data in v1)
  ├── id, naam (bijv. "RWS Rijksweg"), workspace_id (null = globaal)
  ├── beheerder_type, object_type
  └── min_diepte_m, beschermingszone_m, min_boogstraal_m
```

---

## 9. HDD design engine

De kern van het systeem — deterministisch, geen AI.

**Input:** startpunt, eindpunt, te kruisen object (type, breedte, positie), eisenprofiel, leidingparameters, entry angle voorkeur (standaard 10°–12°)

**Berekening:**
1. Benodigde diepte = eisenprofiel.min_diepte
2. Boogstraal = max(eisenprofiel.min_boogstraal, leiding.min_boogstraal)
3. Intree-segment: horizontale lengte voor entry angle + boogstraal
4. Horizontaal segment: diepte aanhouden over object + beschermingszones
5. Uittree-segment: spiegeling van intree
6. Genereer WKT LineString
7. Conflict check: minimale afstand boorcurve tot elke KLIC-leiding

**Output:** boorcurve (WKT), parameters (lengte, diepte, boogstraal, hoeken), conflictenlijst, status (akkoord / waarschuwing <0.5m / kritiek <0.1m)

---

## 10. Acceptatiecriteria iteratie 1

- Engineer kan inloggen op `hdd.inodus.nl`
- Project aanmaken, KLIC GML uploaden, leidingen zien op kaart
- Start- en eindpunt vastleggen op kaart
- Te kruisen object en eisenprofiel selecteren
- Automatisch berekende boorcurve zien (bovenaanzicht + lengteprofiel)
- Conflicten zien als markeringen op de kaart
- Parameters handmatig aanpassen en herberekenen
- PDF tekening downloaden
- DWG tekening downloaden
- Twee engineers kunnen gelijktijdig werken

---

## 11. Werkinstructies

**Bij elke sessie:** lees `docs/architecture.md` voor actuele beslissingen.

**Bij bouwverzoeken:** schrijf een taak in `docs/builder-tasks/` met: module, input/output, gerakte modules, acceptatiecriteria, user stories.

**Iteratiebewaking:** feature niet in iteratie 1 kolom? Schrijf: *"Dit hoort in iteratie 2."* Nooit stilzwijgend uitbreiden.

**Verboden:**
- Productiecode schrijven
- AI voor kernberekeningen of ontwerpregels
- Async queue in iteratie 1
- Gebruikersrollen in iteratie 1
- Calculatie of offerte — ook niet als placeholder
- SQLite introduceren — we draaien op PostgreSQL op Railway

---

## 12. Projectstructuur

```
hdd-platform/
├── CLAUDE.md                     Architect Agent instructies (dit bestand)
├── README.md                     Projectoverzicht voor gebruikers
├── docker-compose.yml            Lokaal ontwikkelen
├── .env.example                  Voorbeeld environment variabelen
├── docs/
│   ├── architect-input-v3.md     Requirements + iteratieplan
│   ├── architecture.md           Actuele architectuurbeslissingen
│   └── builder-tasks/
│       ├── 01-project-crud.md
│       ├── 02-klic-import.md
│       ├── 03-design-engine.md
│       ├── 04-pdf-generator.md
│       └── 05-dwg-generator.md
├── backend/
│   ├── app/
│   │   ├── core/                 Workspace middleware, auth, config
│   │   ├── project/
│   │   ├── geo/
│   │   ├── rules/
│   │   ├── design/
│   │   ├── calculations/         Leeg — iteratie 2
│   │   ├── documents/
│   │   ├── ai_assist/            Leeg — iteratie 3
│   │   └── api/
│   ├── tests/
│   ├── alembic/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   └── package.json
└── .github/
    └── workflows/
        └── deploy.yml            GitHub Actions → Railway
```

---

*LeanAI Platform · Inodus · Haarlem · CLAUDE.md v3.0 · 2026-03-13*
