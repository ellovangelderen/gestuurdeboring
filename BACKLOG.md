# BACKLOG.md — HDD Ontwerp Platform

**Project:** GBT / HDD Platform
**Fase:** Productie-hardening
**Aangemaakt:** 2026-03-20
**Status:** Draait op Railway, productiedata geladen (356 orders)

---

## Huidige staat

| Metriek | Waarde |
|---------|--------|
| Orders in productie | 356 |
| Boringen | 545 |
| Gebruikers | 2 (martien, visser) |
| Deploy | Railway via Dockerfile |
| Database | SQLite (lokaal, GEEN persistent volume) |

---

## Kritiek — Nu fixen

| # | Item | Ernst | Status |
|---|------|-------|--------|
| K-01 | **Persistent volume voor SQLite** — data gaat verloren bij redeploy | KRITIEK | TODO |
| K-02 | **Alembic migraties in startup** — Procfile/CMD moet `alembic upgrade head` draaien | KRITIEK | TODO |
| K-03 | **PDF generatie** — WeasyPrint + CairoSVG + Pillow enabled via Dockerfile | KRITIEK | DONE (deployed) |
| K-04 | **Kwetsbare dependencies** — jinja2 3.1.4 (CVE), python-multipart 0.0.12 (CVE) | KRITIEK | TODO |

---

## Hoog — Voor productie

| # | Item | Prio | Status |
|---|------|------|--------|
| H-01 | CSRF bescherming op alle POST formulieren | Must | TODO |
| H-02 | Security headers (X-Frame-Options, CSP, HSTS) | Must | TODO |
| H-03 | Rate limiting op login (HTTP Basic brute force) | Must | TODO |
| H-04 | Custom error pagina's (404/500 — nu raw JSON) | Must | TODO |
| H-05 | Logging + audit trail (wie wijzigde wat) | Must | TODO |
| H-06 | Bare `except: pass` vervangen door proper error handling (20+ locaties) | Must | TODO |
| H-07 | Database backup strategie (nachtelijke kopie + Excel export) | Must | TODO |
| H-08 | HTTPS redirect in productie | Should | TODO |
| H-09 | Session management (HTTP Basic stuurt credentials bij elk request) | Should | TODO |
| H-10 | File upload limieten (grootte, type whitelist) | Should | TODO |

---

## Medium — Verbetering

| # | Item | Prio | Status |
|---|------|------|--------|
| M-01 | Import: Revisie sheet ook importeren (1258 rijen) | Should | TODO |
| M-02 | Geometry conversie errors tonen i.p.v. stil falen | Should | TODO |
| M-03 | Health check uitbreiden (DB connectivity, disk space) | Should | TODO |
| M-04 | Input validatie op alle Form() velden (lengte, type, whitelist) | Should | TODO |
| M-05 | PDF temp files cleanup (worden nu niet altijd opgeruimd) | Should | TODO |
| M-06 | Tabel full-width op breed scherm | Should | DONE |
| M-07 | Boringen badges wrappen na 4 | Should | DONE |
| M-08 | Excel import: URL detectie in locatie kolom | Should | DONE |
| M-09 | Alembic env.py: DATABASE_URL fallback als niet gezet | Should | TODO |
| M-10 | Tests uitbreiden: route/integratie tests (nu alleen unit tests) | Should | TODO |

---

## Laag — Nice to have

| # | Item | Prio | Status |
|---|------|------|--------|
| L-01 | Static files cache busting (hash in filename) | Could | TODO |
| L-02 | Environment-specifieke configuratie (debug, DB threading) | Could | TODO |
| L-03 | Legacy project routes opruimen of deprecaten | Could | TODO |
| L-04 | Werkplan afbeeldingen opruimen (orphaned files) | Could | TODO |
| L-05 | API documentatie (OpenAPI/Swagger aanpassen) | Could | TODO |

---

## Architectuur documentatie

Zie `docs/architecture.md` voor:
- Tech stack
- Deployment instructies
- Datamodel
- Routes overzicht
- Excel import formaat
- Gebruikers
- Backup & herstel

---

## Volgende stappen (prioriteit)

```
1. K-01: Persistent volume configureren op Railway
2. K-02: Alembic in startup CMD
3. K-04: Dependencies updaten (jinja2, python-multipart)
4. H-06: Bare except:pass → logging
5. H-01: CSRF bescherming
6. H-04: Error pagina's
7. H-07: Backup strategie
```

---

## Bug log

| # | Bug | Oorzaak | Fix | Status |
|---|-----|---------|-----|--------|
| B-01 | Locatie kolom toont volledige Google Maps URLs, tabel breekt | Import sloeg kolom N (URL) op als locatie i.p.v. adres | URL detectie + adres uit ordernaam parsen | FIXED |
| B-02 | Boringen badges duwen kolommen van scherm bij 14+ boringen | `white-space: nowrap` op boringen kolom | `flex-wrap` + `max-width: 160px` | FIXED |
| B-03 | Dashboard tabel niet full-width op brede schermen | `main { max-width: 1200px }` in CSS | Gewijzigd naar `max-width: 100%` | FIXED |
| B-04 | Deploy FAILED: `$PORT is not a valid integer` | railway.json `startCommand` overschrijft Dockerfile CMD, `$PORT` wordt niet geëxpandeerd | startCommand verwijderd, Dockerfile CMD doet alles | FIXED |
| B-05 | Deploy FAILED: healthcheck na Dockerfile switch | Gevolg van B-04, app kon niet starten | Opgelost met B-04 fix | FIXED |
| B-06 | Alembic.ini wijst naar `./hdd.db` i.p.v. Railway volume `/data/` | Hardcoded pad in alembic.ini | env.py overschrijft URL met settings.DATABASE_URL | FIXED |

---

*Aangemaakt op 2026-03-20 — Inodus / LeanAI Platform*
