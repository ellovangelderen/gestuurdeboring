# Builder Task — Sprint 0: Fundament & Railway

**Sprint:** 0 | **Duur:** 1 week | **Afhankelijkheden:** geen

---

## Doel

Alle infrastructuur staat. De applicatie draait op Railway onder `hdd.inodus.nl`. De Builder Agent kan direct met features beginnen.

---

## Wat te bouwen

### 1. Repository structuur

```
hdd-platform/
├── CLAUDE.md
├── README.md
├── docker-compose.yml          ← lokale ontwikkeling
├── .env.example
├── docs/
│   ├── architecture.md
│   └── builder-tasks/
├── backend/
│   ├── app/
│   │   ├── core/               config, database, workspace middleware
│   │   ├── project/
│   │   ├── geo/
│   │   ├── rules/
│   │   ├── design/
│   │   ├── calculations/       LEEG — placeholder iteratie 2
│   │   ├── documents/
│   │   ├── ai_assist/          LEEG — placeholder iteratie 3
│   │   └── api/
│   ├── alembic/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   ├── package.json
│   └── Dockerfile
└── .github/
    └── workflows/
        └── deploy.yml
```

### 2. Docker Compose — lokale ontwikkeling (`docker-compose.yml`)

Services:
- `postgres` — PostgreSQL 16 + PostGIS 3.4, port 5432
- `backend` — FastAPI met hot-reload, port 8000
- `frontend` — Vite dev server, port 5173

Geen Redis, geen MinIO, geen worker service — die zijn niet nodig in iteratie 1.

Volumes voor postgres data persistentie.

### 3. Backend skelet

**`app/core/config.py`** — Pydantic BaseSettings:
```python
DATABASE_URL: str
SECRET_KEY: str
STORAGE_PATH: str = "/storage"   # Railway volume mount path
ENVIRONMENT: str = "development"
WORKSPACE_SLUG: str = "inodus"   # seed workspace slug
```

**`app/core/database.py`** — SQLAlchemy 2.x async (asyncpg):
```python
# Async engine + session factory
# get_db() dependency voor FastAPI
```

**`app/core/workspace.py`** — workspace middleware:
```python
async def get_current_workspace(db: Session) -> Workspace:
    """
    Haalt de enige workspace op uit de database.
    In iteratie 1: altijd dezelfde workspace.
    Klaar voor multi-workspace in iteratie 2+ zonder refactor.
    """
```

**`app/main.py`**:
- FastAPI app met lifespan
- Router: `/api/v1/health`
- CORS (alle origins in development, alleen `hdd.inodus.nl` in production)
- Global exception handler (geen stack traces in production)

**`app/api/routers/health.py`**:
```
GET /api/v1/health
Response: {"status": "ok", "db": "ok", "environment": "production"}
```

**`requirements.txt`**:
```
fastapi
uvicorn[standard]
sqlalchemy[asyncio]
asyncpg
alembic
pydantic-settings
python-jose[cryptography]
passlib[bcrypt]
lxml
shapely
pyproj
weasyprint
jinja2
ezdxf
pytest
pytest-asyncio
httpx
```

### 4. Database schema — `alembic/versions/0001_initial_schema.py`

