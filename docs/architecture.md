# HDD Ontwerp Platform — Architectuurdocument

**Versie:** 1.0 | **Datum:** 2026-03-12 | **Opgesteld door:** LeanAI Architect Agent

---

## Antwoorden op de 6 Openstaande Architectuurvragen

Voordat het architectuurdocument volgt, worden de openstaande vragen beantwoord zodat het document daarop kan worden afgestemd.

**1. KLIC import:** Handmatige GML upload in MVP. BGT API-aanroep wordt wel geimplementeerd (open API, lage complexiteit), maar geautomatiseerde KLIC-aanvraag valt buiten MVP. Dit geeft de meeste waarde met de minste afhankelijkheid van externe systemen.

**2. DWG kwaliteit:** Minimaal vereist voor vergunningindiening: titelblok met projectnaam, opdrachtgever, datum, schaal, tekenaar; lagenstructuur met minimaal lagen SITUATIE, KLIC, ONTWERP, LENGTEPROFIEL, TEKST, MAATVOERING. Kleuren en lijntypen conform NEN-ISO 128.

**3. Meerdere boringen per project:** Expliciet buiten MVP. Het datamodel ondersteunt het wel via een `boring_id` foreign key, maar de UI en workflow ondersteunen slechts 1 boring per project in release 1.

**4. Eisenprofiel beheer:** In MVP direct via beheerscherm configureerbaar — niet hardcoded. Reden: het aantal beheerders (RWS, waterschappen, gemeenten) is te groot en te divers om te hardcoden, en het beheerscherm is snel te bouwen. De eerste vier profielen (RWS, waterschap, gemeente, ProRail) worden als seed-data meegeleverd.

**5. AI werkplan:** Optionele actie door de engineer via een expliciete knop. De AI-aanvulling is geen blokkade voor de workflow en is eenvoudig uitschakelbaar per project.

**6. Hosting:** VPS met Docker Compose voor MVP. Eenvoudig te migreren naar cloud (AWS/GCP) zodra het platform stabiel is. S3-compatibele opslag via MinIO op dezelfde VPS in MVP, vervangbaar door AWS S3 zonder codewijzigingen.

---

## 1. Component Diagram

### 1.1 Overzicht

```
┌─────────────────────────────────────────────────────────────────────┐
│  BROWSER (React / Vite)                                             │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ Intake       │  │ Kaart &      │  │ Output       │              │
│  │ Wizard       │  │ Ontwerp      │  │ Dashboard    │              │
│  │ Component    │  │ Component    │  │ Component    │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                 │                  │                      │
│  ┌──────┴─────────────────┴──────────────────┴───────┐             │
│  │ API Client Layer (Axios + React Query)             │             │
│  └──────────────────────────┬────────────────────────┘             │
└─────────────────────────────│───────────────────────────────────────┘
                              │ HTTPS / REST + JSON
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│  APPLICATION API  (FastAPI — poort 8000)                            │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ Auth Router  │  │ Project      │  │ Workflow      │              │
│  │ /auth        │  │ Router       │  │ Router        │              │
│  │              │  │ /projects    │  │ /workflow     │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                 │                  │                      │
│  ┌──────┴─────────────────┴──────────────────┴───────┐             │
│  │ Middleware: JWT-authenticatie · Rate limiting       │             │
│  │ CORS · Request logging · Error handling             │             │
│  └──────────────────────────────────────────────────┘              │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Domeinservice Laag (interne Python modules)                  │   │
│  │                                                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │   │
│  │  │ GeoService  │  │ RuleEngine  │  │ DesignEngine│          │   │
│  │  │             │  │             │  │             │          │   │
│  │  │ - KLIC parse│  │ - Eisen-    │  │ - Boorcurve │          │   │
│  │  │ - BGT fetch │  │   profiel   │  │   berekening│          │   │
│  │  │ - Geometrie │  │ - Min diepte│  │ - Conflict  │          │   │
│  │  │   opslaan   │  │ - Zones     │  │   check     │          │   │
│  │  │ - Kaartdata │  │ - Validatie │  │ - Parameters│          │   │
│  │  │   queries   │  │             │  │ - Versioning│          │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘          │   │
│  │                                                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │   │
│  │  │ Calc Engine │  │ DocGenerator│  │ AIAssistant │          │   │
│  │  │             │  │             │  │             │          │   │
│  │  │ - Sterkte   │  │ - PDF via   │  │ - Werkplan  │          │   │
│  │  │ - Intrek-   │  │   WeasyPrint│  │   tekst     │          │   │
│  │  │   kracht    │  │ - DWG via   │  │ - LLM call  │          │   │
│  │  │ - Slurry-   │  │   ezdxf     │  │   (OpenAI/  │          │   │
│  │  │   druk      │  │ - Template  │  │    lokaal)  │          │   │
│  │  │ - Frac-out  │  │   beheer    │  │             │          │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘          │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
          │                   │                    │
          ▼                   ▼                    ▼
┌──────────────┐   ┌─────────────────┐   ┌───────────────┐
│ PostgreSQL   │   │  Redis          │   │  File Storage │
│ + PostGIS    │   │  (job queue +   │   │  (MinIO/S3)   │
│              │   │   sessie cache) │   │               │
│ Hoofd data   │   │                 │   │ - KLIC GML    │
│ Geometrie    │   │  ARQ workers:   │   │ - DWG uploads │
│ Projecten    │   │  - PDF generatie│   │ - PDF output  │
│ Ontwerpen    │   │  - DWG generatie│   │ - DWG output  │
│ Berekeningen │   │  - BGT fetch    │   │ - Werkplannen │
└──────────────┘   │  - AI werkplan  │   └───────────────┘
                   └─────────────────┘

Externe API's:
┌─────────────────────────────────────────────────────────┐
│  BGT API (Kadaster PDOK)     → GeoService               │
│  OpenAI API / Lokale LLM     → AIAssistant              │
└─────────────────────────────────────────────────────────┘
```

### 1.2 Domeinservice Verantwoordelijkheden

**GeoService**
- GML parsing van KLIC-bestanden (lxml + shapely)
- Geometrie transformatie naar RD New (EPSG:28992) en WGS84
- BGT ophalen via PDOK API voor project bounding box
- PostGIS queries voor ruimtelijke analyses
- Conflictdetectie: buffer geometrie vs. KLIC objecten
- Kaartdata serialisatie naar GeoJSON voor frontend

**RuleEngine**
- Eisenprofielen laden vanuit database
- Minimale diepte bepalen op basis van type te kruisen object en beheerder
- Beschermingszones berekenen
- Ontwerp valideren tegen eisenprofiel
- Resultaat: lijst van validatieregels met status (OK / waarschuwing / afgekeurd)

**DesignEngine**
- Boorcurve genereren: catenary/clothoid spline berekening
- Ontwerpparameters uitrekenen: lengte, diepte, boogstraal, intrede- en uittredehoek
- Handmatige aanpassingen verwerken en herberekenen
- Versiebeheer van ontwerpen (immutable versies)
- Entry/exit punt constraints handhaven

**CalcEngine**
- Sterktecontrole: toelaatbare spanning PE/staal, Von Mises criteriun
- Intrekkracht: wrijving, gewicht, boogweerstand langs tracé
- Boorvloeistofdruk: hydrostatische druk, annulaire drukval, frac-out grenswaarde
- Alle formules gedocumenteerd met norm-referentie (NEN, ASTM)

**DocGenerator**
- PDF genereren via WeasyPrint met Jinja2 HTML template
- Titelblok vullen vanuit projectdata
- Situatietekening renderen als SVG embedded in PDF
- Lengteprofiel tekenen als SVG embedded in PDF
- DWG genereren via ezdxf met lagenstructuur
- Werkplan PDF via template

**AIAssistant**
- Werkplantekst genereren op basis van gestructureerde projectdata
- Prompt assembly vanuit templateparameters
- LLM aanroepen (configurable: OpenAI GPT-4 of lokale Ollama)
- Output als markdown, omgezet naar PDF via DocGenerator

---

## 2. API Design

### 2.1 Algemene Conventies

- Alle endpoints vereisen `Authorization: Bearer <JWT>` tenzij anders vermeld
- Content-Type: `application/json` voor alle request/response bodies
- Foutresponse altijd: `{"detail": "...", "code": "ERROR_CODE"}`
- Paginatie via `?page=1&limit=20` waar van toepassing
- Versie prefix: `/api/v1/`
- Timestamps: ISO 8601 UTC (`2026-03-12T10:00:00Z`)

### 2.2 Auth Module `/api/v1/auth`

```
POST   /auth/login
  Body:    {"email": "string", "password": "string"}
  Response: {"access_token": "string", "token_type": "bearer", "user": {...}}
  Auth:    Geen (public endpoint)

POST   /auth/logout
  Body:    {}
  Response: {"message": "Uitgelogd"}

POST   /auth/refresh
  Body:    {"refresh_token": "string"}
  Response: {"access_token": "string"}

GET    /auth/me
  Response: {"id": "uuid", "naam": "string", "email": "string", "rol": "werkvoorbereider|engineer|beheerder"}

PUT    /auth/me/password
  Body:    {"huidig_wachtwoord": "string", "nieuw_wachtwoord": "string"}
  Response: {"message": "Wachtwoord gewijzigd"}
```

