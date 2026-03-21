# Backlog — Security & Code Quality Review
**Datum: 21 maart 2026**
**Bron: OWASP Top 10 2021 assessment + Code Review (verse checkout)**

---

## Prioriteit: MUST FIX (vóór productie)

### SEC-1 — File upload size limit
**Bron:** OWASP A04 / Code Review #3
**Ernst:** 🔴 HIGH
**Waar:** `router.py:902` (KLIC upload), `router.py:1771` (werkplan afbeelding)
**Probleem:** Geen max file size check. Een gebruiker kan een multi-GB bestand uploaden → server crash / disk vol.
**Fix:** Check `file.size` vóór schrijven. Max 50MB voor KLIC, 10MB voor afbeeldingen.
```python
if klic_zip.size and klic_zip.size > 50_000_000:
    raise HTTPException(413, "Bestand te groot (max 50MB)")
```
**Effort:** Klein (15 min)

---

### SEC-2 — Logging toevoegen
**Bron:** OWASP A09 / Code Review #13
**Ernst:** 🔴 HIGH
**Waar:** Hele applicatie — slechts 5 logging statements
**Probleem:** Geen auth failure logging (brute force onzichtbaar), geen request logging, geen error logging. Bij productie-issues is debugging onmogelijk.
**Fix:**
- Auth failures loggen in `auth.py`
- Request logging middleware (method, path, status, duration)
- Structured JSON logging voor Railway
- `logger.exception()` bij alle `except Exception` blocks (nu 38× stille catches)
**Effort:** Middel (2-3 uur)

---

### SEC-3 — tifffile + numpy in requirements
**Bron:** Code Review #15
**Ernst:** 🔴 HIGH
**Waar:** `requirements.txt` — commented out
**Probleem:** `app/geo/ahn5.py` importeert `tifffile` en `numpy` direct. Op Railway zonder deze deps crasht AHN5 maaiveld ophalen.
**Fix:** Uncomment in requirements.txt of maak import optioneel met fallback.
**Effort:** Klein (5 min)

---

## Prioriteit: SHOULD FIX (korte termijn)

### SEC-4 — Rate limiting op login
**Bron:** OWASP A04 / A07
**Ernst:** 🟠 MEDIUM
**Waar:** `auth.py`
**Probleem:** Onbeperkt wachtwoord raden mogelijk. Geen lockout na N pogingen.
**Fix:** `slowapi` of custom middleware: max 10 pogingen per IP per minuut.
**Effort:** Klein (30 min)

---

### SEC-5 — CSRF bescherming
**Bron:** OWASP A04 / Code Review #2
**Ernst:** 🟠 MEDIUM
**Waar:** Alle 20 POST `Form(...)` routes
**Probleem:** Geen CSRF token op forms. HTTPBasic mitigeert dit deels (credentials per request, niet cookie-based), maar een gerichte aanval is mogelijk.
**Fix:** CSRF middleware of `starlette-csrf` package. Alternatief: SameSite cookie + Referer check.
**Effort:** Middel (1-2 uur)

---

### SEC-6 — Dependency lock file
**Bron:** OWASP A06 / A08
**Ernst:** 🟡 LOW
**Waar:** `requirements.txt`
**Probleem:** Geen pinned hashes. `pip install` kan andere versies installeren. Supply chain risico.
**Fix:** `pip-compile` → `requirements.lock` met hashes. Of `poetry.lock`.
**Effort:** Klein (15 min)

---

### SEC-7 — Auth failure audit logging
**Bron:** OWASP A09
**Ernst:** 🟠 MEDIUM
**Waar:** `auth.py`
**Probleem:** Mislukte login pogingen worden niet gelogd. Brute force aanvallen zijn onzichtbaar.
**Fix:** Log username + IP bij 401 responses.
**Effort:** Klein (15 min)

---

### QUA-1 — Split god router (1833 regels)
**Bron:** Code Review #1
**Ernst:** 🟠 MEDIUM
**Waar:** `app/order/router.py` — 1833 regels, 22 functies >40 regels
**Probleem:** Ononderhoudbaar. 17+ domeinen in 1 bestand. Bug-risico bij wijzigingen.
**Fix:** Split in sub-routers:
- `routes/cockpit.py` (order lijst, stats, CSV, statusmail)
- `routes/trace.py` (trace invoer, varianten)
- `routes/brondata.py` (KLIC, maaiveld, doorsneden, intrekkracht)
- `routes/analyse.py` (conflictcheck, sleufloze, GWSW, topotijdreis, vergunning, sonderingen)
- `routes/documents.py` (DXF, PDF, werkplan, factuur)
- `routes/asbuilt.py` (as-built invoer)
**Effort:** Groot (4-6 uur, maar geen functionaliteitswijziging)

---

### QUA-2 — Temp file cleanup met context manager
**Bron:** Code Review #5
**Ernst:** 🟡 MEDIUM
**Waar:** `pdf_generator.py` — 12 temp file operaties
**Probleem:** Bij crash tussen aanmaken en cleanup blijven temp files staan. Kan disk vullen op Railway.
**Fix:** `tempfile.TemporaryDirectory()` als context manager, of `try/finally` pattern.
**Effort:** Klein (30 min)

---

