# Builder Task — Sprint 2: Project CRUD

**Sprint:** 2 | **Duur:** 1 week | **Afhankelijkheden:** Sprint 1 compleet

---

## Doel

Engineers kunnen projecten aanmaken, openen en de status bijhouden.

---

## Wat te bouwen

### Backend

#### `app/project/models.py`

SQLAlchemy modellen voor `project` tabel (schema aanwezig uit sprint 0).

#### `app/project/service.py`

```python
async def maak_project(data: ProjectAanmaken, user: Gebruiker, workspace: Workspace, db) -> Project
async def haal_project_op(project_id: UUID, workspace: Workspace, db) -> Project   # 404 als niet gevonden
async def lijst_projecten(workspace: Workspace, status: str | None, db) -> list[Project]
async def werk_project_bij(project_id: UUID, data: ProjectBijwerken, workspace, db) -> Project
async def verwijder_project(project_id: UUID, workspace, db) -> None   # alleen concept
async def wijzig_status(project_id: UUID, nieuwe_status: str, workspace, db) -> Project
```

Statusmachine — geldige overgangen:
```
concept → ontwerp → review → opgeleverd
```
Illegale overgang → 422 met melding.

Alle queries filteren op `workspace_id` via `get_current_workspace`.

#### `app/api/routers/projecten.py`

```
POST   /api/v1/projecten                → aanmaken
GET    /api/v1/projecten                → lijst (query param: status)
GET    /api/v1/projecten/{id}           → ophalen
PUT    /api/v1/projecten/{id}           → bijwerken
DELETE /api/v1/projecten/{id}           → verwijderen (alleen concept)
PUT    /api/v1/projecten/{id}/status    → statusovergang
```

#### `app/project/schemas.py`

Pydantic v2 schemas:
- `ProjectAanmaken` — naam (verplicht), opdrachtgever (verplicht), locatie_omschrijving, type_leiding
- `ProjectBijwerken` — alle velden optioneel
- `ProjectResponse` — volledig object
- `ProjectLijstItem` — compacte versie voor lijst

#### Tests (`tests/test_projecten.py`)

- Project aanmaken → 201
- Project ophalen → 200
- Statusovergang geldig → 200
- Statusovergang ongeldig → 422
- Project verwijderen (concept) → 204
- Project verwijderen (niet-concept) → 422
- Projecten zijn workspace-geïsoleerd (query op andere workspace geeft 404)

---

### Frontend

#### `src/pages/Projecten.tsx`

- Tabel: naam, opdrachtgever, status (badge), aangemaakt op
- Statusfilter dropdown
- Zoekbalk op naam (client-side)
- "Nieuw project" knop → wizard
- Klik op rij → navigeer naar `/projecten/{id}`
- Lege state: "Nog geen projecten. Maak uw eerste project aan."

#### `src/pages/ProjectAanmaken.tsx`

Eenvoudig formulier (geen wizard nodig voor iteratie 1):
- Projectnaam (verplicht)
- Opdrachtgever (verplicht)
- Locatie omschrijving (optioneel)
- Type leiding (dropdown)
- Submit → POST → redirect naar `/projecten/{id}`

#### `src/pages/ProjectDetail.tsx`

- Sidebar: projectinfo, status badge
- Tabbladen voor workflow stappen (worden per sprint gevuld):
  - Locatie (sprint 3)
  - Brondata (sprint 4)
  - Eisen (sprint 5)
  - Ontwerp (sprint 6)
  - Output (sprint 7)
- "Status wijzigen" knop → modal met dropdown
- In deze sprint: alleen basistabblad zichtbaar, rest grijs

---

## Data in / Data uit

**In:** projectgegevens (naam, opdrachtgever, type leiding)
**Uit:** Project object met UUID en status

---

## Modules geraakt

- `app/main.py` — projecten router registreren

---

## Acceptatiecriteria

- [ ] Project aanmaken in < 1 minuut via formulier
- [ ] Projectenlijst laadt (paginering niet vereist in iteratie 1)
- [ ] Statusovergang concept → ontwerp werkt
- [ ] Ongeldige statusovergang geeft 422
- [ ] Project verwijderen werkt alleen voor concept-projecten
- [ ] Projecten zijn niet zichtbaar voor andere workspaces

---

## User Stories

- Epic 1 Must have: "Als werkvoorbereider wil ik een nieuw project aanmaken"
- Epic 1 Must have: "Als werkvoorbereider wil ik de status bijhouden"
- Epic 1 Must have: "Als werkvoorbereider wil ik een overzicht van alle projecten"
- Epic 1 Must have: "Als engineer wil ik een project openen en bewerken"