### 2.3 Gebruikersbeheer `/api/v1/gebruikers` (beheerder only)

```
GET    /gebruikers
  Response: [{"id", "naam", "email", "rol", "actief", "aangemaakt_op"}]

POST   /gebruikers
  Body:    {"naam": "string", "email": "string", "rol": "string", "wachtwoord": "string"}
  Response: {"id": "uuid", ...}

GET    /gebruikers/{id}
  Response: {"id", "naam", "email", "rol", "projecten_count", ...}

PUT    /gebruikers/{id}
  Body:    {"naam"?, "email"?, "rol"?, "actief"?}
  Response: {"id", ...}

DELETE /gebruikers/{id}
  Response: 204 No Content
```

### 2.4 Project Module `/api/v1/projecten`

```
GET    /projecten
  Query: ?status=concept|ontwerp|review|opgeleverd&page=1&limit=20
  Response: {"items": [...], "totaal": int, "pagina": int}
  Item:  {"id", "naam", "opdrachtgever", "status", "aangemaakt_op", "bijgewerkt_op",
          "aangemaakt_door": {"id", "naam"}, "boring_type": "string"}

POST   /projecten
  Body:    {
    "naam": "string",
    "opdrachtgever": "string",
    "locatie_omschrijving": "string",
    "leiding_type": "gas|water|elektriciteit|glasvezel|overig",
    "leiding_materiaal": "PE|staal|PVC|overig",
    "leiding_diameter_mm": float,
    "leiding_wanddikte_mm": float,
    "gewenste_output": ["pdf_tekening", "dwg_tekening", "werkplan", "berekeningen"]
  }
  Response: {"id": "uuid", "naam": "string", "status": "concept", ...}

GET    /projecten/{id}
  Response: Volledig projectobject met alle geneste data

PUT    /projecten/{id}
  Body:    Deelverzameling van POST body velden
  Response: Bijgewerkt project object

DELETE /projecten/{id}
  Response: 204 No Content
  Constraint: Alleen beheerder of eigenaar, alleen als status=concept

POST   /projecten/{id}/kopieer
  Body:    {"nieuwe_naam": "string"}
  Response: Nieuw project object (kopie)

GET    /projecten/{id}/status-geschiedenis
  Response: [{"status", "gewijzigd_op", "gewijzigd_door": {"naam"}, "opmerking"}]

PUT    /projecten/{id}/status
  Body:    {"status": "ontwerp|review|opgeleverd", "opmerking": "string"}
  Response: Bijgewerkt project object
```

### 2.5 Locatie en Brondata `/api/v1/projecten/{id}/brondata`

```
PUT    /projecten/{id}/locatie
  Body:    {
    "startpunt": {"lat": float, "lon": float},
    "eindpunt": {"lat": float, "lon": float},
    "bounding_box": {"min_lat": float, "min_lon": float, "max_lat": float, "max_lon": float}
  }
  Response: {"locatie": {...}, "bgt_status": "niet_opgehaald|bezig|gereed"}

POST   /projecten/{id}/brondata/klic
  Body:    multipart/form-data (meerdere .gml bestanden)
  Response: {"job_id": "uuid", "status": "verwerking_gestart"}
  Note:    Async verwerking via ARQ worker

GET    /projecten/{id}/brondata/klic/status
  Response: {"status": "verwerking|gereed|fout", "objecten_count": int, "fout_melding"?: "string"}

GET    /projecten/{id}/brondata/klic/objecten
  Query: ?type=gas|elektriciteit|water|telecom|riool&bbox=...
  Response: GeoJSON FeatureCollection met KLIC objecten

POST   /projecten/{id}/brondata/bgt/ophalen
  Body:    {} (gebruikt projectbounding box)
  Response: {"job_id": "uuid", "status": "verwerking_gestart"}
  Note:    Async; haalt BGT op via PDOK API

GET    /projecten/{id}/brondata/bgt/status
  Response: {"status": "verwerking|gereed|fout", "objecten_count": int}

GET    /projecten/{id}/brondata/bgt/objecten
  Query: ?type=wegdeel|waterdeel|spoor|gebouw
  Response: GeoJSON FeatureCollection

POST   /projecten/{id}/brondata/dwg
  Body:    multipart/form-data (.dwg of .dxf bestand)
  Response: {"bestand_id": "uuid", "bestandsnaam": "string", "grootte_bytes": int}

DELETE /projecten/{id}/brondata/dwg/{bestand_id}
  Response: 204 No Content

PUT    /projecten/{id}/brondata/klic/objecten/{object_id}/diepte
  Body:    {"diepte_cm": int, "reden": "string"}
  Response: Bijgewerkt KLIC object
```

### 2.6 Te Kruisen Object en Eisen `/api/v1/projecten/{id}/kruisingsobject`

```
PUT    /projecten/{id}/kruisingsobject
  Body:    {
    "type": "rijksweg|provinciale_weg|gemeenteweg|watergang|waterkering|spoorlijn",
    "naam": "string",
    "beheerder_type": "rws|waterschap|gemeente|prorail|provincie",
    "breedte_m": float,
    "aanvullende_eisen": "string"
  }
  Response: {
    "kruisingsobject": {...},
    "eisenprofiel": {"id": "uuid", "naam": "string", "min_diepte_m": float, ...}
  }

GET    /projecten/{id}/kruisingsobject
  Response: Huidig kruisingsobject met gekoppeld eisenprofiel

GET    /eisenprofielen
  Response: [{"id", "naam", "beheerder_type", "object_type", "min_diepte_m",
              "beschermingszone_m", "bijzonderheden"}]

GET    /eisenprofielen/{id}
  Response: Volledig eisenprofiel met alle regels

POST   /eisenprofielen (beheerder only)
  Body:    {"naam", "beheerder_type", "object_type", "min_diepte_m",
            "beschermingszone_m", "bijzonderheden", "regels": [...]}
  Response: Nieuw eisenprofiel

PUT    /eisenprofielen/{id} (beheerder only)
  Body:    Deelverzameling eisenprofiel velden
  Response: Bijgewerkt eisenprofiel

DELETE /eisenprofielen/{id} (beheerder only)
  Response: 204 No Content
```

### 2.7 HDD Design Engine `/api/v1/projecten/{id}/ontwerp`

```
POST   /projecten/{id}/ontwerp/genereer
  Body:    {
    "overschrijf_bestaand": bool,
    "parameters"?: {
      "max_boogstraal_m"?: float,
      "min_boogstraal_m"?: float,
      "intrede_hoek_graden"?: float,
      "uittrede_hoek_graden"?: float
    }
  }
  Response: {"job_id": "uuid", "status": "gestart"}
  Note:    Async; resultaat via polling of websocket

GET    /projecten/{id}/ontwerp
  Response: {
    "versie": int,
    "status": "concept|akkoord|waarschuwing|afgekeurd",
    "aangemaakt_op": "timestamp",
    "parameters": {
      "totale_lengte_m": float,
      "max_diepte_m": float,
      "min_boogstraal_m": float,
      "intrede_hoek": float,
      "uittrede_hoek": float,
      "horizontale_lengte_m": float
    },
    "tracé_geojson": "GeoJSON LineString",
    "validaties": [
      {"regel": "string", "status": "ok|waarschuwing|afgekeurd", "waarde": float, "limiet": float}
    ],
    "conflicten": [
      {"klic_object_id": "uuid", "type": "string", "afstand_m": float, "ernst": "info|waarschuwing|kritiek"}
    ]
  }

PUT    /projecten/{id}/ontwerp/aanpassen
  Body:    {
    "startpunt_aanpassing"?: {"lat": float, "lon": float, "diepte_m": float},
    "eindpunt_aanpassing"?: {"lat": float, "lon": float, "diepte_m": float},
    "max_diepte_m"?: float,
    "intrede_hoek"?: float,
    "uittrede_hoek"?: float,
    "handmatige_punten"?: [{"lat", "lon", "diepte_m"}]
  }
  Response: Herberekend ontwerp (synchroon voor kleine aanpassingen, async voor grote)

GET    /projecten/{id}/ontwerp/versies
  Response: [{"versie": int, "aangemaakt_op", "aangemaakt_door": {"naam"}, "opmerking", "status"}]

GET    /projecten/{id}/ontwerp/versies/{versie}
  Response: Volledig ontwerp van specifieke versie

POST   /projecten/{id}/ontwerp/versies/{versie}/herstel
  Body:    {"opmerking": "string"}
  Response: Nieuw ontwerp op basis van herstelversie

PUT    /projecten/{id}/ontwerp/accordeer
  Body:    {"opmerking": "string"}
  Response: Ontwerp met status "akkoord" (engineer rol vereist)
```

### 2.8 Berekeningen `/api/v1/projecten/{id}/berekeningen`

