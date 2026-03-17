# Builder Agent — hdd-platform v3 (Martien Luijben)
# Project: HDD Ontwerp Platform · GestuurdeBoringTekening.nl
# Hosted: hdd.inodus.nl · Aanpak: walking skeleton + backlog
# Updated: 2026-03-17 — Order→Boring datamodel

## STACK
- Frontend:    HTMX + Jinja2 + Alpine.js (geen build tool, server-side HTML)
- Kaart:       Leaflet + OpenStreetMap + PDOK lagen
- Coördinaten: pyproj EPSG:28992 (RD↔WGS84), altijd 2 decimalen
- Backend:     Python FastAPI (modulaire monoliet)
- Database:    SQLite + SQLAlchemy (geen server nodig, Alembic migraties)
- PDF:         WeasyPrint + Jinja2 templates
- DXF:         ezdxf, uitvoer R2013 (AC1027)
- Auth:        FastAPI HTTPBasic, gebruikers in .env
- Hosting:     Railway autodeploy (git push → live), geen Docker
- AI tekst:    Anthropic Claude API (backlog 1 werkplan generator)
- Email:       SMTP (backlog 4 statusmail)
- Facturatie:  SnelStart REST API (backlog 13)

## PROJECTSTRUCTUUR
app/
  core/         workspace middleware, auth, config, db sessie
  order/        order CRUD + cockpit (vervangt project/)
  boring/       boring CRUD per order, type B/N/Z/C
  geo/          KLIC GML parser, geometrie, conflictcheck
  rules/        eisenprofielen seed (hardcoded skeleton)
  design/       boorprofiel geometrie engine (5-segment + boogzinker)
  calculations/ Sigma berekeningen (backlog 17)
  documents/    PDF generator + DXF generator + werkplan generator
  ai_assist/    Claude API werkplan (backlog 1)
  statusmail/   wekelijkse statusmail generator (backlog 4)
  drive/        Google Drive sync
  api/          FastAPI routes

## CONVENTIES
- Routes:        /orders, /orders/{id}, /orders/{id}/boringen/{volgnr}
- Errors:        { "error": "...", "code": "...", "field": "..." }
- Naamgeving:    snake_case Python, kebab-case HTML/CSS
- Migraties:     altijd Alembic — nooit raw ALTER TABLE
- Workspace:     elke query filtert op workspace_id (middleware)
- Gebruik nooit: tenant · klant · organisatie — altijd "workspace"
- Coördinaten:   altijd RD New EPSG:28992, 2 decimalen
- Kaart:         oriëntatie only — RD tangentpunten zijn echte invoer
- Bestanden:     {ordernummer}-{volgnummer:02d}-rev.{n}.dxf/pdf

## DATAMODEL KERNREGELS
- Order is het hoofdniveau. Boring[] is een child van Order.
- Boring heeft volgnummer (01, 02, 03...) en type (B/N/Z/C).
- KLICUpload zit op Order-niveau, niet op Boring.
- BoringKLIC koppeltabel: boring verwijst naar specifieke KLIC-versie.
- Type C (calculatie): alleen Berekening + Document. Geen TracePunten, DXF, PDF tekening.
- Boogzinker (Z): booghoek + stand als parameters. 1 ARC in DXF, geen 5 segmenten.
- B/N: intreehoek, uittreehoek, Rv_in, Rv_uit, L_hor als parameters.

## DOMEINREGELS
- Override principe: elke complexe stap heeft handmatige fallback — altijd
- KLIC: dieptes zijn ALTIJD onbetrouwbaar — altijd waarschuwen bij conflictcheck
- KLIC versioning: meldingnummer + versie. Engineer kiest welke versie per boring.
- Berekeningen: altijd expliciete Python code — nooit via AI-prompting
- DXF laagnamen: exact conform HDD28 referentie (sectie 7 CLAUDE.md)
- Auth: USER_TEST_PASSWORD alleen actief als ENV=development
- Tekenaar: default "martien", wijzigbaar per order
- Status enum: order_received / in_progress / delivered / waiting_for_approval / done / cancelled

## BUITEN SCOPE — nooit bouwen
- React, Vue, Next.js, of enig JS framework
- Docker of pipeline files
- MySQL of PostgreSQL
- JWT tokens
- Offertegenerator (calculatie is WEL in scope, offerte NIET)
- Automatisch uploaden naar Omgevingsloket
- BGT API, async queue → pas via backlog
