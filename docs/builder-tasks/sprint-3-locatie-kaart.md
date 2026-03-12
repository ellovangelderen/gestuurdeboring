# Builder Task — Sprint 3: Locatie & Kaart

**Sprint:** 3 | **Duur:** 2 weken | **Afhankelijkheden:** Sprint 2 compleet

---

## Doel

Start- en eindpunt van de boring vastleggen op de kaart. Bounding box automatisch berekenen voor brondata (KLIC/BGT ophalen in sprint 4).

---

## Wat te bouwen

### Backend

#### `app/models/locatie.py`

SQLAlchemy model voor `hdd.locaties`:
- `id` (UUID, PK)
- `project_id` (UUID FK → projecten, unique — één locatie per project)
- `startpunt` (PostGIS POINT, SRID=28992, nullable)
- `eindpunt` (PostGIS POINT, SRID=28992, nullable)
- `bounding_box` (PostGIS POLYGON, SRID=28992, nullable — auto berekend)
- `startpunt_wgs84` (PostGIS POINT, SRID=4326, nullable — voor frontend)
- `eindpunt_wgs84` (PostGIS POINT, SRID=4326, nullable)
- `adres_start` (str, nullable)
- `adres_eind` (str, nullable)
- `bijgewerkt_op` (datetime)

#### `app/services/geo_service.py` (begin)

Coördinatentransformatie helpers:
```python
from pyproj import Transformer

wgs84_to_rd = Transformer.from_crs("EPSG:4326", "EPSG:28992", always_xy=True)
rd_to_wgs84 = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)

def wgs84_naar_rd(lon: float, lat: float) -> tuple[float, float]:
    """Converteer WGS84 (lon, lat) naar RD New (x, y) in meters."""
    return wgs84_to_rd.transform(lon, lat)

def rd_naar_wgs84(x: float, y: float) -> tuple[float, float]:
    """Converteer RD New (x, y) naar WGS84 (lon, lat)."""
    return rd_to_wgs84.transform(x, y)

def valideer_in_nederland(lon: float, lat: float) -> bool:
    """Check of coördinaten binnen Nederland vallen (ruime bounding box)."""
    return 3.0 <= lon <= 7.5 and 50.5 <= lat <= 53.8

def bereken_bounding_box(startpunt_rd, eindpunt_rd, buffer_m=250) -> Polygon:
    """Bereken bounding box met buffer van buffer_m meter rondom tracé."""
```

#### `app/routers/locatie.py`

```
PUT /api/v1/projecten/{id}/locatie
  Auth: Bearer vereist
  Body: {
    "startpunt": {"lon": float, "lat": float},
    "eindpunt": {"lon": float, "lat": float},
    "adres_start": str (optional),
    "adres_eind": str (optional)
  }
  Validatie:
    - Beide punten in Nederland (valideer_in_nederland)
    - Minimale afstand tussen punten: 10 meter
    - Maximale afstand: 5000 meter
  Response: locatie object (zie schema)
  Fout: 422 bij punten buiten Nederland

GET /api/v1/projecten/{id}/locatie
  Auth: Bearer vereist
  Response: {
    "startpunt": {"lon": float, "lat": float, "rd_x": float, "rd_y": float},
    "eindpunt": {"lon": float, "lat": float, "rd_x": float, "rd_y": float},
    "bounding_box": GeoJSON Polygon (WGS84),
    "afstand_m": float,
    "adres_start": str,
    "adres_eind": str
  }
```

#### Tests (`tests/test_locatie.py`)

- Locatie opslaan met geldige coordinaten → 200
- Coördinaten buiten Nederland → 422
- Bounding box is correct berekend (buffer van 250m)
- Coordinatentransformatie heen-en-terug klopt op 1cm nauwkeurigheid

---

### Frontend

#### `src/components/KaartComponent.tsx`

Leaflet kaart met:
- **Achtergrondlagen (layer control):**
  - OpenStreetMap (default)
  - PDOK luchtfoto (WMS: `https://service.pdok.nl/hwh/luchtfotorgb/wms/v1_0`)
- **Markers:**
  - Startpunt: groen marker met label "Start"
  - Eindpunt: rood marker met label "Eind"
  - Beide markers zijn draggable
  - Klik op kaart in "start selecteren" modus → plaatst startmarker
  - Klik op kaart in "eind selecteren" modus → plaatst eindmarker
- **Bounding box:** semi-transparante blauwe rechthoek
- **Lijn** tussen start en eind (stippellijn)

Props:
```typescript
interface KaartProps {
  startpunt?: {lon: number, lat: number}
  eindpunt?: {lon: number, lat: number}
  boundingBox?: GeoJSON.Polygon
  modus: 'locatie' | 'klic' | 'ontwerp' | 'readonly'
  onStartpuntWijziging?: (lon: number, lat: number) => void
  onEindpuntWijziging?: (lon: number, lat: number) => void
}
```

#### `src/components/LocatiePanel.tsx`

Rechterpaneel naast de kaart:
- "Startpunt selecteren" / "Eindpunt selecteren" knoppen (toggle modus)
- Coordinaten display in WGS84 (lat/lon) en RD New (X/Y)
- Adresveld: zoek op adres via PDOK locatieserver
  - API: `https://api.pdok.nl/bzk/locatieserver/search/v3_1/free?q={zoekterm}&fq=type:adres`
  - Resultaten als dropdown, klik zoomt kaart en plaatst marker
- Handmatige coordinaatvelden (WGS84 of RD New invoer)
- "Opslaan" knop → PUT `/api/v1/projecten/{id}/locatie`
- Afstandsweergave: "Tracélengte: ~{afstand} meter"

Integreer in `src/pages/ProjectDetail.tsx` als tabblad "Locatie" (stap 2 van de workflow).

#### `src/hooks/useLocatie.ts`

React Query hook:
- `useLocatie(projectId)` → query voor GET locatie
- `useLocatieOpslaan(projectId)` → mutation voor PUT locatie

---

## Data in / Data uit

**In:** WGS84 coördinaten (lon, lat) van start en eindpunt
**Uit:** Locatie opgeslagen in RD New (PostGIS), bounding box berekend, GeoJSON response voor frontend

---

## Modules geraakt

- `app/services/geo_service.py` — nieuw bestand aanmaken (wordt uitgebreid in sprint 4)
- `app/main.py` — locatie router registreren
- `ProjectDetail.tsx` — "Locatie" tabblad activeren

---

## Acceptatiecriteria

- [ ] Start- en eindpunt plaatsbaar via klikken op kaart
- [ ] Markers zijn verplaatsbaar via drag; API wordt bijgewerkt (debounce 500ms)
- [ ] Adreszoeken werkt voor Nederlandse adressen (PDOK locatieserver)
- [ ] Coördinaten buiten Nederland geven foutmelding: "Locatie ligt buiten Nederland"
- [ ] Bounding box wordt automatisch bijgewerkt bij verplaatsen markers
- [ ] Locatie blijft bewaard na herladen pagina (React Query cache + server state)
- [ ] Transformatie WGS84 ↔ RD New correct op < 1cm nauwkeurigheid

---

## User Stories

- Epic 2 Must have: "Als werkvoorbereider wil ik een locatie kunnen selecteren via kaart, adres of coördinaten"
- Epic 2 Must have: "Als werkvoorbereider wil ik start- en eindpunt van de boring kunnen vastleggen op de kaart"
