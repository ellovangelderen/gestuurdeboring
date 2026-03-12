# Builder Task — Sprint 4: KLIC & BGT Brondata

**Sprint:** 4 | **Duur:** 2 weken | **Afhankelijkheden:** Sprint 3 compleet

---

## Doel

KLIC GML-bestanden uploaden, parsen en op de kaart tonen. BGT-data ophalen via PDOK API. Handmatige dieptecorrectie van KLIC-objecten.

---

## Wat te bouwen

### Backend

#### `app/models/brondata.py`

SQLAlchemy modellen:

**`hdd.klic_uploads`:**
- `id` (UUID, PK)
- `project_id` (UUID FK → projecten)
- `bestandsnaam` (str)
- `s3_pad` (str)
- `status` (enum: geupload/verwerkt/fout)
- `foutmelding` (str, nullable)
- `aantal_objecten` (int, nullable)
- `geupload_op` (datetime)
- `verwerkt_op` (datetime, nullable)

**`hdd.klic_objecten`:**
- `id` (UUID, PK)
- `project_id` (UUID FK → projecten)
- `upload_id` (UUID FK → klic_uploads)
- `klic_type` (str — GAS/ELEKTRICITEIT/WATER/TELECOM/RIOOL/OVERIG)
- `beheerder` (str)
- `geometrie` (PostGIS LINESTRING/MULTILINESTRING, SRID=28992)
- `diepte_bovenkant_m` (float, nullable — diepte in meters onder maaiveld)
- `diepte_nauwkeurigheid` (str, nullable)
- `diepte_handmatig_gecorrigeerd` (bool, default False)
- `eigenschappen` (JSONB — overige KLIC attributen)
- `aangemaakt_op` (datetime)

**`hdd.bgt_objecten`:**
- `id` (UUID, PK)
- `project_id` (UUID FK → projecten)
- `bgt_type` (str — weg/water/spoor/gebouw/groen/talud)
- `geometrie` (PostGIS GEOMETRY, SRID=28992)
- `eigenschappen` (JSONB)
- `opgehaald_op` (datetime)

**`hdd.dwg_uploads`:**
- `id` (UUID, PK)
- `project_id` (UUID FK → projecten)
- `bestandsnaam` (str)
- `s3_pad` (str)
- `geupload_op` (datetime)

#### `app/services/geo_service.py` (uitbreiden)

**KLIC GML parsing (`verwerk_klic_gml(s3_pad, project_id, upload_id, db)`):**

```python
# IMKL 2.1 formaat
# Namespaces: imkl, gml, net, us-net-common
NAMESPACES = {
    'imkl': 'http://www.geostandaarden.nl/imkl/2015/wion/1.2',
    'gml': 'http://www.opengis.net/gml/3.2',
    ...
}

def parse_klic_gml(gml_inhoud: bytes) -> list[KlicObject]:
    """
    Parse IMKL 2.1 GML bestand.
    - Gebruik lxml etree voor parsing
    - Controleer srsName in geometrie: kan EPSG:28992 of EPSG:4326 zijn
    - Transformeer altijd naar EPSG:28992 voor opslag
    - Extraheer: geometrie, diepte (bovenkantLeiding), beheerder, type
    - Bepaal klic_type op basis van feature type naam
    """
```

Type mapping (feature naam → klic_type):
- `*Gas*`, `*Brandstof*` → `GAS`
- `*Elektriciteit*`, `*Hoogspanning*` → `ELEKTRICITEIT`
- `*Water*`, `*Riool*` van watertype → `WATER`
- `*Telecom*`, `*Datatransport*` → `TELECOM`
- `*Riool*` → `RIOOL`
- overig → `OVERIG`

**BGT ophalen (`haal_bgt_op(project_id, bounding_box, db)`):**

```python
# PDOK BGT WFS API
BGT_WFS_URL = "https://api.pdok.nl/lv/bgt/ogc/v1_0/collections/{collection}/items"
# Collections: wegdeel, waterdeel, spoor, pand, begroeidterreindeel, onbegroeidterreindeel

def haal_bgt_op(bounding_box_wgs84: Polygon, project_id: UUID, db: Session):
    """
    - Converteer bounding box naar WGS84 voor API call
    - Per BGT collection: GET met bbox parameter
    - GeoJSON response parsen
    - Geometrie transformeren naar RD New
    - Opslaan in hdd.bgt_objecten
    """
```

#### `app/workers/klic_worker.py`

ARQ worker functie:
```python
async def verwerk_klic_gml(ctx, project_id: str, upload_id: str):
    """
    1. Download GML van S3
    2. Parse alle KLIC objecten
    3. Sla op in database
    4. Update upload status
    max_tries = 3
    timeout = 300
    """
```

#### `app/workers/bgt_worker.py`

ARQ worker functie:
```python
async def haal_bgt_op_worker(ctx, project_id: str):
    """
    1. Haal bounding box op uit database
    2. Roep BGT API aan per collection
    3. Sla BGT objecten op
    4. Update status
    max_tries = 3
    timeout = 120
    """
```

#### `app/routers/brondata.py`