```
POST   /projecten/{id}/berekeningen/sterkte
  Body:    {
    "veiligheidsfactor": float,
    "toelaatbare_spanning_mpa"?: float
  }
  Response: {
    "id": "uuid",
    "type": "sterkte",
    "resultaat": {
      "max_trekspanning_mpa": float,
      "max_buigspanning_mpa": float,
      "combinatie_spanning_mpa": float,
      "toelaatbaar": bool,
      "utilisation_ratio": float
    },
    "status": "ok|waarschuwing|afgekeurd",
    "berekend_op": "timestamp"
  }

POST   /projecten/{id}/berekeningen/intrekkracht
  Body:    {
    "wrijvingscoefficient": float,
    "boorvloeistof_soortgewicht": float,
    "veiligheidsfactor": float
  }
  Response: {
    "id": "uuid",
    "type": "intrekkracht",
    "resultaat": {
      "max_trekkracht_kn": float,
      "per_segment": [{"segment": int, "trekkracht_kn": float}],
      "toelaatbaar": bool
    },
    "status": "ok|waarschuwing|afgekeurd"
  }

POST   /projecten/{id}/berekeningen/slurrydruk
  Body:    {
    "boordiameter_mm": float,
    "pompdruk_bar": float,
    "debiet_lpm": float
  }
  Response: {
    "id": "uuid",
    "type": "slurrydruk",
    "resultaat": {
      "max_annulaire_druk_bar": float,
      "hydrostatische_druk_bar": float,
      "frac_out_druk_bar": float,
      "frac_out_risico": "laag|midden|hoog",
      "kritieke_punten": [{"diepte_m": float, "druk_bar": float}]
    },
    "status": "ok|waarschuwing|afgekeurd"
  }

GET    /projecten/{id}/berekeningen
  Response: [{"id", "type", "status", "berekend_op"}]

GET    /projecten/{id}/berekeningen/{berekening_id}
  Response: Volledig berekeningsresultaat
```

### 2.9 Document Output `/api/v1/projecten/{id}/output`

```
POST   /projecten/{id}/output/genereer
  Body:    {
    "types": ["pdf_tekening", "dwg_tekening", "werkplan", "berekening_pdf"],
    "template_id"?: "uuid"
  }
  Response: {"job_id": "uuid", "status": "gestart", "geschatte_duur_sec": int}

GET    /projecten/{id}/output/jobs/{job_id}
  Response: {
    "status": "wachten|bezig|gereed|fout",
    "voortgang_pct": int,
    "fout_melding"?: "string",
    "documenten"?: [{"id": "uuid", "type": "string", "bestandsnaam": "string"}]
  }

GET    /projecten/{id}/output/documenten
  Response: [{"id", "type", "bestandsnaam", "grootte_bytes", "aangemaakt_op", "versie"}]

GET    /projecten/{id}/output/documenten/{document_id}/download
  Response: Bestand als binary stream (Content-Disposition: attachment)

DELETE /projecten/{id}/output/documenten/{document_id}
  Response: 204 No Content

POST   /projecten/{id}/output/ai-werkplan
  Body:    {"aanvullende_context"?: "string"}
  Response: {"job_id": "uuid"}
  Note:    Async; genereert werkplantekst via LLM

GET    /templates (beheerder only)
  Response: [{"id", "naam", "opdrachtgever", "type"}]

POST   /templates (beheerder only)
  Body:    multipart/form-data (HTML template bestand + metadata)
  Response: {"id": "uuid", ...}
```

---

## 3. Datamodel (ERD)

### 3.1 Schema Overzicht

Alle tabellen zitten in het `hdd` schema. PostGIS geometrie kolommen gebruiken EPSG:28992 (RD New) als primair CRS, WGS84 voor API output.

### 3.2 Tabeldefinities