**PostGIS extensie activeren:**
```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

**Tabel: `workspace`**
```sql
id          UUID PK
naam        VARCHAR(200) NOT NULL
slug        VARCHAR(100) NOT NULL UNIQUE
aangemaakt_op TIMESTAMPTZ DEFAULT now()
```

**Tabel: `gebruiker`**
```sql
id              UUID PK
workspace_id    UUID FK → workspace NOT NULL
naam            VARCHAR(200) NOT NULL
email           VARCHAR(200) NOT NULL UNIQUE
wachtwoord_hash VARCHAR NOT NULL
actief          BOOLEAN DEFAULT TRUE
aangemaakt_op   TIMESTAMPTZ DEFAULT now()
```

**Tabel: `eisenprofiel`**
```sql
id                  UUID PK
workspace_id        UUID FK → workspace (NULL = globaal)
naam                VARCHAR(200) NOT NULL
beheerder_type      VARCHAR(50) NOT NULL   -- RWS/WATERSCHAP/PROVINCIE/GEMEENTE
object_type         VARCHAR(50) NOT NULL   -- RIJKSWEG/WATERKERING/PROVINCIALE_WEG/GEMEENTEWEG
min_diepte_m        FLOAT NOT NULL
beschermingszone_m  FLOAT NOT NULL
min_boogstraal_m    FLOAT NOT NULL
aangemaakt_op       TIMESTAMPTZ DEFAULT now()
```

**Tabel: `project`**
```sql
id                  UUID PK
workspace_id        UUID FK → workspace NOT NULL
naam                VARCHAR(200) NOT NULL
opdrachtgever       VARCHAR(200) NOT NULL
locatie_omschrijving TEXT
type_leiding        VARCHAR(50)   -- elektriciteit/gas/water/telecom/warmte/overig
status              VARCHAR(50) DEFAULT 'concept'  -- concept/ontwerp/review/opgeleverd
aangemaakt_door_id  UUID FK → gebruiker
aangemaakt_op       TIMESTAMPTZ DEFAULT now()
gewijzigd_op        TIMESTAMPTZ DEFAULT now()
```

**Tabel: `locatie`**
```sql
id              UUID PK
project_id      UUID FK → project UNIQUE NOT NULL
startpunt_lon   FLOAT
startpunt_lat   FLOAT
eindpunt_lon    FLOAT
eindpunt_lat    FLOAT
bijgewerkt_op   TIMESTAMPTZ DEFAULT now()
```

**Tabel: `klic_upload`**
```sql
id              UUID PK
project_id      UUID FK → project NOT NULL
bestandsnaam    VARCHAR(500) NOT NULL
bestandspad     TEXT NOT NULL   -- pad op Railway volume
status          VARCHAR(50) DEFAULT 'geupload'  -- geupload/verwerkt/fout
foutmelding     TEXT
aantal_objecten INT
geupload_op     TIMESTAMPTZ DEFAULT now()
verwerkt_op     TIMESTAMPTZ
```

**Tabel: `klic_object`**
```sql
id              UUID PK
project_id      UUID FK → project NOT NULL
upload_id       UUID FK → klic_upload NOT NULL
klic_type       VARCHAR(50)   -- GAS/ELEKTRICITEIT/WATER/TELECOM/RIOOL/OVERIG
beheerder       VARCHAR(200)
geometrie       GEOMETRY(LINESTRING, 28992)
diepte_m        FLOAT
eigenschappen   JSONB
aangemaakt_op   TIMESTAMPTZ DEFAULT now()

INDEX: GIST(geometrie)
INDEX: (project_id)
```

**Tabel: `te_kruisen_object`**
```sql
id                  UUID PK
project_id          UUID FK → project UNIQUE NOT NULL
type                VARCHAR(50)   -- weg/water/spoor/waterkering/overig
naam                VARCHAR(200)
breedte_m           FLOAT
eisenprofiel_id     UUID FK → eisenprofiel
aanvullende_eisen   TEXT
bijgewerkt_op       TIMESTAMPTZ DEFAULT now()
```

**Tabel: `nieuwe_leiding`**
```sql
id                  UUID PK
project_id          UUID FK → project UNIQUE NOT NULL
materiaal           VARCHAR(50)   -- PE/staal/PVC/HDPE/overig
buitendiameter_mm   FLOAT
wanddikte_mm        FLOAT
max_trekkracht_kn   FLOAT
min_boogstraal_m    FLOAT
met_mantelbuis      BOOLEAN DEFAULT FALSE
bijgewerkt_op       TIMESTAMPTZ DEFAULT now()
```

**Tabel: `ontwerp`**
```sql
id              UUID PK
project_id      UUID FK → project UNIQUE NOT NULL
status          VARCHAR(50) DEFAULT 'concept'  -- concept/akkoord/waarschuwing/afkeur
boorcurve_wkt   TEXT   -- WKT LineString in WGS84
boorlengte_m    FLOAT
max_diepte_m    FLOAT
boogstraal_m    FLOAT
entry_angle_deg FLOAT
exit_angle_deg  FLOAT
aangemaakt_op   TIMESTAMPTZ DEFAULT now()
herberekend_op  TIMESTAMPTZ
```

**Tabel: `ontwerp_lengteprofiel`**
```sql
id          UUID PK
ontwerp_id  UUID FK → ontwerp NOT NULL
afstand_m   FLOAT NOT NULL
diepte_m    FLOAT NOT NULL
volgorde    INT NOT NULL

INDEX: (ontwerp_id, volgorde)
```

**Tabel: `conflict`**
```sql
id              UUID PK
ontwerp_id      UUID FK → ontwerp NOT NULL
klic_object_id  UUID FK → klic_object NOT NULL
klic_type       VARCHAR(50)
klic_beheerder  VARCHAR(200)
afstand_m       FLOAT NOT NULL
diepte_leiding_m FLOAT
ernst           VARCHAR(50)   -- info/waarschuwing/kritiek