```
POST /api/v1/projecten/{id}/brondata/klic
  Content-Type: multipart/form-data
  Body: files (meerdere .gml bestanden, max 50MB per bestand)
  Validatie: MIME type check (text/xml of application/gml+xml)
  Response: [{upload_id, bestandsnaam, status: "geupload"}]
  Actie: upload naar S3, maak upload record aan, start ARQ worker

GET /api/v1/projecten/{id}/brondata/klic/status
  Response: [{upload_id, bestandsnaam, status, aantal_objecten, foutmelding}]

GET /api/v1/projecten/{id}/brondata/klic/objecten
  Response: GeoJSON FeatureCollection
  Query params: type (filter op klic_type)
  Elk feature heeft properties: {id, klic_type, beheerder, diepte_bovenkant_m, diepte_handmatig_gecorrigeerd}

PUT /api/v1/projecten/{id}/brondata/klic/objecten/{object_id}/diepte
  Body: {"diepte_bovenkant_m": float}
  Validatie: 0.0 ≤ diepte ≤ 50.0
  Response: bijgewerkt klic object
  Actie: diepte bijwerken, diepte_handmatig_gecorrigeerd=True

DELETE /api/v1/projecten/{id}/brondata/klic/{upload_id}
  Response: 204

POST /api/v1/projecten/{id}/brondata/bgt/ophalen
  Response: {"job_id": str, "status": "gestart"}
  Actie: start ARQ worker

GET /api/v1/projecten/{id}/brondata/bgt/status
  Response: {"status": "ophalen/klaar/fout", "aantal_objecten": int}

GET /api/v1/projecten/{id}/brondata/bgt/objecten
  Response: GeoJSON FeatureCollection
  Query params: type (filter op bgt_type)

POST /api/v1/projecten/{id}/brondata/dwg
  Content-Type: multipart/form-data
  Body: file (.dwg of .dxf, max 100MB)
  Response: {upload_id, bestandsnaam, s3_pad}

DELETE /api/v1/projecten/{id}/brondata/dwg/{upload_id}
  Response: 204
```

#### `app/workers/settings.py`

ARQ worker settings:
```python
class WorkerSettings:
    functions = [verwerk_klic_gml, haal_bgt_op_worker, ...]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 10
```

#### Tests

- KLIC GML parsing: test met een echt IMKL 2.1 fixture bestand (voeg toe aan `tests/fixtures/`)
- BGT ophalen: mock PDOK API, test parsing en opslag
- Dieptecorrectie: bijwerken en vlag zetten
- Upload status polling werkt

---

### Frontend

#### `src/components/KlicUploadZone.tsx`

- Drag-and-drop zone voor meerdere `.gml` bestanden
- Bestandsvalidatie: alleen .gml, max 50MB
- Voortgangsindicator per bestand (axios upload progress)
- Na upload: polling van `/brondata/klic/status` elke 3 seconden
- Samenvatting na verwerking: "X objecten geladen (Gas: N, Elektriciteit: N, ...)"
- Foutmelding per bestand als parsing mislukt

#### `src/components/KlicKaartlaag.tsx`

Leaflet layer voor KLIC objecten:
- Kleurcodering per type:
  - GAS → geel (`#FFD700`)
  - ELEKTRICITEIT → rood (`#FF0000`)
  - WATER → blauw (`#0000FF`)
  - TELECOM → oranje (`#FFA500`)
  - RIOOL → bruin (`#8B4513`)
  - OVERIG → grijs (`#808080`)
- Popup bij klikken: beheerder, type, diepte (met "onbekend" als null)
- Inline diepte bewerken in popup:
  - Invoerveld voor diepte
  - "Opslaan" knop → PUT `/brondata/klic/objecten/{id}/diepte`
  - Visuele indicator voor handmatig gecorrigeerde dieptes (ster-icoontje)
- Layer control: elke KLIC type aan/uitzetten

#### `src/components/BgtKaartlaag.tsx`

- "BGT ophalen" knop → POST `/brondata/bgt/ophalen` → polling status
- BGT objecten op kaart:
  - Wegen: lichtgrijs
  - Water: lichtblauw
  - Spoor: donkergrijs gestreept
  - Gebouwen: beige
- Layer control: BGT aan/uitzetten

#### `src/components/DwgUpload.tsx`

- Eenvoudig file upload veld voor .dwg/.dxf
- Bevestiging na upload
- Verwijder knop

Integreer alles in `ProjectDetail.tsx` als tabblad "Brondata" (stap 2 van de 7-staps workflow).

---

## Data in / Data uit

**In:** KLIC GML bestanden (IMKL 2.1 formaat), project bounding box voor BGT
**Uit:** KLIC objecten als GeoJSON met type/beheerder/diepte, BGT objecten als GeoJSON

---

## Modules geraakt

- `app/services/geo_service.py` — KLIC/BGT functies toevoegen
- `app/main.py` — brondata router en ARQ worker registreren
- `docker-compose.yml` — ARQ worker service was al aangemaakt in sprint 0, `WorkerSettings` nu vullen

---

## Acceptatiecriteria

- [ ] KLIC GML upload van 10 bestanden en 5000 objecten verwerkt binnen 60 seconden
- [ ] Alle KLIC objecten zichtbaar op kaart met juiste kleur en popup
- [ ] Diepte handmatig aanpasbaar; direct zichtbaar op kaart na opslaan
- [ ] BGT ophalen werkt voor bounding box van 500×500 meter (via PDOK)
- [ ] Bij fout in GML parsing: foutmelding met bestandsnaam, andere bestanden wel verwerkt
- [ ] MIME-type validatie: alleen .gml bestanden worden geaccepteerd
- [ ] Bestanden groter dan 50MB worden geweigerd met duidelijke melding

---

## User Stories

- Epic 2 Must have: "Als werkvoorbereider wil ik een KLIC GML-bestand kunnen uploaden"
- Epic 2 Must have: "Als engineer wil ik de geïmporteerde KLIC-objecten op de kaart zien"
- Epic 2 Must have: "Als werkvoorbereider wil ik BGT-data kunnen ophalen voor het projectgebied"
- Epic 2 Should have: "Als engineer wil ik de diepte van een bestaande leiding handmatig kunnen corrigeren"