```sql
-- ═══════════════════════════════════════════════════
-- GEBRUIKERS EN AUTHENTICATIE
-- ═══════════════════════════════════════════════════

CREATE TABLE hdd.gebruikers (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    naam                VARCHAR(255)    NOT NULL,
    email               VARCHAR(255)    NOT NULL UNIQUE,
    wachtwoord_hash     VARCHAR(255)    NOT NULL,
    rol                 VARCHAR(50)     NOT NULL CHECK (rol IN ('werkvoorbereider', 'engineer', 'beheerder')),
    actief              BOOLEAN         NOT NULL DEFAULT TRUE,
    aangemaakt_op       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    bijgewerkt_op       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    laatste_login_op    TIMESTAMPTZ
);

CREATE INDEX idx_gebruikers_email ON hdd.gebruikers(email);
CREATE INDEX idx_gebruikers_rol   ON hdd.gebruikers(rol);


-- ═══════════════════════════════════════════════════
-- EISENPROFIELEN (beheerd door admin)
-- ═══════════════════════════════════════════════════

CREATE TABLE hdd.eisenprofielen (
    id                      UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    naam                    VARCHAR(255)    NOT NULL,
    beheerder_type          VARCHAR(50)     NOT NULL CHECK (beheerder_type IN (
                                'rws', 'waterschap', 'gemeente', 'prorail', 'provincie', 'overig')),
    object_type             VARCHAR(50)     NOT NULL CHECK (object_type IN (
                                'rijksweg', 'provinciale_weg', 'gemeenteweg',
                                'watergang', 'waterkering', 'spoorlijn', 'overig')),
    min_diepte_m            DECIMAL(6,2)    NOT NULL,
    beschermingszone_m      DECIMAL(6,2)    NOT NULL DEFAULT 0,
    bijzonderheden          TEXT,
    actief                  BOOLEAN         NOT NULL DEFAULT TRUE,
    aangemaakt_op           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    bijgewerkt_op           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    aangemaakt_door_id      UUID            NOT NULL REFERENCES hdd.gebruikers(id)
);

CREATE TABLE hdd.eisenprofiel_regels (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    eisenprofiel_id     UUID            NOT NULL REFERENCES hdd.eisenprofielen(id) ON DELETE CASCADE,
    regel_code          VARCHAR(100)    NOT NULL,
    omschrijving        TEXT            NOT NULL,
    parameter           VARCHAR(100),       -- bijv. "min_diepte_m", "max_boogstraal_m"
    waarde              DECIMAL(10,4),
    eenheid             VARCHAR(20),
    verplicht           BOOLEAN         NOT NULL DEFAULT TRUE,
    UNIQUE(eisenprofiel_id, regel_code)
);


-- ═══════════════════════════════════════════════════
-- PROJECTEN
-- ═══════════════════════════════════════════════════

CREATE TABLE hdd.projecten (
    id                      UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    naam                    VARCHAR(255)    NOT NULL,
    opdrachtgever           VARCHAR(255)    NOT NULL,
    locatie_omschrijving    VARCHAR(500),
    status                  VARCHAR(50)     NOT NULL DEFAULT 'concept'
                                CHECK (status IN ('concept', 'ontwerp', 'review', 'opgeleverd', 'gearchiveerd')),
    leiding_type            VARCHAR(50)     NOT NULL CHECK (leiding_type IN (
                                'gas', 'water', 'elektriciteit', 'glasvezel', 'riool', 'overig')),
    leiding_materiaal       VARCHAR(50)     NOT NULL CHECK (leiding_materiaal IN (
                                'PE', 'staal', 'PVC', 'GVK', 'overig')),
    leiding_diameter_mm     DECIMAL(8,2)    NOT NULL,
    leiding_wanddikte_mm    DECIMAL(8,3)    NOT NULL,
    gewenste_output         TEXT[]          NOT NULL DEFAULT '{"pdf_tekening","dwg_tekening"}',
    aangemaakt_door_id      UUID            NOT NULL REFERENCES hdd.gebruikers(id),
    aangemaakt_op           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    bijgewerkt_op           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    gearchiveerd_op         TIMESTAMPTZ
);

CREATE INDEX idx_projecten_status          ON hdd.projecten(status);
CREATE INDEX idx_projecten_aangemaakt_door ON hdd.projecten(aangemaakt_door_id);
CREATE INDEX idx_projecten_aangemaakt_op   ON hdd.projecten(aangemaakt_op DESC);

CREATE TABLE hdd.project_status_geschiedenis (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          UUID            NOT NULL REFERENCES hdd.projecten(id) ON DELETE CASCADE,
    van_status          VARCHAR(50)     NOT NULL,
    naar_status         VARCHAR(50)     NOT NULL,
    gewijzigd_door_id   UUID            NOT NULL REFERENCES hdd.gebruikers(id),
    gewijzigd_op        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    opmerking           TEXT
);

CREATE INDEX idx_status_gesch_project ON hdd.project_status_geschiedenis(project_id);


-- ═══════════════════════════════════════════════════
-- LOCATIE EN GEOMETRIE
-- ═══════════════════════════════════════════════════

CREATE TABLE hdd.project_locaties (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          UUID            NOT NULL UNIQUE REFERENCES hdd.projecten(id) ON DELETE CASCADE,
    startpunt           GEOMETRY(Point, 28992)      NOT NULL,
    eindpunt            GEOMETRY(Point, 28992)      NOT NULL,
    bounding_box        GEOMETRY(Polygon, 28992)    NOT NULL,
    tracé_gebied        GEOMETRY(Polygon, 28992),   -- uitgebreid gebied voor brondata ophalen
    bijgewerkt_op       TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_locaties_project     ON hdd.project_locaties(project_id);
CREATE INDEX idx_locaties_startpunt   ON hdd.project_locaties USING GIST(startpunt);
CREATE INDEX idx_locaties_bbox        ON hdd.project_locaties USING GIST(bounding_box);


-- ═══════════════════════════════════════════════════
-- TE KRUISEN OBJECTEN
-- ═══════════════════════════════════════════════════

CREATE TABLE hdd.kruisingsobjecten (
    id                      UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id              UUID            NOT NULL UNIQUE REFERENCES hdd.projecten(id) ON DELETE CASCADE,
    type                    VARCHAR(50)     NOT NULL CHECK (type IN (
                                'rijksweg', 'provinciale_weg', 'gemeenteweg',
                                'watergang', 'waterkering', 'spoorlijn', 'overig')),
    naam                    VARCHAR(255)    NOT NULL,
    beheerder_type          VARCHAR(50)     NOT NULL,
    breedte_m               DECIMAL(8,2),
    aanvullende_eisen       TEXT,
    eisenprofiel_id         UUID            REFERENCES hdd.eisenprofielen(id),
    geometrie               GEOMETRY(LineString, 28992),  -- lijn van te kruisen object
    aangemaakt_op           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    bijgewerkt_op           TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_kruising_project       ON hdd.kruisingsobjecten(project_id);
CREATE INDEX idx_kruising_eisenprofiel  ON hdd.kruisingsobjecten(eisenprofiel_id);
CREATE INDEX idx_kruising_geometrie     ON hdd.kruisingsobjecten USING GIST(geometrie);


-- ═══════════════════════════════════════════════════
-- KLIC BRONDATA
-- ═══════════════════════════════════════════════════

CREATE TABLE hdd.klic_uploads (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          UUID            NOT NULL REFERENCES hdd.projecten(id) ON DELETE CASCADE,
    bestandsnaam        VARCHAR(500)    NOT NULL,
    s3_sleutel          VARCHAR(1000)   NOT NULL,
    grootte_bytes       BIGINT          NOT NULL,
    verwerk_status      VARCHAR(50)     NOT NULL DEFAULT 'wachten'
                            CHECK (verwerk_status IN ('wachten', 'bezig', 'gereed', 'fout')),
    fout_melding        TEXT,
    objecten_count      INTEGER,
    geupload_op         TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    verwerkt_op         TIMESTAMPTZ,
    geupload_door_id    UUID            NOT NULL REFERENCES hdd.gebruikers(id)
);

CREATE INDEX idx_klic_uploads_project ON hdd.klic_uploads(project_id);

CREATE TABLE hdd.klic_objecten (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          UUID            NOT NULL REFERENCES hdd.projecten(id) ON DELETE CASCADE,
    upload_id           UUID            NOT NULL REFERENCES hdd.klic_uploads(id) ON DELETE CASCADE,
    klic_id             VARCHAR(255),                   -- originele KLIC identifier
    type                VARCHAR(50)     NOT NULL CHECK (type IN (
                            'gas', 'elektriciteit', 'water', 'telecom', 'riool',
                            'warmte', 'datakabel', 'overig')),
    beheerder           VARCHAR(255),
    naam                VARCHAR(255),
    geometrie           GEOMETRY(Geometry, 28992)       NOT NULL,  -- punt, lijn of vlak
    diepte_cm           INTEGER,                        -- bovenkant leiding onder maaiveld
    diepte_cm_manueel   INTEGER,                        -- handmatige correctie
    diepte_handmatig    BOOLEAN         NOT NULL DEFAULT FALSE,
    diepte_reden        TEXT,
    eigenschappen       JSONB           NOT NULL DEFAULT '{}',  -- overige GML attributen
    aangemaakt_op       TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_klic_objecten_project  ON hdd.klic_objecten(project_id);
CREATE INDEX idx_klic_objecten_type     ON hdd.klic_objecten(type);
CREATE INDEX idx_klic_objecten_geom     ON hdd.klic_objecten USING GIST(geometrie);


-- ═══════════════════════════════════════════════════
-- BGT BRONDATA
-- ═══════════════════════════════════════════════════

CREATE TABLE hdd.bgt_objecten (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          UUID            NOT NULL REFERENCES hdd.projecten(id) ON DELETE CASCADE,
    bgt_id              VARCHAR(255),                   -- originele BGT identifier
    type                VARCHAR(50)     NOT NULL CHECK (type IN (
                            'wegdeel', 'waterdeel', 'spoor', 'gebouw',
                            'begroeid_terreindeel', 'overig_terrein', 'overig')),
    subtype             VARCHAR(100),
    geometrie           GEOMETRY(Geometry, 28992)       NOT NULL,
    eigenschappen       JSONB           NOT NULL DEFAULT '{}',
    opgehaald_op        TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_bgt_objecten_project  ON hdd.bgt_objecten(project_id);
CREATE INDEX idx_bgt_objecten_type     ON hdd.bgt_objecten(type);
CREATE INDEX idx_bgt_objecten_geom     ON hdd.bgt_objecten USING GIST(geometrie);

CREATE TABLE hdd.bgt_ophaal_status (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          UUID            NOT NULL UNIQUE REFERENCES hdd.projecten(id) ON DELETE CASCADE,
    status              VARCHAR(50)     NOT NULL DEFAULT 'niet_opgehaald'
                            CHECK (status IN ('niet_opgehaald', 'bezig', 'gereed', 'fout')),
    objecten_count      INTEGER,
    fout_melding        TEXT,
    opgehaald_op        TIMESTAMPTZ,
    bijgewerkt_op       TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);


-- ═══════════════════════════════════════════════════
-- DWG UPLOADS (optionele achtergrondtekening)
-- ═══════════════════════════════════════════════════

CREATE TABLE hdd.dwg_uploads (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          UUID            NOT NULL REFERENCES hdd.projecten(id) ON DELETE CASCADE,
    bestandsnaam        VARCHAR(500)    NOT NULL,
    s3_sleutel          VARCHAR(1000)   NOT NULL,
    grootte_bytes       BIGINT          NOT NULL,
    geupload_op         TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    geupload_door_id    UUID            NOT NULL REFERENCES hdd.gebruikers(id)
);

CREATE INDEX idx_dwg_uploads_project ON hdd.dwg_uploads(project_id);


-- ═══════════════════════════════════════════════════
-- HDD ONTWERPEN (versiebeheert)
-- ═══════════════════════════════════════════════════

CREATE TABLE hdd.ontwerpen (
    id                      UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id              UUID            NOT NULL REFERENCES hdd.projecten(id) ON DELETE CASCADE,
    versie                  INTEGER         NOT NULL,
    status                  VARCHAR(50)     NOT NULL DEFAULT 'concept'
                                CHECK (status IN ('concept', 'akkoord', 'waarschuwing', 'afgekeurd')),
    is_huidig               BOOLEAN         NOT NULL DEFAULT TRUE,
    -- Tracé geometrie
    tracé_lijn              GEOMETRY(LineString, 28992)     NOT NULL,  -- bovenaanzicht
    tracé_3d                GEOMETRY(LineStringZ, 28992),               -- 3D met diepte
    -- Ontwerpparameters
    totale_lengte_m         DECIMAL(10,3)   NOT NULL,
    horizontale_lengte_m    DECIMAL(10,3)   NOT NULL,
    max_diepte_m            DECIMAL(8,3)    NOT NULL,
    min_boogstraal_m        DECIMAL(8,3)    NOT NULL,
    max_boogstraal_m        DECIMAL(8,3),
    intrede_hoek_graden     DECIMAL(6,3)    NOT NULL,
    uittrede_hoek_graden    DECIMAL(6,3)    NOT NULL,
    -- Metadata
    gegenereerd_door_id     UUID            NOT NULL REFERENCES hdd.gebruikers(id),
    aangemaakt_op           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    opmerking               TEXT,
    -- Accordering
    geaccordeerd_door_id    UUID            REFERENCES hdd.gebruikers(id),
    geaccordeerd_op         TIMESTAMPTZ,
    UNIQUE(project_id, versie)
);

CREATE INDEX idx_ontwerpen_project   ON hdd.ontwerpen(project_id);
CREATE INDEX idx_ontwerpen_is_huidig ON hdd.ontwerpen(project_id, is_huidig) WHERE is_huidig = TRUE;
CREATE INDEX idx_ontwerpen_tracé     ON hdd.ontwerpen USING GIST(tracé_lijn);

-- Lengteprofiel punten (gesamplede hoogtecurve voor rendering)
CREATE TABLE hdd.ontwerp_lengteprofiel_punten (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    ontwerp_id      UUID            NOT NULL REFERENCES hdd.ontwerpen(id) ON DELETE CASCADE,
    afstand_m       DECIMAL(10,3)   NOT NULL,   -- afstand langs tracé vanaf startpunt
    diepte_m        DECIMAL(8,3)    NOT NULL,   -- diepte t.o.v. maaiveld (positief = dieper)
    maaiveld_m      DECIMAL(8,3),               -- NAP hoogte maaiveld op dit punt
    boogstraal_m    DECIMAL(8,3),
    volgorde        INTEGER         NOT NULL
);

CREATE INDEX idx_lp_punten_ontwerp ON hdd.ontwerp_lengteprofiel_punten(ontwerp_id, volgorde);

-- Validatieresultaten per ontwerp
CREATE TABLE hdd.ontwerp_validaties (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    ontwerp_id      UUID            NOT NULL REFERENCES hdd.ontwerpen(id) ON DELETE CASCADE,
    regel_code      VARCHAR(100)    NOT NULL,
    omschrijving    TEXT            NOT NULL,
    status          VARCHAR(20)     NOT NULL CHECK (status IN ('ok', 'waarschuwing', 'afgekeurd')),
    gemeten_waarde  DECIMAL(12,4),
    limiet_waarde   DECIMAL(12,4),
    eenheid         VARCHAR(20),
    aangemaakt_op   TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_validaties_ontwerp ON hdd.ontwerp_validaties(ontwerp_id);

-- Conflicten met KLIC objecten
CREATE TABLE hdd.ontwerp_conflicten (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    ontwerp_id      UUID            NOT NULL REFERENCES hdd.ontwerpen(id) ON DELETE CASCADE,
    klic_object_id  UUID            NOT NULL REFERENCES hdd.klic_objecten(id),
    afstand_m       DECIMAL(8,3)    NOT NULL,   -- minimale vrije ruimte
    ernst           VARCHAR(20)     NOT NULL CHECK (ernst IN ('info', 'waarschuwing', 'kritiek')),
    kruispunt       GEOMETRY(Point, 28992),      -- punt van dichtstbijzijnde nadering
    aangemaakt_op   TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_conflicten_ontwerp ON hdd.ontwerp_conflicten(ontwerp_id);
CREATE INDEX idx_conflicten_ernst   ON hdd.ontwerp_conflicten(ernst);


-- ═══════════════════════════════════════════════════
-- TECHNISCHE BEREKENINGEN
-- ═══════════════════════════════════════════════════

CREATE TABLE hdd.berekeningen (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          UUID            NOT NULL REFERENCES hdd.projecten(id) ON DELETE CASCADE,
    ontwerp_id          UUID            NOT NULL REFERENCES hdd.ontwerpen(id),
    type                VARCHAR(50)     NOT NULL CHECK (type IN ('sterkte', 'intrekkracht', 'slurrydruk')),
    status              VARCHAR(20)     NOT NULL CHECK (status IN ('ok', 'waarschuwing', 'afgekeurd', 'fout')),
    invoer              JSONB           NOT NULL DEFAULT '{}',   -- invoerparameters
    resultaat           JSONB           NOT NULL DEFAULT '{}',   -- berekeningsresultaten
    norm_referentie     VARCHAR(255),                           -- bijv. "NEN 3651:2020"
    berekend_op         TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    berekend_door_id    UUID            NOT NULL REFERENCES hdd.gebruikers(id)
);

CREATE INDEX idx_berekeningen_project ON hdd.berekeningen(project_id);
CREATE INDEX idx_berekeningen_ontwerp ON hdd.berekeningen(ontwerp_id);
CREATE INDEX idx_berekeningen_type    ON hdd.berekeningen(type);


-- ═══════════════════════════════════════════════════
-- OUTPUT DOCUMENTEN
-- ═══════════════════════════════════════════════════

CREATE TABLE hdd.output_jobs (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          UUID            NOT NULL REFERENCES hdd.projecten(id) ON DELETE CASCADE,
    ontwerp_id          UUID            REFERENCES hdd.ontwerpen(id),
    types               TEXT[]          NOT NULL,               -- gewenste output types
    status              VARCHAR(50)     NOT NULL DEFAULT 'wachten'
                            CHECK (status IN ('wachten', 'bezig', 'gereed', 'fout')),
    voortgang_pct       INTEGER         NOT NULL DEFAULT 0,
    fout_melding        TEXT,
    aangemaakt_op       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    voltooid_op         TIMESTAMPTZ,
    aangemaakt_door_id  UUID            NOT NULL REFERENCES hdd.gebruikers(id)
);

CREATE INDEX idx_output_jobs_project ON hdd.output_jobs(project_id);

CREATE TABLE hdd.output_documenten (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          UUID            NOT NULL REFERENCES hdd.projecten(id) ON DELETE CASCADE,
    job_id              UUID            REFERENCES hdd.output_jobs(id),
    ontwerp_id          UUID            REFERENCES hdd.ontwerpen(id),
    type                VARCHAR(50)     NOT NULL CHECK (type IN (
                            'pdf_tekening', 'dwg_tekening', 'werkplan', 'berekening_pdf')),
    bestandsnaam        VARCHAR(500)    NOT NULL,
    s3_sleutel          VARCHAR(1000)   NOT NULL,
    grootte_bytes       BIGINT          NOT NULL,
    versie              INTEGER         NOT NULL DEFAULT 1,
    aangemaakt_op       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    aangemaakt_door_id  UUID            NOT NULL REFERENCES hdd.gebruikers(id)
);

CREATE INDEX idx_output_docs_project ON hdd.output_documenten(project_id);
CREATE INDEX idx_output_docs_type    ON hdd.output_documenten(type);


-- ═══════════════════════════════════════════════════
-- DOCUMENT TEMPLATES (beheerd door admin)
-- ═══════════════════════════════════════════════════

CREATE TABLE hdd.document_templates (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    naam                VARCHAR(255)    NOT NULL,
    opdrachtgever       VARCHAR(255),               -- NULL = generiek
    type                VARCHAR(50)     NOT NULL CHECK (type IN ('pdf_tekening', 'werkplan')),
    s3_sleutel          VARCHAR(1000)   NOT NULL,   -- HTML template bestand
    is_standaard        BOOLEAN         NOT NULL DEFAULT FALSE,
    aangemaakt_op       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    aangemaakt_door_id  UUID            NOT NULL REFERENCES hdd.gebruikers(id)
);


-- ═══════════════════════════════════════════════════
-- ASYNC JOB TRACKING
-- ═══════════════════════════════════════════════════

CREATE TABLE hdd.async_jobs (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type            VARCHAR(100)    NOT NULL,   -- "klic_verwerken", "bgt_ophalen", etc.
    project_id          UUID            REFERENCES hdd.projecten(id),
    arq_job_id          VARCHAR(255),               -- ARQ internal job ID
    status              VARCHAR(50)     NOT NULL DEFAULT 'wachten'
                            CHECK (status IN ('wachten', 'bezig', 'gereed', 'fout', 'geannuleerd')),
    voortgang_pct       INTEGER         NOT NULL DEFAULT 0,
    fout_melding        TEXT,
    invoer              JSONB           NOT NULL DEFAULT '{}',
    resultaat           JSONB           NOT NULL DEFAULT '{}',
    aangemaakt_op       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    gestart_op          TIMESTAMPTZ,
    voltooid_op         TIMESTAMPTZ,
    aangemaakt_door_id  UUID            REFERENCES hdd.gebruikers(id)
);

CREATE INDEX idx_async_jobs_project ON hdd.async_jobs(project_id);
CREATE INDEX idx_async_jobs_status  ON hdd.async_jobs(status);
CREATE INDEX idx_async_jobs_type    ON hdd.async_jobs(job_type);
```

