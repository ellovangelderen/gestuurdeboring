# Builder Agent — hdd-platform (Martien Luijben)
# Project: HDD Ontwerp Platform · GestuurdeBoringTekening.nl
# Hosted: hdd.inodus.nl · Aanpak: walking skeleton + backlog

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
- AI tekst:    Anthropic Claude API (alleen backlog item 3)

## PROJECTSTRUCTUUR
app/
  core/         workspace middleware, auth, config, db sessie
  project/      project CRUD — begin hier
  geo/          KLIC GML parser, geometrie, conflictcheck
  rules/        eisenprofielen seed (hardcoded skeleton)
  design/       boorprofiel geometrie engine
  calculations/ LEEG → backlog 11
  documents/    PDF generator + DXF generator
  ai_assist/    LEEG → backlog 3
  drive/        Google Drive sync
  api/          FastAPI routes

## CONVENTIES
- Routes:        /api/v1/{resource}/{action}
- Errors:        { "error": "...", "code": "...", "field": "..." }
- Naamgeving:    snake_case Python, kebab-case HTML/CSS
- Migraties:     altijd Alembic — nooit raw ALTER TABLE
- Workspace:     elke query filtert op workspace_id (middleware)
- Gebruik nooit: tenant · klant · organisatie — altijd "workspace"
- Coördinaten:   altijd RD New EPSG:28992, 2 decimalen
- Kaart:         oriëntatie only — RD tangentpunten zijn echte invoer

## DOMEINREGELS (walking skeleton scope)
- Override principe: elke complexe stap heeft handmatige fallback — altijd
- KLIC: dieptes zijn ALTIJD onbetrouwbaar — altijd waarschuwen bij conflictcheck
- Berekeningen: altijd expliciete Python code — nooit via AI-prompting
- DXF laagnamen: exact conform HDD28 referentie (sectie 7 CLAUDE.md)
- Auth: USER_TEST_PASSWORD alleen actief als ENV=development

## BUITEN SCOPE — nooit bouwen
- React, Vue, Next.js, of enig JS framework
- Docker of pipeline files
- MySQL of PostgreSQL
- JWT tokens
- Calculatiemodule / offertegenerator
- Automatisch uploaden naar Omgevingsloket
- BGT API, async queue, AI → pas na skeleton via backlog
