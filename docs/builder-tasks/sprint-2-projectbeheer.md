# Builder Task — Sprint 2: Projectbeheer

**Sprint:** 2 | **Duur:** 1.5 week | **Afhankelijkheden:** Sprint 1 compleet

---

## Doel

Werkvoorbereider kan projecten aanmaken, openen en de status bijhouden. Engineer kan een project openen en bewerken.

---

## Wat te bouwen

### Backend

#### `app/models/project.py`

SQLAlchemy modellen voor:

**`hdd.projecten`:**
- `id` (UUID, PK)
- `naam` (str, not null)
- `opdrachtgever` (str, not null)
- `locatie_omschrijving` (str)
- `leiding_type` (str — glasvezel/water/gas/elektriciteit/anders)
- `leiding_materiaal` (str — PE/staal/PVC)
- `leiding_diameter_mm` (float)
- `leiding_wanddikte_mm` (float)
- `gewenste_output` (JSONB — array van strings: pdf/dwg/berekeningen/werkplan)
- `status` (enum: concept/ontwerp/review/opgeleverd/gearchiveerd)
- `aangemaakt_door_id` (UUID FK → gebruikers)
- `aangemaakt_op` (datetime)
- `gewijzigd_op` (datetime)

**`hdd.project_status_geschiedenis`:**
- `id` (UUID, PK)
- `project_id` (UUID FK → projecten)
- `oude_status` (str)
- `nieuwe_status` (str)
- `opmerking` (str, nullable)
- `gewijzigd_door_id` (UUID FK → gebruikers)
- `gewijzigd_op` (datetime)

#### `app/services/project_service.py`

- `maak_project(data, user)` → Project
- `haal_project_op(project_id, user)` → Project of 404
- `lijst_projecten(user, status_filter, page, limit)` → lijst + totaal
- `werk_project_bij(project_id, data, user)` → Project
- `verwijder_project(project_id, user)` — alleen concept-projecten, alleen eigen projecten of beheerder
- `wijzig_status(project_id, nieuwe_status, opmerking, user)` → Project
  - Geldige statusovergangen: concept→ontwerp, ontwerp→review, review→opgeleverd, *→gearchiveerd (beheerder only)
  - Illegale overgang → 422 met melding
- `kopieer_project(project_id, user)` → nieuw Project (basisdata, geen brondata)
- `status_geschiedenis(project_id, user)` → lijst

#### `app/routers/projecten.py`

```
POST   /api/v1/projecten                    → aanmaken (alle auth. rollen)
GET    /api/v1/projecten                    → lijst (query params: status, page, limit, zoek)
GET    /api/v1/projecten/{id}               → ophalen
PUT    /api/v1/projecten/{id}               → bijwerken (eigen project of beheerder)
DELETE /api/v1/projecten/{id}              → verwijderen (alleen concept)
PUT    /api/v1/projecten/{id}/status        → statusovergang
GET    /api/v1/projecten/{id}/status-geschiedenis → lijst
POST   /api/v1/projecten/{id}/kopieer      → kopiëren
```

#### `app/schemas/project.py`

Pydantic v2 schemas:
- `ProjectAanmaken` — alle velden voor aanmaken
- `ProjectBijwerken` — optionele velden voor bijwerken
- `ProjectResponse` — volledige response
- `ProjectLijstItem` — compacte versie voor lijst
- `StatusWijziging` — `{nieuwe_status, opmerking}`

#### Tests (`tests/test_projecten.py`)

- Project aanmaken → 201 + project object
- Project ophalen → 200
- Project bijwerken → 200
- Project verwijderen (concept) → 204
- Project verwijderen (niet-concept) → 422
- Statusovergang geldig → 200
- Statusovergang ongeldig → 422
- Kopieer project → nieuw project met zelfde basisdata, andere ID

---

### Frontend

#### `src/pages/Projecten.tsx`

Projectenoverzicht:
- Tabel met kolommen: naam, opdrachtgever, status (badge), aangemaakt op
- Statusfilter dropdown (alle/concept/ontwerp/review/opgeleverd)
- Zoekbalk op projectnaam (client-side filtering)
- "Nieuw project" knop → opent wizard
- Klik op rij → navigeer naar `/projecten/{id}`
- Lege state: "Geen projecten gevonden. Maak uw eerste project aan."
- Paginatie (20 per pagina)

#### `src/pages/ProjectAanmaken.tsx`

3-staps wizard:

**Stap 1 — Basisgegevens:**
- Projectnaam (verplicht)
- Opdrachtgever (verplicht)
- Locatie omschrijving (optioneel, vrije tekst)

**Stap 2 — Leiding:**
- Type (dropdown: glasvezel/water/gas/elektriciteit/anders)
- Materiaal (dropdown: PE/staal/PVC)
- Diameter in mm (numeriek)
- Wanddikte in mm (numeriek)

**Stap 3 — Gewenste output:**
- Checkboxes: PDF tekening (altijd aangevinkt, disabled), DWG tekening (altijd aangevinkt, disabled), Technische berekeningen, Werkplan

Submit → POST `/api/v1/projecten` → redirect naar `/projecten/{id}`

#### `src/pages/ProjectDetail.tsx`

- Sidebar links: projectinfo (naam, opdrachtgever, status badge, datum)
- Statusbadge met kleur (concept=grijs, ontwerp=blauw, review=oranje, opgeleverd=groen)
- Tabbladen voor workflow stappen (1-7), alleen stap 1 actief in deze sprint
- "Status wijzigen" knop → modal met dropdown nieuwe status + tekstveld opmerking
- "Project kopiëren" knop
- Statushistorie accordion onderaan

---

## Data in / Data uit

**In:** projectgegevens (naam, opdrachtgever, leiding, output selectie)
**Uit:** Project object met UUID, status-machine

---

## Modules geraakt

- `app/main.py` — projecten router registreren

---

## Acceptatiecriteria

- [ ] Werkvoorbereider maakt project aan in < 2 minuten via 3-staps wizard
- [ ] Projectenlijst laadt in < 1 seconde (20 projecten, geen N+1 queries)
- [ ] Statusovergang concept→ontwerp lukt
- [ ] Statusovergang opgeleverd→concept geeft 422
- [ ] Project verwijderen werkt alleen voor concept-projecten
- [ ] Kopiëren dupliceert basisgegevens, start als nieuw concept-project
- [ ] Status-geschiedenis toont alle wijzigingen met gebruikersnaam en tijdstip

---

## User Stories

- Epic 1 Must have: "Als werkvoorbereider wil ik een nieuw project aanmaken"
- Epic 1 Must have: "Als werkvoorbereider wil ik de status van een project kunnen bijhouden"
- Epic 1 Must have: "Als werkvoorbereider wil ik een overzicht zien van alle projecten"
- Epic 1 Must have: "Als engineer wil ik een bestaand project kunnen openen en verder bewerken"