### 3.3 Relatie-overzicht (tekstueel ERD)

```
gebruikers ─┬─< projecten (aangemaakt_door_id)
             ├─< eisenprofielen (aangemaakt_door_id)
             ├─< ontwerpen (gegenereerd_door_id, geaccordeerd_door_id)
             ├─< berekeningen (berekend_door_id)
             ├─< klic_uploads (geupload_door_id)
             └─< output_documenten (aangemaakt_door_id)

projecten ──┬── project_locaties (1:1)
            ├── kruisingsobjecten (1:1)
            ├── bgt_ophaal_status (1:1)
            ├─< klic_uploads ──< klic_objecten
            ├─< bgt_objecten
            ├─< dwg_uploads
            ├─< ontwerpen ──┬─< ontwerp_lengteprofiel_punten
            │               ├─< ontwerp_validaties
            │               └─< ontwerp_conflicten ──> klic_objecten
            ├─< berekeningen ──> ontwerpen
            ├─< output_jobs ──< output_documenten
            └─< async_jobs

eisenprofielen ──< eisenprofiel_regels
eisenprofielen ──< kruisingsobjecten (eisenprofiel_id FK)
```

---

## 4. MVP Bouwplan

### 4.1 Bouwprincipes

- Elke sprint levert werkende, testbare software op
- Integratie-tests draaien na elke sprint in CI/CD
- Database migraties via Alembic (Python) — nooit handmatige SQL
- Frontend en backend worden parallel gebouwd; mock API in sprint 1
- Acceptatiecriteria zijn functioneel geformuleerd (wat de gebruiker kan doen)

### 4.2 Sprint Overzicht

```
Sprint 0: Fundament            (1 week)
Sprint 1: Gebruikers & Auth    (1 week)
Sprint 2: Projectbeheer        (1.5 week)
Sprint 3: Locatie & Kaart      (2 weken)
Sprint 4: KLIC & BGT Brondata  (2 weken)
Sprint 5: Eisen Engine         (1 week)
Sprint 6: Design Engine        (3 weken)  ← zwaarste sprint
Sprint 7: Berekeningen         (2 weken)
Sprint 8: Document Output      (2 weken)
Sprint 9: Integratie & QA      (1.5 week)
```

