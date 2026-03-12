# Builder Task — Sprint 9: Integratie & QA

**Sprint:** 9 | **Duur:** 1.5 week | **Afhankelijkheden:** Sprint 8 compleet

---

## Doel

Volledige workflow end-to-end getest. Performance optimalisaties. Security hardening. Productie Docker Compose klaar. UAT-voorbereiding.

---

## Wat te bouwen

### 1. End-to-end tests (`tests/e2e/`)

Gebruik pytest + httpx voor backend E2E (tegen echte database), en optioneel Playwright voor frontend.

**`tests/e2e/test_volledige_workflow.py`:**

```python
async def test_volledige_hdd_workflow(client, db):
    """
    Stap 1: Login als werkvoorbereider
    Stap 2: Project aanmaken
    Stap 3: Locatie instellen (Haarlem testcoördinaten)
    Stap 4: KLIC GML uploaden (fixture bestand)
    Stap 5: BGT ophalen (gemocked PDOK API)
    Stap 6: Kruisingsobject instellen (RWS rijksweg)
    Stap 7: Ontwerp genereren
    Stap 8: Ontwerp accorderen
    Stap 9: Berekeningen uitvoeren (sterkte + intrekkracht)
    Stap 10: Output genereren (PDF + DWG)
    Stap 11: PDF downloaden → HTTP 200, content-type pdf
    Stap 12: DWG downloaden → HTTP 200
    Assert: alle stappen geven geen 4xx/5xx
    Assert: PDF bestandsgrootte > 10KB
    Assert: DWG kan worden ingelezen door ezdxf
    """
```

**`tests/e2e/test_autorisatie.py`:**

```python
async def test_rol_toegang():
    """
    Werkvoorbereider kan GEEN ontwerp accorderen → 403
    Engineer kan WEL ontwerp accorderen
    Niet-beheerder kan GEEN eisenprofiel aanmaken → 403
    Beheerder kan alles
    Uitgelogde gebruiker krijgt 401 op alle beveiligde endpoints
    """
```

### 2. Performance optimalisaties

**Database indices controleren (`alembic/versions/0002_performance_indices.py`):**

```sql
-- Veelgebruikte queries optimaliseren
CREATE INDEX idx_projecten_status ON hdd.projecten(status);
CREATE INDEX idx_projecten_aangemaakt_door ON hdd.projecten(aangemaakt_door_id);
CREATE INDEX idx_klic_objecten_project ON hdd.klic_objecten(project_id);
CREATE INDEX idx_klic_objecten_type ON hdd.klic_objecten(klic_type);
CREATE INDEX idx_klic_objecten_geometrie ON hdd.klic_objecten USING GIST(geometrie);
CREATE INDEX idx_bgt_objecten_geometrie ON hdd.bgt_objecten USING GIST(geometrie);
CREATE INDEX idx_ontwerpen_project ON hdd.ontwerpen(project_id, is_huidig);
CREATE INDEX idx_output_documenten_project ON hdd.output_documenten(project_id);
```

**N+1 queries elimineren:**
- Review alle SQLAlchemy queries in services
- Gebruik `selectinload()` of `joinedload()` voor gerelateerde objecten
- Stel `echo=True` in development in en analyseer SQL logs

**API responstijden meten:**
- Voeg timing middleware toe: log alle requests > 200ms
- Target: alle endpoints < 500ms (excl. async jobs)

### 3. Foutafhandeling hardening

**ARQ workers — retry logica:**
```python
# Alle workers:
max_tries = 3
retry_delay = 30  # seconden tussen pogingen

# Bij definitieve fout (max retries bereikt):
# - Update job status naar 'fout'
# - Stuur foutmelding naar structured log
# - Gebruiker ziet foutmelding bij status polling
```

**Gebruikersvriendelijke foutmeldingen:**
```python
# app/main.py — global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    if settings.ENVIRONMENT == "production":
        # Log stack trace intern, stuur generieke melding
        logger.error("Onverwachte fout", exc_info=exc, path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Er is een interne fout opgetreden. Probeer het opnieuw."}
        )
    else:
        raise exc  # In development: toon volledige stack trace
```

**Structured logging (`app/logging.py`):**
```python
import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)

# Elke API request logt: method, path, status_code, duration_ms, user_id
```

### 4. Security checklist

**Bestandsupload validatie (`app/services/file_service.py`):**
```python
TOEGESTANE_KLIC_MIMETYPES = {'text/xml', 'application/xml', 'application/gml+xml'}
TOEGESTANE_DWG_MIMETYPES = {'image/vnd.dwg', 'application/acad', 'application/octet-stream'}
MAX_KLIC_BESTANDSGROOTTE = 50 * 1024 * 1024   # 50 MB
MAX_DWG_BESTANDSGROOTTE = 100 * 1024 * 1024   # 100 MB

def valideer_klic_upload(file: UploadFile):
    if file.content_type not in TOEGESTANE_KLIC_MIMETYPES:
        raise HTTPException(422, "Alleen .gml bestanden zijn toegestaan")
    # Controleer ook magic bytes (eerste bytes van bestand)
```

