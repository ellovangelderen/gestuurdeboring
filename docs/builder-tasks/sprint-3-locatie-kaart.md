# Builder Task — Sprint 3: Locatie & Kaart

**Sprint:** 3 | **Duur:** 1 week | **Afhankelijkheden:** Sprint 2 compleet

---

## Doel

Start- en eindpunt van de boring vastleggen op de kaart. Bounding box automatisch berekenen voor latere KLIC-upload (sprint 4).

---

## Wat te bouwen

### Backend

#### `app/geo/service.py` (begin)

Coördinatentransformatie helpers:
```python
from pyproj import Transformer

def wgs84_naar_rd(lon: float, lat: float) -> tuple[float, float]:
    """WGS84 (lon, lat) → RD New (x, y) in meters. Voor interne berekeningen."""

def rd_naar_wgs84(x: float, y: float) -> tuple[float, float]:
    """RD New → WGS84. Voor API responses en kaartweergave."""

def valideer_in_nederland(lon: float, lat: float) -> bool:
    """Check: 3.0 ≤ lon ≤ 7.5 en 50.5 ≤ lat ≤ 53.8"""

def bereken_bounding_box_wgs84(
    start_lon, start_lat, eind_lon, eind_lat, buffer_m=250
) -> dict:
    """
    Bereken bounding box rondom tracé met buffer.
    Return: {min_lon, min_lat, max_lon, max_lat}
    """
```

#### `app/api/routers/locatie.py`

```
PUT /api/v1/projecten/{id}/locatie
  Auth: Bearer vereist
  Body: {
    "startpunt_lon": float,
    "startpunt_lat": float,
    "eindpunt_lon": float,
    "eindpunt_lat": float
  }
  Validatie:
    - Beide punten in Nederland
    - Minimale afstand: 10 meter
    - Maximale afstand: 5000 meter
  Response: locatie object
  Fout: 422 bij punten buiten Nederland

GET /api/v1/projecten/{id}/locatie
  Auth: Bearer vereist
  Response: {
    startpunt_lon, startpunt_lat,
    eindpunt_lon, eindpunt_lat,
    bounding_box: {min_lon, min_lat, max_lon, max_lat},
    afstand_m: float
  }
```

#### Tests (`tests/test_locatie.py`)

- Locatie opslaan met geldige coördinaten → 200
- Punten buiten Nederland → 422
- Bounding box bevat beide punten + buffer
- Transformatie heen-en-terug klopt op < 1cm

---

### Frontend

#### `src/components/KaartComponent.tsx`

Leaflet kaart:
- **Achtergrond:** OpenStreetMap tile layer (geen API key nodig)
- **Startmarker:** groen, label "Start", draggable
- **Eindmarker:** rood, label "Eind", draggable
- **Bounding box:** semi-transparante blauwe rechthoek
- **Verbindingslijn:** stippellijn start → eind
- **Modi:** `'locatie'` (klik plaatst markers) | `'klic'` | `'ontwerp'` | `'readonly'`
- Klik op kaart in locatie-modus → plaatst eerstvolgende ontbrekende marker (start → eind)

```typescript
interface KaartProps {
  startpunt?: {lon: number; lat: number}
  eindpunt?: {lon: number; lat: number}
  boundingBox?: {min_lon: number; min_lat: number; max_lon: number; max_lat: number}
  modus: 'locatie' | 'klic' | 'ontwerp' | 'readonly'
  onStartpuntWijziging?: (lon: number, lat: number) => void
  onEindpuntWijziging?: (lon: number, lat: number) => void
  // Extra layers voor later:
  klicObjecten?: GeoJSON.FeatureCollection
  ontwerp?: {tracé: GeoJSON.LineString; conflicten: Conflict[]}
}
```

#### `src/components/LocatiePanel.tsx`

Rechterpaneel naast de kaart:
- "Startpunt selecteren" / "Eindpunt selecteren" knoppen
- Coördinatenvelden: lon/lat invoer als alternatief voor kaart-klik
- Adreszoeken via PDOK locatieserver:
  ```
  https://api.pdok.nl/bzk/locatieserver/search/v3_1/free?q={zoekterm}&fq=type:adres
  ```
  Resultaten als dropdown → klik zoomt kaart + plaatst marker
- Afstandsweergave: "Tracélengte: ~{afstand}m"
- "Opslaan" knop → PUT `/projecten/{id}/locatie`
- Foutmelding bij coördinaten buiten Nederland

#### Integreren in `ProjectDetail.tsx`

Tabblad "Locatie" activeren. `KaartComponent` + `LocatiePanel` naast elkaar.

---

## Data in / Data uit

**In:** WGS84 coördinaten (lon, lat) van start en eindpunt
**Uit:** Locatie opgeslagen in DB, bounding box berekend voor KLIC-ophaalgebied

---

## Modules geraakt

- `app/geo/service.py` — nieuw, wordt uitgebreid in sprint 4
- `app/main.py` — locatie router registreren
- `ProjectDetail.tsx` — "Locatie" tabblad activeren

---

## Acceptatiecriteria

- [ ] Start- en eindpunt plaatsbaar via klikken op kaart
- [ ] Markers verplaatsbaar via drag, locatie wordt bijgewerkt (debounce 500ms)
- [ ] Adreszoeken via PDOK werkt voor Nederlandse adressen
- [ ] Coördinaten buiten Nederland → foutmelding "Locatie ligt buiten Nederland"
- [ ] Bounding box past aan bij verplaatsen markers
- [ ] Locatie bewaard na herladen pagina

---

## User Stories

- Epic 2 Must have: "Als werkvoorbereider wil ik een locatie selecteren via kaart of adres"
- Epic 2 Must have: "Als werkvoorbereider wil ik start- en eindpunt vastleggen op de kaart"