Totaal: ca. 17 weken (4 maanden)

---

### Sprint 0 — Fundament (1 week)

**Doel:** Alle infrastructuur staat; de Builder Agent kan direct beginnen met features.

**Taken:**

1. Git repository aanmaken met monorepo structuur:
   ```
   /backend    → FastAPI applicatie
   /frontend   → React/Vite applicatie
   /docker     → docker-compose bestanden
   /docs       → architectuurdocumenten
   ```

2. Docker Compose opzetten met services:
   - `postgres` (PostgreSQL 16 + PostGIS 3.4)
   - `redis` (Redis 7 voor ARQ queue)
   - `minio` (S3-compatibele opslag)
   - `backend` (FastAPI, hot-reload)
   - `worker` (ARQ worker)
   - `frontend` (Vite dev server)

3. Backend skelet aanmaken:
   - FastAPI app factory met lifespan
   - Alembic voor migraties
   - SQLAlchemy 2.x async (asyncpg driver)
   - Pydantic v2 settings via `.env`
   - Structuur: `app/routers/`, `app/services/`, `app/models/`, `app/schemas/`

4. Database initieel schema aanmaken via Alembic migratie (alle tabellen uit sectie 3.2)

5. Frontend skelet aanmaken:
   - React 18 + Vite
   - React Router v6 voor navigatie
   - Axios + React Query voor API calls
   - shadcn/ui als componentbibliotheek
   - Leaflet voor kaartcomponent

6. CI/CD pipeline (GitHub Actions):
   - Backend: pytest + ruff lint
   - Frontend: Vitest + ESLint
   - Docker build check

**Acceptatiecriteria:**
- `docker compose up` start alle services zonder fouten
- `GET /api/v1/health` geeft `{"status": "ok", "db": "ok", "redis": "ok"}` terug
- Frontend toont lege pagina op `http://localhost:5173`
- Alembic migraties zijn reproduceerbaar (`alembic downgrade base && alembic upgrade head`)
- CI pipeline is groen

---

### Sprint 1 — Gebruikers & Authenticatie (1 week)

**Doel:** Gebruikers kunnen inloggen; rollen worden afgedwongen.

**Backend taken:**

1. `hdd.gebruikers` tabel is aanwezig (uit Sprint 0 migratie)
2. JWT authenticatie implementeren (python-jose of PyJWT):
   - Access token: 30 minuten geldigheid
   - Refresh token: 7 dagen geldigheid, opgeslagen in Redis
   - `POST /api/v1/auth/login` — email/wachtwoord verificatie, tokens retourneren
   - `POST /api/v1/auth/refresh` — nieuw access token via refresh token
   - `POST /api/v1/auth/logout` — refresh token invalideren in Redis
   - `GET /api/v1/auth/me` — huidige gebruiker ophalen
3. FastAPI dependency `get_current_user` implementeren (JWT decoder)
4. Rol-based access dependency `require_rol(rol: str)` implementeren
5. CRUD voor gebruikers (`/api/v1/gebruikers`) alleen voor beheerder rol
6. Wachtwoord hashing via bcrypt (passlib)
7. Seed script: 1 beheerder account aanmaken bij eerste start

**Frontend taken:**

1. Loginpagina (email + wachtwoord formulier)
2. JWT opslaan in memory (niet localStorage) + refresh token in httpOnly cookie
3. Axios interceptor voor automatisch toevoegen Bearer header
4. Automatische token vernieuwing bij 401 respons
5. Uitlogknop
6. Gebruikersbeheer pagina (alleen zichtbaar voor beheerder)

**Acceptatiecriteria:**
- Werkvoorbereider kan inloggen en wordt doorgestuurd naar projectenoverzicht
- Ongeldige credentials geven 401 terug met duidelijke melding
- Na 30 minuten inactiviteit wordt de sessie automatisch vernieuwd via refresh token
- Beheerder kan nieuwe gebruiker aanmaken met rol
- Niet-beheerder krijgt 403 op gebruikersbeheer endpoints
- Wachtwoorden zijn gehashed in de database (nooit plaintext)

---

### Sprint 2 — Projectbeheer (1.5 week)

**Doel:** Werkvoorbereider kan projecten aanmaken, openen en de status bijhouden.

**Backend taken:**

1. Project CRUD endpoints implementeren:
   - `POST /api/v1/projecten` — aanmaken met alle verplichte velden
   - `GET /api/v1/projecten` — lijst met paginatie en statusfilter
   - `GET /api/v1/projecten/{id}` — volledig project ophalen
   - `PUT /api/v1/projecten/{id}` — project bijwerken
   - `DELETE /api/v1/projecten/{id}` — verwijderen (alleen concept)
   - `PUT /api/v1/projecten/{id}/status` — statusovergang met logging
   - `GET /api/v1/projecten/{id}/status-geschiedenis`
   - `POST /api/v1/projecten/{id}/kopieer`

2. Statusmachine valideren: alleen geldige overgangen toestaan:
   ```
   concept → ontwerp → review → opgeleverd
   * → gearchiveerd (alleen beheerder)
   ```

3. Pydantic schemas voor alle request/response bodies

**Frontend taken:**

1. Projectenoverzicht pagina:
   - Tabel/kaartjes met naam, opdrachtgever, status, datum
   - Statusfilter dropdown
   - Zoekbalk op naam
   - "Nieuw project" knop

2. Project aanmaken wizard (stap 1 van de 7-staps workflow):
   - Naam, opdrachtgever, locatie omschrijving
   - Leiding type + materiaal + diameter + wanddikte
   - Gewenste output selectie (checkboxes)

3. Project detailpagina:
   - Sidebar met projectinfo en statusbadge
   - Tabbladen voor elke workflowstap (nog niet allemaal actief)
   - Statuswijziging knop (met modal voor opmerking)

4. Kopieer project actie

**Acceptatiecriteria:**
- Werkvoorbereider maakt project aan in < 2 minuten via wizard
- Projectenlijst laadt in < 1 seconde (20 projecten)
- Statusovergang van `concept` naar `ontwerp` is alleen mogelijk als locatie en brondata compleet zijn (validatie in volgende sprint, hier alvast de check registreren als TODO)
- Project kopiëren dupliceert alle basisgegevens, niet de brondata
- Status-geschiedenis toont alle wijzigingen met gebruikersnaam en tijdstip

---

### Sprint 3 — Locatie & Kaart (2 weken)

**Doel:** Start- en eindpunt vastleggen op kaart; bounding box bepalen voor brondata.

**Backend taken:**

1. `PUT /api/v1/projecten/{id}/locatie` implementeren:
   - Coördinaten opslaan in PostGIS (WGS84 input, opslaan als RD New)
   - Bounding box automatisch berekenen (buffer van 250m rondom tracé)
   - WGS84 ↔ RD New transformatie via pyproj

2. Helper: coördinaten valideren (vallen in Nederland)

3. `GET /api/v1/projecten/{id}/locatie` — locatie ophalen als GeoJSON

**Frontend taken:**

1. Kaartcomponent (Leaflet + MapLibre GL):
   - OpenStreetMap als achtergrondlaag
   - Satelietlaag als optie (via PDOK luchtfoto WMS)
   - Klikken op kaart om startpunt te plaatsen
   - Klikken op kaart om eindpunt te plaatsen
   - Markers verplaatsbaar via drag
   - Bounding box als half-transparante rechthoek tonen
   - Coördinaten tonen in RD New en WGS84

2. Adreszoeken (via PDOK locatieserver API):
   - Zoek op adres → zoom naar locatie
   - Coördinaten invoeren via tekstveld (RD New of WGS84)

3. Locatiedata opslaan via API bij elke wijziging (debounced)

**Acceptatiecriteria:**
- Start- en eindpunt zijn plaatsbaar via klikken op kaart
- Adreszoeken werkt voor Nederlandse adressen
- Bounding box past zich automatisch aan bij verplaatsen punten
- Locatie blijft bewaard na herladen pagina
- Coördinaten buiten Nederland geven foutmelding

---

### Sprint 4 — KLIC & BGT Brondata (2 weken)

**Doel:** KLIC GML-bestanden uploaden en verwerken; BGT ophalen via API.

**Backend taken:**

1. KLIC upload endpoint:
   - `POST /api/v1/projecten/{id}/brondata/klic` — multipart upload naar S3
   - ARQ worker `verwerk_klic_gml`:
     - GML parsen met lxml
     - Geometrie extraheren en transformeren naar RD New
     - Objecten opslaan in `hdd.klic_objecten`
     - Upload status bijwerken
   - `GET /api/v1/projecten/{id}/brondata/klic/status`
   - `GET /api/v1/projecten/{id}/brondata/klic/objecten` — GeoJSON output
   - `PUT /api/v1/projecten/{id}/brondata/klic/objecten/{id}/diepte` — handmatige correctie

2. BGT ophalen:
   - ARQ worker `haal_bgt_op`:
     - PDOK NGR WFS API aanroepen met project bounding box
     - BGT objecten opslaan in `hdd.bgt_objecten`
     - Status bijwerken in `hdd.bgt_ophaal_status`
   - `POST /api/v1/projecten/{id}/brondata/bgt/ophalen`
   - `GET /api/v1/projecten/{id}/brondata/bgt/status`
   - `GET /api/v1/projecten/{id}/brondata/bgt/objecten` — GeoJSON output