### QUA-3 — Alembic migraties bijwerken
**Bron:** Code Review #6
**Ernst:** 🟠 MEDIUM
**Waar:** `alembic/versions/` — niet up-to-date
**Probleem:** Kolommen `variant` (TracePunt), `revisie` (Boring), tabel `asbuilt_punten` zijn handmatig toegevoegd. Bij fresh deploy op Railway ontbreken ze (tenzij `create_all` alles aanmaakt).
**Fix:** Alembic migratie genereren: `alembic revision --autogenerate`. Of vertrouwen op `create_all` (huidige aanpak, werkt maar is niet best practice).
**Effort:** Middel (1 uur)

---

### QUA-4 — Deprecated `on_startup` event
**Bron:** Code Review #10
**Ernst:** 🟡 LOW
**Waar:** `main.py:57`
**Probleem:** `@app.on_event("startup")` is deprecated in FastAPI 0.95+.
**Fix:** Gebruik `lifespan` context manager.
**Effort:** Klein (15 min)

---

## Prioriteit: NICE TO HAVE (langere termijn)

### QUA-5 — Pydantic schemas voor input validatie
**Bron:** Code Review #12
**Ernst:** 🟡 LOW
**Waar:** `app/order/schemas.py` (leeg)
**Probleem:** Alle input via `Form(...)` zonder type/range validatie. Geen API documentatie.
**Fix:** Pydantic models per route. Geeft type checking + Swagger docs gratis.
**Effort:** Groot (4+ uur)

---

### QUA-6 — Fetch order+boring dependency
**Bron:** Code Review #8
**Ernst:** 🟡 LOW
**Waar:** 29× `fetch_order` + 24× `fetch_boring` calls
**Probleem:** Verbose boilerplate in elke route.
**Fix:** Gecombineerde FastAPI dependency.
**Effort:** Middel (1 uur)

---

### SEC-8 — IDOR ownership check
**Bron:** OWASP A01
**Ernst:** 🟡 LOW (2 users, zelfde workspace)
**Waar:** `fetch_order()` in `dependencies.py`
**Probleem:** Elke ingelogde user kan elke order benaderen via UUID. Geen workspace filtering.
**Fix:** `fetch_order` checkt `order.workspace_id == get_workspace_id(user)`.
**Effort:** Klein (15 min)

---

### SEC-9 — File type magic bytes check
**Bron:** OWASP A08
**Ernst:** 🟡 LOW
**Waar:** KLIC upload
**Probleem:** Alleen extensie check (`.zip/.xml/.gml`), geen magic bytes verificatie.
**Fix:** Check eerste bytes: ZIP=`PK\x03\x04`, XML=`<?xml`, GML=`<?xml`.
**Effort:** Klein (15 min)

---

### QUA-7 — Audit trail
**Bron:** OWASP A09
**Ernst:** 🟡 LOW
**Waar:** Geen
**Probleem:** Geen log van wie welke order/boring wanneer heeft gewijzigd.
**Fix:** `updated_by` + `updated_at` kolommen, of apart audit log tabel.
**Effort:** Middel (2 uur)

---

### QUA-8 — OSM tile caching
**Bron:** Code Review #7
**Ernst:** 🟡 LOW
**Waar:** `pdf_generator.py` — 21+ tiles per PDF
**Probleem:** Bij veel PDF generatie kan OSM rate limiten.
**Fix:** Lokale tile cache (filesystem of in-memory met TTL).
**Effort:** Middel (1-2 uur)

---

## Overzicht per prioriteit

| Prio | ID | Item | Status |
|------|-----|------|--------|
| 🔴 MUST | SEC-1 | File upload size limit | ✅ DONE |
| 🔴 MUST | SEC-2 | Logging toevoegen | ✅ DONE |
| 🔴 MUST | SEC-3 | tifffile/numpy in requirements | ✅ DONE |
| 🟠 SHOULD | SEC-4 | Rate limiting login | ✅ DONE |
| 🟠 SHOULD | SEC-5 | CSRF bescherming | Open |
| 🟠 SHOULD | SEC-6 | Dependency lock file | ✅ DONE |
| 🟠 SHOULD | SEC-7 | Auth failure logging | ✅ DONE (in SEC-2) |
| 🟠 SHOULD | QUA-1 | Split god router | Open |
| 🟠 SHOULD | QUA-2 | Temp file cleanup | ✅ DONE |
| 🟠 SHOULD | QUA-3 | Alembic migraties | Open |
| 🟡 NICE | QUA-4 | Deprecated on_startup | ✅ DONE |
| 🟡 NICE | QUA-5 | Pydantic schemas | 4+ uur |
| 🟡 NICE | QUA-6 | Fetch dependency | 1 uur |
| 🟡 NICE | SEC-8 | IDOR ownership check | 15 min |
| 🟡 NICE | SEC-9 | Magic bytes check | 15 min |
| 🟡 NICE | QUA-7 | Audit trail | 2 uur |
| 🟡 NICE | QUA-8 | OSM tile caching | 1-2 uur |
| 🟠 BUG | BG-1 | Download bestanden zonder extensie | ✅ DONE |
| 🟠 BUG | BG-2 | Railway 500 ontbrekende DB kolommen | ✅ DONE (startup migraties) |

**Totaal MUST FIX effort: ~3 uur**
**Totaal SHOULD FIX effort: ~8-10 uur**
