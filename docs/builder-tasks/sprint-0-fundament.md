# Builder Task — Sprint 0: Projectfundament

**Sprint:** 0 | **Duur:** 1 week | **Afhankelijkheden:** geen

---

## Doel

Alle infrastructuur staat zodat de Builder Agent direct met features kan beginnen. Geen features, alleen de basis.

---

## Wat te bouwen

### 1. Git repository structuur (aanwezig via CLAUDE.md)

```
/backend    → FastAPI applicatie
/frontend   → React/Vite applicatie
/docker     → docker-compose bestanden
/docs       → architectuurdocumenten
```

### 2. Docker Compose (`docker/docker-compose.yml`)

Services:
- `postgres` — PostgreSQL 16 + PostGIS 3.4, port 5432
- `redis` — Redis 7, port 6379 (ARQ job queue)
- `minio` — MinIO latest, ports 9000 (API) + 9001 (console)
- `backend` — FastAPI met hot-reload, port 8000
- `worker` — ARQ worker (zelfde image als backend)
- `frontend` — Vite dev server, port 5173

Volumes voor postgres en minio (data persistentie).
`backend` en `worker` wachten op `postgres` en `redis` (healthcheck).

### 3. Backend skelet (`/backend`)

Bestandsstructuur:
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app factory met lifespan
│   ├── config.py            # Pydantic v2 Settings (laadt .env)
│   ├── database.py          # SQLAlchemy 2.x async engine + session factory
│   ├── routers/
│   │   └── health.py        # GET /api/v1/health
│   ├── models/              # SQLAlchemy ORM modellen (leeg, gevuld in sprint 1+)
│   ├── schemas/             # Pydantic schemas (leeg, gevuld in sprint 1+)
│   └── services/            # Domeinservices (leeg, gevuld in sprint 1+)
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 0001_initial_schema.py  # Volledig initieel schema (zie architectuur sectie 3.2)
├── tests/
│   └── test_health.py
├── requirements.txt
├── .env.example
└── Dockerfile
```

**`app/main.py`:**
- FastAPI app met `lifespan` context manager
- Database connectie openen/sluiten in lifespan
- Router registreren: `/api/v1/health`
- Middleware: CORS (alle origins in development)
- Global exception handler

**`app/config.py`:**
- Pydantic BaseSettings
- Variabelen: `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `BGT_API_URL`, `ENVIRONMENT`

**`routers/health.py`:**
```python
GET /api/v1/health
Response: {"status": "ok", "db": "ok", "redis": "ok", "environment": "development"}
```
Controleer db en redis actief door een simpele query/ping.

**`requirements.txt` packages:**
- fastapi, uvicorn[standard]
- sqlalchemy[asyncio], asyncpg, alembic
- pydantic-settings
- redis[hiredis], arq
- python-jose[cryptography], passlib[bcrypt]
- lxml, shapely, pyproj
- boto3 (S3)
- ezdxf
- weasyprint
- jinja2
- structlog
- pytest, pytest-asyncio, httpx

### 4. Database schema — Alembic migratie `0001_initial_schema.py`

Maak alle tabellen aan zoals beschreven in architectuur sectie 3.2. Schema naam: `hdd`.

Tabellen (volgorde op basis van FK afhankelijkheden):
1. `hdd.gebruikers`
2. `hdd.eisenprofielen`
3. `hdd.eisenprofiel_regels`
4. `hdd.projecten`
5. `hdd.project_status_geschiedenis`
6. `hdd.locaties`
7. `hdd.klic_uploads`
8. `hdd.klic_objecten` (met PostGIS geometry kolom)
9. `hdd.bgt_objecten` (met PostGIS geometry kolom)
10. `hdd.dwg_uploads`
11. `hdd.kruisingsobjecten`
12. `hdd.nieuwe_leidingen`
13. `hdd.ontwerpen`
14. `hdd.ontwerp_lengteprofiel_punten`
15. `hdd.ontwerp_validaties`
16. `hdd.ontwerp_conflicten`
17. `hdd.berekeningen`
18. `hdd.output_jobs`
19. `hdd.output_documenten`
20. `hdd.async_jobs`

PostGIS extensie activeren: `CREATE EXTENSION IF NOT EXISTS postgis;`
Indices aanmaken op alle FK kolommen en geometry kolommen (GIST index).

### 5. Frontend skelet (`/frontend`)

```
frontend/
├── src/
│   ├── main.tsx
│   ├── App.tsx              # React Router setup
│   ├── api/
│   │   └── client.ts        # Axios instantie met base URL
│   ├── pages/
│   │   └── Home.tsx         # Lege homepage
│   └── components/          # Leeg, gevuld in sprint 1+
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

Dependencies:
- react 18, react-dom, react-router-dom v6
- axios, @tanstack/react-query
- leaflet, react-leaflet
- shadcn/ui (via CLI installatie)
- tailwindcss
- typescript

### 6. CI/CD (`/.github/workflows/ci.yml`)

Triggers: push op main, pull_request.

Jobs:
- `backend-test`: Python 3.11, `pip install -r requirements.txt`, `pytest tests/`
- `backend-lint`: `ruff check app/`
- `frontend-test`: Node 20, `npm ci`, `npm run test`
- `frontend-lint`: `npm run lint`
- `docker-build`: `docker compose build` (smoke check)

### 7. `.gitignore`

Backend: `__pycache__`, `.venv`, `.env`, `*.pyc`
Frontend: `node_modules`, `dist`
Docker: geen (docker-compose.yml wel in repo, .env niet)

---

## Data in / Data uit

**In:** geen (bootstrapping)
**Uit:** werkende lokale omgeving, health endpoint, lege frontend

---

## Acceptatiecriteria

- [ ] `docker compose up` start alle 6 services zonder fouten
- [ ] `GET /api/v1/health` → `{"status": "ok", "db": "ok", "redis": "ok"}`
- [ ] Frontend laadt op `http://localhost:5173` zonder console errors
- [ ] `alembic downgrade base && alembic upgrade head` werkt reproduceerbaar
- [ ] CI pipeline is groen op eerste commit
- [ ] `.env.example` bevat alle variabelen met placeholder waarden

---

## User Stories

Epic 1 (infrastructuur — geen directe user story, fundament voor alles)