3. DWG upload (eenvoudig opslaan in S3, geen parsing):
   - `POST /api/v1/projecten/{id}/brondata/dwg`
   - `DELETE /api/v1/projecten/{id}/brondata/dwg/{id}`

**Frontend taken:**

1. KLIC upload component:
   - Drag-and-drop upload zone voor meerdere .gml bestanden
   - Upload voortgang tonen
   - Verwerkingsstatus polling (elke 3 seconden)
   - Samenvatting: X objecten geladen, per type

2. Kaartlaag voor KLIC objecten:
   - Kleurcodering per type (gas=geel, elektriciteit=rood, water=blauw, etc.)
   - Popup met details bij klikken (beheerder, diepte, type)
   - Diepte handmatig aanpassen via popup formulier
   - Laag aan/uitzetten per type

3. BGT kaartlaag:
   - "BGT ophalen" knop met voortgangsindicator
   - BGT objecten op kaart tonen (wegen, water, bebouwing)
   - Laag aan/uitzetten

4. DWG upload veld

**Acceptatiecriteria:**
- KLIC GML upload van 10 bestanden en 5000 objecten verwerkt binnen 60 seconden
- Alle KLIC objecten zijn zichtbaar op kaart met juiste kleur en popup
- BGT ophalen werkt voor bounding box van 500x500 meter
- Handmatige diepte correctie is direct zichtbaar op kaart
- Bij fout in GML parsing: duidelijke foutmelding met bestandsnaam

---

### Sprint 5 — Eisen Engine (1 week)

**Doel:** Eisenprofielen beheersen; juiste eisen koppelen aan te kruisen object.

**Backend taken:**

1. Te kruisen object endpoints:
   - `PUT /api/v1/projecten/{id}/kruisingsobject`
   - `GET /api/v1/projecten/{id}/kruisingsobject`

2. Automatisch eisenprofiel koppelen op basis van `beheerder_type` + `object_type`

3. Eisenprofiel CRUD (beheerder):
   - `GET /api/v1/eisenprofielen`
   - `POST /api/v1/eisenprofielen`
   - `PUT /api/v1/eisenprofielen/{id}`
   - `DELETE /api/v1/eisenprofielen/{id}`

4. Seed data: 4 standaard eisenprofielen aanmaken:
   - RWS rijksweg: min. 3m, beschermingszone 5m
   - Waterschap waterkering: min. 7.5m (gemiddelde), beschermingszone 10m
   - Gemeente gemeenteweg: min. 1.25m, beschermingszone 1m
   - ProRail spoorlijn: min. 4m, beschermingszone 8m

**Frontend taken:**

1. Te kruisen object formulier (workflowstap 3):
   - Type selectie (weg, water, spoor, waterkering)
   - Beheerder type selectie
   - Naam en breedte invoer
   - Automatisch gekoppeld eisenprofiel tonen

2. Eisenprofielen beheerscherm (beheerder):
   - Lijst van alle profielen
   - Aanmaken/bewerken/verwijderen via formulier
   - Regels per profiel beheren

**Acceptatiecriteria:**
- Werkvoorbereider selecteert "RWS rijksweg" → eisenprofiel met min. 3m diepte wordt automatisch geladen
- Beheerder kan nieuw eisenprofiel aanmaken en regels toevoegen
- Eisenprofiel is zichtbaar in projectdetail
- Aanvullende projectspecifieke eisen kunnen worden ingevoerd als vrije tekst

---

### Sprint 6 — HDD Design Engine (3 weken)

**Zwaarste sprint — iteratief te bouwen.**

**Week 1 — Algoritme fundament:**

1. DesignEngine module (`app/services/design_engine.py`):
   - Clothoid (Euler spiraal) boorcurve berekening
   - Input: startpunt (x,y), eindpunt (x,y), min. diepte, max. boogstraal
   - Output: lijst van punten in 2D (bovenaanzicht) + diepte curve (lengteprofiel)
   - Algoritme stappen:
     a. Rechte lijn tussen start en eind
     b. Dieptecurve bepalen: intrede → horizontaal segment → uittrede
     c. Boogstraal berekenen: `R = D / (2 * sin(θ))` waarbij D = breedte kruising
     d. Lengte van in- en uittredebogen
     e. Validatie: boogstraal ≥ min. boogstraal uit leidingspecs
   - Unit tests voor alle formules

2. Conflict check algoritme:
   - Buffer tracé met 0.5m
   - Spatiale query op KLIC objecten binnen buffer
   - Afstand berekenen per conflict
   - Ernst bepalen: < 0.3m = kritiek, < 1m = waarschuwing, < 2m = info

**Week 2 — API en async:**

3. Design endpoints implementeren:
   - `POST /api/v1/projecten/{id}/ontwerp/genereer` → ARQ worker
   - ARQ worker `genereer_ontwerp`: roept DesignEngine aan, slaat op
   - `GET /api/v1/projecten/{id}/ontwerp` — huidig ontwerp ophalen
   - `PUT /api/v1/projecten/{id}/ontwerp/aanpassen` — synchroon herberekenen
   - `GET /api/v1/projecten/{id}/ontwerp/versies`
   - Versiebeheerslogica: bij genereer/aanpassen → nieuw versie object, vorige `is_huidig=FALSE`
   - `PUT /api/v1/projecten/{id}/ontwerp/accordeer` — engineer rol vereist

4. RuleEngine integratie:
   - Na ontwerp genereren: alle eisenprofiel regels valideren
   - Resultaten opslaan in `ontwerp_validaties`
   - Ontwerp status bepalen (akkoord/waarschuwing/afgekeurd)

**Week 3 — Frontend:**

5. Kaartweergave ontwerp:
   - Tracé lijn op kaart tonen (kleur op basis van validatiestatus)
   - Conflicten tonen als gekleurde markers
   - Conflictdetails in sidebar bij klikken

6. Lengteprofiel component:
   - SVG-gebaseerde grafiek (D3.js of recharts)
   - X-as: afstand langs tracé (meter)
   - Y-as: diepte t.o.v. maaiveld
   - Maaiveldlijn, tracélijn, KLIC doorsnijelijn (als beschikbaar)
   - Interactief: hover toont waarden

7. Handmatig aanpassen:
   - Intrede/uittrede hoek aanpassen via sliders
   - Max. diepte aanpassen via invoerveld
   - Herberekening tonen na aanpassing

8. Accordeerscherm (engineer):
   - Validatieresultaten tabel (groen/oranje/rood)
   - Conflicten lijst
   - "Accordeer ontwerp" knop

**Acceptatiecriteria:**
- Ontwerp wordt automatisch gegenereerd binnen 30 seconden na klikken op "Genereer"
- Tracé voldoet aan minimum diepte van het gekoppelde eisenprofiel
- Alle KLIC conflicten worden gedetecteerd en geclassificeerd
- Engineer kan ontwerp aanpassen en herberekenen
- Versie 1 blijft bewaard na aanpassing (versie 2 wordt aangemaakt)
- Lengteprofiel is leesbaar en toont alle relevante informatie
- Accordering is alleen mogelijk voor gebruikers met engineer rol

---

### Sprint 7 — Technische Berekeningen (2 weken)

**Doel:** Optionele berekeningen uitvoeren en koppelen aan ontwerp.

**Week 1 — CalcEngine:**

1. `app/services/calc_engine.py` implementeren:

   **Sterktecontrole:**
   ```python
   # Toelaatbare spanning: σ_tot = σ_trek + σ_buig
   # σ_buig = E * d_buiten / (2 * R_min)
   # σ_trek = F_intrek / A_dwarsdoorsnede
   # Controle: σ_tot ≤ σ_toelaatbaar (PE: 6 MPa, staal: 0.5 * Rp0.2)
   ```

   **Intrekkracht:**
   ```python
   # F_intrek = Σ per segment: F_wrijving + F_gewicht + F_boogweerstand
   # F_wrijving = μ * N (normaalkracht)
   # N = W_leiding + W_vloeibaar - opwaartse druk
   # F_boogweerstand = F_vorige * (e^(μ*θ) - 1) per boog
   ```

   **Bookvloeistofdruk:**
   ```python
   # P_hydrostatisch = ρ_slurry * g * h
   # ΔP_annulair = (via Herschel-Bulkley of Bingham plastic model)
   # Frac-out grens: P_frac = σ_v * Ko (gronddruk coefficient)
   ```

2. Unit tests voor alle formules met bekende referentiewaarden

**Week 2 — API en Frontend:**

3. Berekenings-endpoints implementeren (synchroon, < 2 sec):
   - `POST /api/v1/projecten/{id}/berekeningen/sterkte`
   - `POST /api/v1/projecten/{id}/berekeningen/intrekkracht`
   - `POST /api/v1/projecten/{id}/berekeningen/slurrydruk`
   - `GET /api/v1/projecten/{id}/berekeningen`
   - `GET /api/v1/projecten/{id}/berekeningen/{id}`