**S3 pre-signed URLs:**
```python
def genereer_download_url(s3_pad: str, ttl_seconden: int = 3600) -> str:
    return s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': settings.S3_BUCKET, 'Key': s3_pad},
        ExpiresIn=ttl_seconden
    )
# Nooit publieke buckets. Bucket ACL = private.
```

**CORS productie configuratie:**
```python
# In production: alleen eigen domein
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],  # bijv. https://hdd.inodus.nl
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**SQL injection:** SQLAlchemy ORM + parameterized queries — geen raw SQL strings met f-strings.

**Input validatie:** Alle Pydantic schemas valideren maximale lengtes:
```python
class ProjectAanmaken(BaseModel):
    naam: str = Field(min_length=1, max_length=200)
    opdrachtgever: str = Field(min_length=1, max_length=200)
```

### 5. Docker productie configuratie

**`docker/docker-compose.prod.yml`:**

```yaml
services:
  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl  # SSL certificaten
    depends_on: [backend, frontend]

  backend:
    build: ../backend
    environment:
      - ENVIRONMENT=production
    env_file: .env.prod
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2

  worker:
    build: ../backend
    command: arq app.workers.settings.WorkerSettings
    env_file: .env.prod

  postgres:
    image: postgis/postgis:16-3.4
    volumes: [postgres_data:/var/lib/postgresql/data]
    env_file: .env.prod
    # Geen externe port mapping in productie!

  redis:
    image: redis:7-alpine
    # Geen externe port mapping in productie!

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    volumes: [minio_data:/data]
    # Geen externe port mapping in productie (alleen via nginx)
```

**`docker/nginx.conf`:**
- Frontend bestanden serveren (static build)
- Backend proxy naar `backend:8000`
- SSL termination
- Gzip compressie
- Security headers: `X-Frame-Options`, `X-Content-Type-Options`, `HSTS`

**Database backup cron:**
```bash
# docker/backup.sh — dagelijkse pg_dump naar S3
#!/bin/bash
DATUM=$(date +%Y%m%d_%H%M%S)
pg_dump $DATABASE_URL | gzip | aws s3 cp - s3://$BACKUP_BUCKET/backups/hdd_$DATUM.sql.gz
```

Cron entry in docker-compose.prod.yml als aparte `backup` service met `ofelia` scheduler.

**`.env.prod.example`:**
```env
DATABASE_URL=postgresql+asyncpg://postgres:WIJZIG_DIT@postgres:5432/hdd_platform
SECRET_KEY=WIJZIG_DIT_LANGE_RANDOM_STRING
REDIS_URL=redis://redis:6379
S3_ENDPOINT=http://minio:9000
S3_BUCKET=hdd-platform
S3_ACCESS_KEY=WIJZIG_DIT
S3_SECRET_KEY=WIJZIG_DIT
BGT_API_URL=https://api.pdok.nl/lv/bgt/ogc/v1_0
FRONTEND_URL=https://hdd.inodus.nl
OPENAI_API_KEY=sk-...
SEED_ADMIN_EMAIL=admin@inodus.nl
SEED_ADMIN_PASSWORD=WIJZIG_DIT
ENVIRONMENT=production
```

### 6. Frontend productie build

**`frontend/Dockerfile.prod`:**
```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx-frontend.conf /etc/nginx/conf.d/default.conf
```

**`frontend/nginx-frontend.conf`:**
- SPA routing: alle routes → `index.html`
- Gzip voor JS/CSS/HTML

### 7. CI/CD uitbreiden (`.github/workflows/ci.yml`)

Extra job: `deploy` (alleen op push naar `main`):
- Docker build + push naar container registry (GitHub Packages)
- SSH naar productie VPS
- `docker compose -f docker-compose.prod.yml pull && docker compose up -d`

---

## Acceptatiecriteria

- [ ] End-to-end test volledige workflow is groen in CI
- [ ] Alle Must Have user stories uit Epics 1-7 zijn geïmplementeerd
- [ ] Geen openstaande kritieke bugs
- [ ] Alle API endpoints responderen in < 500ms (excl. async jobs)
- [ ] Geen N+1 queries (geverifieerd via SQL logging)
- [ ] Productie Docker Compose start zonder fouten op VPS
- [ ] SSL certificaat aanwezig, HTTP redirect naar HTTPS
- [ ] Security headers aanwezig op alle responses
- [ ] Pre-signed S3 URLs gebruikt voor alle downloads
- [ ] Database backup script werkt (test: backup aanmaken en terugzetten)
- [ ] Structured logging in JSON formaat

---

## UAT checklist (voor opdrachtgever)

Doorloop met 2 werkvoorbereiders en 1 engineer:

1. Werkvoorbereider logt in en maakt project aan
2. Locatie instellen via kaart + adreszoeken
3. KLIC GML bestanden uploaden (echte KLIC aanvraag of anonymized fixture)
4. BGT ophalen
5. Kruisingsobject instellen
6. Ontwerp genereren en beoordelen
7. Engineer accordeert ontwerp
8. Berekeningen uitvoeren
9. PDF + DWG downloaden en controleren in AutoCAD
10. Werkplan downloaden en controleren

Bevindingen documenteren en verwerken vóór go-live.

---

## User Stories

Alle Must Have stories uit Epics 1-7 (volledige lijst in `docs/architecture.md`).