INDEX: (ontwerp_id)
```

**Tabel: `output_document`**
```sql
id              UUID PK
project_id      UUID FK → project NOT NULL
workspace_id    UUID FK → workspace NOT NULL
type            VARCHAR(50)   -- pdf_tekening/dwg_tekening
bestandspad     TEXT NOT NULL
versie          INT DEFAULT 1
gegenereerd_op  TIMESTAMPTZ DEFAULT now()
```

### 5. Seed script (`app/core/seed.py`)

Aanroepen in lifespan bij elke start — idempotent (skip als al bestaat):

```python
async def seed_database(db: AsyncSession):
    # 1. Workspace aanmaken
    workspace = Workspace(naam="Inodus HDD", slug="inodus")

    # 2. Eisenprofielen aanmaken (workspace_id=None = globaal)
    eisenprofielen = [
        EisenProfiel(naam="RWS Rijksweg",
                     beheerder_type="RWS", object_type="RIJKSWEG",
                     min_diepte_m=3.0, beschermingszone_m=5.0, min_boogstraal_m=150.0),
        EisenProfiel(naam="Waterschap Waterkering",
                     beheerder_type="WATERSCHAP", object_type="WATERKERING",
                     min_diepte_m=5.0, beschermingszone_m=10.0, min_boogstraal_m=200.0),
        EisenProfiel(naam="Provincie Provinciale weg",
                     beheerder_type="PROVINCIE", object_type="PROVINCIALE_WEG",
                     min_diepte_m=2.0, beschermingszone_m=3.0, min_boogstraal_m=120.0),
        EisenProfiel(naam="Gemeente Gemeenteweg",
                     beheerder_type="GEMEENTE", object_type="GEMEENTEWEG",
                     min_diepte_m=1.2, beschermingszone_m=1.5, min_boogstraal_m=100.0),
    ]

    # 3. Admin gebruiker aanmaken
    # email + wachtwoord uit environment variabelen SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD
```

### 6. Frontend skelet

```
frontend/src/
├── main.tsx
├── App.tsx              React Router v6 setup
├── api/
│   └── client.ts        Axios instantie, base URL = /api/v1
├── pages/
│   └── Home.tsx         Redirect naar /login of /projecten
└── components/          Leeg — gevuld per sprint
```

Dependencies: react 18, react-router-dom v6, axios, @tanstack/react-query, leaflet, react-leaflet, shadcn/ui, tailwindcss, typescript

### 7. GitHub Actions — `deploy.yml`

```yaml
name: Deploy naar Railway

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: {node-version: '20'}

      # Frontend bouwen
      - run: npm ci
        working-directory: frontend
      - run: npm run build
        working-directory: frontend

      # Backend tests
      - uses: actions/setup-python@v5
        with: {python-version: '3.11'}
      - run: pip install -r requirements.txt && pytest tests/
        working-directory: backend

      # Deploy naar Railway
      - uses: railway/deploy-action@v1
        with:
          token: ${{ secrets.RAILWAY_TOKEN }}
          service: hdd-platform
```

**Secrets op GitHub (instellen in repository settings):**
- `RAILWAY_TOKEN` — Railway deploy token

### 8. Railway configuratie (handmatig éénmalig instellen)

1. Railway project aanmaken: `hdd-platform`
2. PostgreSQL plugin toevoegen → `DATABASE_URL` automatisch beschikbaar
3. Volume koppelen op `/storage`
4. Environment variabelen instellen:
   ```
   SECRET_KEY=<openssl rand -hex 32>
   STORAGE_BACKEND=local
   ENVIRONMENT=production
   SEED_ADMIN_EMAIL=admin@inodus.nl
   SEED_ADMIN_PASSWORD=<sterk wachtwoord>
   WORKSPACE_SLUG=inodus
   ```
5. Dockerfile als build bron instellen

### 9. DNS — `hdd.inodus.nl` (handmatig éénmalig instellen)

In Netlify DNS (zelfde DNS als `inodus.nl`):
```
hdd   CNAME   <railway-url>.railway.app
```

Railway regelt SSL automatisch via Let's Encrypt.

### 10. `.env.example`

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/hdd_platform
SECRET_KEY=change-me-in-development
STORAGE_PATH=./storage
ENVIRONMENT=development
SEED_ADMIN_EMAIL=admin@inodus.nl
SEED_ADMIN_PASSWORD=changeme
WORKSPACE_SLUG=inodus
```

---

## Data in / Data uit

**In:** geen (bootstrapping)
**Uit:** werkende omgeving lokaal + op Railway, health endpoint, DB schema compleet, seed data aanwezig

---

## Acceptatiecriteria

- [ ] `docker compose up` start postgres + backend + frontend zonder fouten
- [ ] `GET /api/v1/health` → `{"status": "ok", "db": "ok"}`
- [ ] Frontend laadt op `http://localhost:5173`
- [ ] Alembic migraties reproduceerbaar (`alembic downgrade base && alembic upgrade head`)
- [ ] Workspace tabel aanwezig met `workspace_id` op alle entiteiten
- [ ] Seed script: workspace + 4 eisenprofielen + admin gebruiker aangemaakt bij eerste start
- [ ] GitHub Actions pipeline groen op push naar main
- [ ] Applicatie bereikbaar op `hdd.inodus.nl` met geldig SSL certificaat
- [ ] `hdd.inodus.nl/api/v1/health` geeft `{"status": "ok"}` terug

---

## Modules geraakt

Alle modules — dit is de fundering.