4. Frontend berekeningenpagina:
   - Invoerformulier per berekeningstype
   - Resultaten tonen in tabel met kleurcodering
   - Frac-out risico als gauge/indicator
   - Historische berekeningen tonen (koppeling aan ontwerp versie)

**Acceptatiecriteria:**
- Sterktecontrole voor PE-100 leiding, diameter 250mm, wanddikte 22.7mm geeft correct resultaat (te verifiëren met handberekening)
- Intrekkracht berekening geeft resultaten per segment van het tracé
- Frac-out risico-indicator toont "hoog" wanneer max. slurry druk > 90% van fracgrens
- Waarschuwing verschijnt als utilisation ratio > 0.9
- Berekening is altijd gekoppeld aan een specifieke ontwerp versie

---

### Sprint 8 — Document Output (2 weken)

**Doel:** PDF en DWG genereren; werkplan optioneel via AI.

**Week 1 — PDF en DWG generator:**

1. DocGenerator module (`app/services/doc_generator.py`):

   **PDF tekening (WeasyPrint + Jinja2):**
   - HTML template met titelblok, kader, legenda
   - Situatietekening: SVG van kaartextract met tracé + KLIC
   - Lengteprofiel: SVG van profielgrafiek
   - Titelblok: projectnaam, opdrachtgever, datum, schaal, tekenaar, revisie
   - Schaal automatisch berekenen op basis van tracélengte

   **DWG tekening (ezdxf):**
   - Lagenstructuur:
     ```
     SITUATIE      - tracé bovenaanzicht
     KLIC_GAS      - KLIC gas leidingen
     KLIC_ELEK     - KLIC elektra
     KLIC_WATER    - KLIC water
     KLIC_TELECOM  - KLIC telecom
     KLIC_OVERIG   - overige KLIC
     BGT           - BGT topografie
     ONTWERP       - boortracé lijn
     LENGTEPROFIEL - profielaanzicht
     TEKST         - annotaties
     MAATVOERING   - maatlijnen
     TITELBLOK     - titelblok
     ```
   - Kleuren per laag conform NEN-ISO 128
   - Maatvoering voor breedte kruising, diepte, tracélengte
   - Annotaties bij start/eindpunt

2. Werkplan template (WeasyPrint):
   - Vaste secties: projectbeschrijving, tracébeschrijving, kruisingsbeschrijving, eisen, veiligheidsmaatregelen, materiaallijst
   - Data gevuld vanuit projectobject

3. Berekening PDF:
   - Invoerparameters + formules + resultaten per berekeningstype
   - Normreferenties vermelden

**Week 2 — Async jobs en Frontend:**

4. Output job implementatie:
   - `POST /api/v1/projecten/{id}/output/genereer` → ARQ worker
   - ARQ worker `genereer_output`: roept DocGenerator aan per type
   - Bestand uploaden naar S3
   - Metadat opslaan in `output_documenten`
   - Status bijwerken in `output_jobs`

5. AI werkplan (optioneel):
   - `POST /api/v1/projecten/{id}/output/ai-werkplan`
   - Prompt assembly: projectdata → gestructureerde context
   - OpenAI API aanroepen (of Ollama als lokaal geconfigureerd)
   - Resultaat als markdown → PDF via WeasyPrint

6. Frontend outputpagina:
   - Lijst van te genereren documenten (checkboxes)
   - "Genereer output" knop met voortgangsbar
   - Documentenlijst met downloadknoppen
   - "AI werkplan genereren" knop (apart, optioneel)
   - Versiebeheer: oude documenten blijven bewaard

**Acceptatiecriteria:**
- PDF tekening bevat titelblok, situatietekening en lengteprofiel
- DWG tekening opent in AutoCAD met correcte lagenstructuur
- Bestandsgrootte PDF < 5 MB voor standaard project
- Download start binnen 3 seconden na klikken
- Werkplan PDF bevat alle verplichte secties gevuld met projectdata
- AI werkplan genereert zinvolle tekst in < 60 seconden
- Documenten blijven bewaard na regenereren (versienummer verhoogd)

---

### Sprint 9 — Integratie & QA (1.5 week)

**Doel:** Volledige workflow end-to-end getest; klaar voor productie.

**Taken:**

1. End-to-end test schrijven voor complete workflow (pytest + playwright):
   - Project aanmaken → locatie instellen → KLIC uploaden → ontwerp genereren → PDF downloaden

2. Performance optimalisaties:
   - PostGIS indices controleren
   - N+1 queries elimineren (SQLAlchemy eager loading)
   - API responstijden meten: alle endpoints < 500ms

3. Foutafhandeling hardening:
   - Alle ARQ workers hebben retry logica (max 3 pogingen)
   - Gebruikersvriendelijke foutmeldingen (geen stack traces in productie)
   - Logging naar structured JSON (structlog)

4. Security checklist:
   - SQL injection: alleen parameterized queries via SQLAlchemy
   - Bestandsupload: MIME-type validatie, maximale bestandsgrootte (50 MB)
   - S3 URLs: signed URLs met TTL voor downloads (geen publieke buckets)
   - CORS: alleen eigen domein whitelisten

5. Docker productie configuratie:
   - Nginx reverse proxy voor frontend + backend
   - SSL termination
   - Environment variabelen via .env.prod
   - Automatische database backup via cron

6. Gebruikersacceptatietest (UAT):
   - 2 werkvoorbereiders en 1 engineer doorlopen workflow met testproject
   - Bevindingen verwerken

**Acceptatiecriteria:**
- End-to-end test is groen in CI
- Alle Must Have user stories uit Epics 1-7 zijn geimplementeerd
- Geen openstaande kritieke bugs
- Productie Docker Compose draait stabiel op VPS
- UAT goedgekeurd door opdrachtgever

---

## 5. Technische Aandachtspunten voor de Builder Agent

### 5.1 Coordinatenstelsel Strategie

Alle geometrie wordt intern opgeslagen in **RD New (EPSG:28992)** (meter-gebaseerd, geschikt voor Nederlandse afstandsberekeningen). De API accepteert en retourneert **WGS84 (EPSG:4326)** (lat/lon). Gebruik pyproj voor alle transformaties. Leaflet werkt in WGS84 — transformeer altijd vóór opslaan, en na ophalen.

```python
from pyproj import Transformer
wgs84_to_rd = Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)
rd_to_wgs84 = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
```

### 5.2 ARQ Worker Configuratie

ARQ gebruikt Redis als queue. Elke worker-functie heeft:
- `max_tries = 3`
- `timeout = 300` seconden voor zware jobs (PDF/DWG generatie)
- Job ID wordt direct teruggegeven; client pollt status endpoint elke 3 seconden

### 5.3 KLIC GML Parsing

KLIC GML bestanden zijn IMKL 2.1 formaat. Gebruik `lxml` voor parsing. Let op:
- Namespaces zijn uitgebreid; gebruik XPath met namespace map
- Geometrie kan in RD New of WGS84 zijn (controleer `srsName` attribuut)
- Diepte staat in `diepteNauwkeurigheid` en `bovenkantLeiding` attributen
- Meerdere GML bestanden per KLIC aanvraag (één per netbeheerder)

### 5.4 ezdxf DWG Generatie

```python
import ezdxf
doc = ezdxf.new('R2018')  # AutoCAD 2018 compatibel
msp = doc.modelspace()
# Laag aanmaken
doc.layers.new(name='ONTWERP', dxfattribs={'color': 3, 'linetype': 'CONTINUOUS'})
# Geometrie toevoegen
msp.add_lwpolyline(points, dxfattribs={'layer': 'ONTWERP'})
```

Coördinaten in DWG: gebruik RD New in meters (zodat schaal 1:1000 klopt).

### 5.5 Boorcurve Algoritme Detail

Het boorcurve algoritme berekent een vlak 2D tracé (bovenaanzicht) en een dieptecurve (zijaanzicht/lengteprofiel) afzonderlijk. De 3D geometrie is de combinatie.

Lengteprofiel segmenten (van start naar eind):
1. Intredeboog: van maaiveld naar werkdiepte (hoek θ_in, boogstraal R_in)
2. Horizontaal segment: op constante diepte
3. Uittredeboog: van werkdiepte naar maaiveld (hoek θ_uit, boogstraal R_uit)

Minimale boogstraal constraint: `R_min = (E * D_buiten) / (2 * σ_toelaatbaar_buig * 1000)` waarbij E = elasticiteitsmodulus leiding.

---

### Critical Files for Implementation

- `/backend/app/services/design_engine.py` - Kern van het platform: boorcurve algoritme, conflict check, versielogica — meest complexe module om te implementeren
- `/backend/app/services/calc_engine.py` - Deterministiche berekeningsmodules (sterkte, intrekkracht, slurrydruk) met alle formules en norm-referenties
- `/backend/app/services/doc_generator.py` - PDF (WeasyPrint) en DWG (ezdxf) generatie, titelblok en lagenstructuur
- `/backend/app/services/geo_service.py` - KLIC GML parsing, BGT API integratie, PostGIS geometrie operaties en coordinatentransformaties
- `/backend/alembic/versions/0001_initial_schema.py` - Initiële database migratie met alle tabellen, PostGIS kolommen, indices en constraints uit sectie 3.2
