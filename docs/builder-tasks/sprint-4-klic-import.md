# Builder Task — Sprint 4: KLIC Import

**Sprint:** 4 | **Duur:** 1.5 week | **Afhankelijkheden:** Sprint 3 compleet

---

## Doel

KLIC GML-bestanden uploaden, synchroon parsen en op de kaart tonen. Handmatige dieptecorrectie mogelijk.

> **BGT API-integratie (PDOK) hoort in iteratie 2.** In iteratie 1 gebruikt de engineer de OpenStreetMap achtergrond als visuele context.

> **Geen async queue.** Voor een klein team (2–5 engineers) en bestanden < 50MB is synchroon verwerken voldoende. Als dit te traag blijkt, voegen we een queue toe in iteratie 2.

---

## Wat te bouwen

### Backend

#### `app/geo/klic_parser.py`

IMKL 2.1 GML parser:

```python
from lxml import etree
from shapely.geometry import shape
from pyproj import Transformer

NAMESPACES = {
    'imkl': 'http://www.geostandaarden.nl/imkl/2015/wion/1.2',
    'gml': 'http://www.opengis.net/gml/3.2',
    # voeg overige namespaces toe die voorkomen in echte KLIC bestanden
}

# Type mapping: feature tag naam → klic_type
TYPE_MAP = {
    'Gas': 'GAS',
    'Brandstof': 'GAS',
    'Elektriciteit': 'ELEKTRICITEIT',
    'Hoogspanning': 'ELEKTRICITEIT',
    'Water': 'WATER',
    'Telecom': 'TELECOM',
    'Datatransport': 'TELECOM',
    'Riool': 'RIOOL',
}

def parse_klic_gml(gml_inhoud: bytes) -> list[dict]:
    """
    Parse één IMKL 2.1 GML bestand.

    Per feature:
    - Bepaal klic_type op basis van feature class naam
    - Extraheer geometrie (LINESTRING of MULTILINESTRING)
    - Controleer srsName: EPSG:28992 of EPSG:4326
    - Transformeer altijd naar EPSG:28992 (RD New) voor opslag
    - Extraheer diepte uit bovenkantLeiding attribuut (float, meters)
    - Extraheer beheerder naam

    Return: list van dicts met {klic_type, beheerder, geometrie_wkt, diepte_m, eigenschappen}
    Fout bij ongeldig GML: raise ValueError met beschrijvende melding
    """
```

#### `app/geo/service.py` (uitbreiden)

```python
def geometrie_naar_geojson(wkt: str, srid_van: int = 28992) -> dict:
    """WKT (RD New) → GeoJSON feature (WGS84) voor frontend"""

def klic_objecten_naar_geojson(objecten: list[KlicObject]) -> dict:
    """Lijst KlicObject → GeoJSON FeatureCollection"""
```

#### `app/geo/models.py`

SQLAlchemy modellen voor `klic_upload` en `klic_object` (schema aanwezig uit sprint 0).

#### `app/api/routers/brondata.py`

```
POST /api/v1/projecten/{id}/brondata/klic
  Content-Type: multipart/form-data
  Body: files[] (.gml bestanden, max 50MB per bestand, max 20 bestanden)
  Validatie:
    - Bestandsextensie .gml
    - Bestandsgrootte ≤ 50MB per bestand
    - Maximaal 20 bestanden tegelijk
  Actie (synchroon):
    1. Sla elk bestand op op Railway volume
    2. Maak klic_upload record aan (status='verwerkt' direct)
    3. Parse GML direct in request handler
    4. Sla klic_objecten op in database
    5. Update klic_upload met aantal_objecten
  Response: [{upload_id, bestandsnaam, aantal_objecten, status}]
  Fout per bestand: als parsing faalt → status='fout', foutmelding opgeslagen, andere bestanden wel verwerkt

GET /api/v1/projecten/{id}/brondata/klic/objecten
  Response: GeoJSON FeatureCollection
  Query param: type (filter op klic_type)
  Properties per feature: {id, klic_type, beheerder, diepte_m}

GET /api/v1/projecten/{id}/brondata/klic/uploads
  Response: [{upload_id, bestandsnaam, status, aantal_objecten, foutmelding}]

PUT /api/v1/projecten/{id}/brondata/klic/objecten/{object_id}/diepte
  Body: {"diepte_m": float}
  Validatie: 0.0 ≤ diepte ≤ 50.0
  Response: bijgewerkt klic_object

DELETE /api/v1/projecten/{id}/brondata/klic/{upload_id}
  Response: 204
  Actie: verwijder upload record + alle bijbehorende klic_objecten + bestand van volume
```

