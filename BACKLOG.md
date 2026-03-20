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

*Aangemaakt op 2026-03-20 — Inodus / LeanAI Platform*
