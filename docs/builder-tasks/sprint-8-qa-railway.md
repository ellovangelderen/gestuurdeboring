# Builder Task — Sprint 8: QA & Oplevering Railway

**Sprint:** 8 | **Duur:** 1 week | **Afhankelijkheden:** Sprint 7 compleet

---

## Doel

Volledige workflow end-to-end getest. Applicatie draait stabiel op `hdd.inodus.nl`. Klaar voor gebruik door 2–5 engineers.

---

## Wat te bouwen

### 1. End-to-end tests (`tests/e2e/`)

**`tests/e2e/test_volledige_workflow.py`:**

```python
async def test_volledige_hdd_workflow(client, db):
    """
    Stap 1:  Login als engineer
    Stap 2:  Project aanmaken
    Stap 3:  Locatie instellen (Haarlem testcoördinaten)
    Stap 4:  KLIC GML uploaden (fixture bestand in tests/fixtures/)
    Stap 5:  KLIC objecten ophalen → GeoJSON bevat objecten
    Stap 6:  Kruisingsobject instellen (RWS rijksweg)
    Stap 7:  Leiding instellen (PE-100, D=250mm)
    Stap 8:  Ontwerp genereren → status akkoord of waarschuwing
    Stap 9:  Lengteprofiel ophalen → bevat punten
    Stap 10: PDF genereren → HTTP 200, bytes > 10KB
    Stap 11: DWG genereren → HTTP 200, bytes > 1KB
    Stap 12: Bestanden downloaden → HTTP 200

    Assert: geen 4xx/5xx op enige stap
    Assert: ontwerp.boorlengte_m > 0
    Assert: PDF bevat %PDF magic bytes
    Assert: DWG inleesbaar door ezdxf
    """

async def test_twee_engineers_tegelijk(client_a, client_b, db):
    """
    Engineer A en engineer B loggen gelijktijdig in.
    Beide maken een project aan.
    Beide genereren een ontwerp.
    Assert: projecten zijn gescheiden, geen data-overlap.
    """
```

**`tests/e2e/test_auth_grenzen.py`:**

```python
async def test_geen_toegang_zonder_token():
    """Elk beveiligd endpoint → 401"""

async def test_workspace_isolatie():
    """Gebruiker kan geen projecten van andere workspace ophalen"""
```

Fixture bestanden:
- `tests/fixtures/klic_test.gml` — klein IMKL 2.1 fixture (5–10 objecten, anonymized)

### 2. Performance controles

Meten en loggen — geen harde eisen maar signaleren als te traag:

```python
# Voeg timing toe aan alle routes via middleware
@app.middleware("http")
async def log_request_timing(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000
    if duration_ms > 500:
        logger.warning("Trage request", path=request.url.path, duration_ms=duration_ms)
    return response
```

Controleer via logging:
- Lijst projecten < 200ms
- KLIC upload (5 bestanden) < 30 seconden
- Ontwerp genereren < 5 seconden
- PDF genereren < 5 seconden

### 3. Security hardening

**Bestandsupload validatie:**
```python
# Controleer magic bytes (eerste bytes), niet alleen extensie
def valideer_gml_bestand(bestand: bytes) -> bool:
    """Eerste bytes moeten XML zijn: <?xml of <IMKL"""

MAX_UPLOAD_GROOTTE = 50 * 1024 * 1024  # 50 MB
MAX_BESTANDEN_PER_UPLOAD = 20
```

**CORS productie:**
```python
# In production:
allow_origins = [settings.FRONTEND_URL]  # "https://hdd.inodus.nl"
# In development:
allow_origins = ["http://localhost:5173"]
```

**Input validatie — Pydantic velden:**
```python
class ProjectAanmaken(BaseModel):
    naam: str = Field(min_length=1, max_length=200)
    opdrachtgever: str = Field(min_length=1, max_length=200)
    locatie_omschrijving: str | None = Field(default=None, max_length=1000)
```

**Structured logging:**
```python
import structlog
# JSON format in production, console format in development
# Log: request method, path, status_code, duration_ms, user_id, workspace_id
```

**Geen stack traces in productie:**
```python
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error("Onverwachte fout", exc_info=exc, path=str(request.url))
    if settings.ENVIRONMENT == "production":
        return JSONResponse(status_code=500,
            content={"detail": "Interne fout — neem contact op met Inodus"})
    raise exc
```

### 4. Railway productie verificatie

Controleer checklist op `hdd.inodus.nl`:

```
[ ] https://hdd.inodus.nl bereikbaar (HTTPS, geen HTTP redirect loop)
[ ] https://hdd.inodus.nl/api/v1/health → {"status": "ok", "db": "ok"}
[ ] Loginpagina laadt
[ ] Admin kan inloggen (seed account)
[ ] Project aanmaken werkt
[ ] KLIC upload werkt (test met klein fixture bestand)
[ ] Ontwerp genereren werkt
[ ] PDF downloaden werkt
[ ] DWG downloaden werkt
[ ] Railway volume persistent (download na restart nog beschikbaar)
[ ] PostgreSQL connectie stabiel
[ ] GitHub Actions: push naar main → automatisch gedeployed binnen 3 minuten
```

### 5. Monitoring instellen op Railway

- Railway metrics: CPU, geheugen, requests/min
- Database connections: max 10 simultane connecties instellen in SQLAlchemy pool
- Alert instellen in Railway als service crasht (via Railway notifications → email)

### 6. Gebruikersacceptatietest (UAT) checklist

Doorloop met minstens 1 engineer van de klant:

```
[ ] Inloggen op hdd.inodus.nl
[ ] Project aanmaken (eigen projectnaam)
[ ] Locatie instellen via kaart (eigen locatie)
[ ] KLIC GML uploaden (eigen KLIC aanvraag)
[ ] KLIC leidingen zichtbaar op kaart
[ ] Kruisingsobject instellen
[ ] Ontwerp genereren → boorcurve zichtbaar
[ ] Lengteprofiel bekijken
[ ] Hoeken aanpassen + herberekenen
[ ] PDF downloaden + openen → titelblok correct
[ ] DWG downloaden + openen in AutoCAD/librecad → lagen correct
[ ] Bevindingen documenteren
```

---

## Acceptatiecriteria iteratie 1 (definitief)

Uit CLAUDE.md — alle moeten groen zijn voor oplevering:

- [ ] Engineer kan inloggen op `hdd.inodus.nl`
- [ ] Project aanmaken, KLIC GML uploaden, leidingen zien op kaart
- [ ] Start- en eindpunt vastleggen op kaart
- [ ] Te kruisen object en eisenprofiel selecteren
- [ ] Automatisch berekende boorcurve zien (bovenaanzicht + lengteprofiel)
- [ ] Conflicten zien als markeringen op kaart
- [ ] Parameters handmatig aanpassen en herberekenen
- [ ] PDF tekening downloaden
- [ ] DWG tekening downloaden
- [ ] Twee engineers kunnen gelijktijdig werken (workspace-isolatie)
- [ ] End-to-end test groen in CI
- [ ] Geen kritieke beveiligingsproblemen

---

## Geen scope-uitbreiding

Features die in deze sprint worden gesignaleerd maar NIET geïmplementeerd:
- BGT achtergrondlaag → iteratie 2
- Werkplan → iteratie 2
- Berekeningen → iteratie 2/3
- Gebruikersrollen → iteratie 2
- Versiebeheer ontwerp → iteratie 2