Bestandsopslag:
```python
# Railway volume mount path uit config: STORAGE_PATH
# Pad opbouw: {STORAGE_PATH}/projecten/{project_id}/klic/{upload_id}/{bestandsnaam}
```

#### Tests (`tests/test_klic.py`)

- Gebruik een echt IMKL 2.1 fixture GML bestand in `tests/fixtures/`
- Upload + parsing → correcte klic_objecten in DB
- Type mapping correct (gas/elektriciteit/water/etc.)
- Geometrie correct getransformeerd naar RD New
- Fout bij corrupt GML → upload status 'fout', andere uploads wel verwerkt
- Diepte handmatig aanpassen → opgeslagen

---

### Frontend

#### `src/components/KlicUploadZone.tsx`

- Drag-and-drop zone voor meerdere `.gml` bestanden
- Bestandsvalidatie client-side: alleen .gml, max 50MB
- Upload voortgang per bestand (axios `onUploadProgress`)
- Na upload: samenvatting per bestand (bestandsnaam + N objecten of foutmelding)
- Totaal: "X objecten geladen (Gas: N, Elektriciteit: N, Water: N, ...)"

#### `src/components/KlicKaartlaag.tsx`

Leaflet layer voor KLIC objecten:
- Kleurcodering per type:
  - GAS → geel `#FFD700`
  - ELEKTRICITEIT → rood `#FF0000`
  - WATER → blauw `#0077CC`
  - TELECOM → oranje `#FF8C00`
  - RIOOL → bruin `#8B4513`
  - OVERIG → grijs `#888888`
- Popup bij klikken: type, beheerder, diepte ("onbekend" als null)
- Inline diepte bewerken in popup: invoerveld + "Opslaan" knop
- Layer control: elk type aan/uitzetten

Integreren als layer in bestaande `KaartComponent`.

#### Integreren in `ProjectDetail.tsx`

Tabblad "Brondata" activeren:
- `KlicUploadZone` bovenaan
- `KaartComponent` met `klicObjecten` prop gevuld

---

## Data in / Data uit

**In:** KLIC GML bestanden (IMKL 2.1 formaat)
**Uit:** `klic_object` records in DB + GeoJSON voor kaartweergave

---

## Modules geraakt

- `app/geo/service.py` — GeoJSON conversie toevoegen
- `app/main.py` — brondata router registreren
- `KaartComponent.tsx` — `klicObjecten` prop doorgeven

---

## Acceptatiecriteria

- [ ] KLIC GML upload van 5 bestanden verwerkt en zichtbaar op kaart binnen 30 seconden
- [ ] Alle KLIC objecten zichtbaar met juiste kleur en popup
- [ ] Diepte handmatig aanpasbaar via popup
- [ ] Fout in één GML bestand → foutmelding voor dat bestand, rest wel verwerkt
- [ ] Bestanden > 50MB worden geweigerd met melding
- [ ] KLIC objecten bewaard na herladen pagina

---

## User Stories

- Epic 2 Must have: "Als werkvoorbereider wil ik KLIC GML-bestanden kunnen uploaden"
- Epic 2 Must have: "Als engineer wil ik KLIC-objecten op de kaart zien"
- Epic 2 Should have: "Als engineer wil ik de diepte handmatig kunnen corrigeren"
