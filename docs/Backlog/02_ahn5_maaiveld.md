# Bouwopdracht — Backlog item 2: AHN5 PDOK WCS — maaiveld automatisch ophalen

**HDD Ontwerp Platform · LeanAI Software Factory**
Versie: 1.0 | 2026-03-15
Opgesteld door: Architect Agent

---

## 1. Doel

Vervang de handmatige invoer van MVin en MVuit op de brondata-pagina door automatisch ophalen van maaiveldwaarden via de AHN5 WCS-service van PDOK. De gebruiker ziet na het opslaan van het tracé direct de opgehaalde waarden. Het override-principe blijft volledig van kracht: als AHN5 faalt, of als de gebruiker de waarde aanpast, valt het systeem terug op handmatige invoer. Automatisch opgehaalde waarden worden gemarkeerd met bron `"ahn5"`. Handmatig overschreven waarden worden gemarkeerd met bron `"handmatig"` en een timestamp.

---

## 2. Scope

### Wel in scope

- Nieuwe module `app/geo/ahn5.py` met één publieke functie `haal_maaiveld_op(rd_x, rd_y) -> float | None`
- AHN5 opvragen voor intree-punt (TracePunt type `"intree"`) en uittree-punt (TracePunt type `"uittree"`) van het project
- Nieuwe route `POST /api/v1/projecten/{project_id}/maaiveld/ahn5` die de WCS aanroept en het resultaat opslaat
- Uitbreiding `MaaiveldOverride`: vier extra kolommen (`MVin_bron`, `MVuit_bron`, `MVin_ahn5_m`, `MVuit_ahn5_m`)
- UI-update op `brondata.html`: knop "Ophalen via AHN5", statusindicatie per waarde, handmatig formulier altijd zichtbaar als fallback
- Alembic-migratie voor de nieuwe kolommen
- Testmodule `tests/test_ahn5.py` met alle acceptatiecriteria

### Niet in scope

- Tussenliggende sensorpunten opvragen (alleen intree en uittree)
- Hoogteprofiel langs het volledige tracé
- Asynchrone achtergrondtaak — de WCS-aanroep is synchroon (timeout 8s)
- Cachen van AHN5-resultaten buiten de database
- BGT, BAG, of andere PDOK-services
- Enige vorm van AI of LLM

---

## 3. Technische keuzes

### PDOK WCS endpoint

```
Base URL:   https://service.pdok.nl/rws/ahn/wcs/v1_0
Service:    WCS
Version:    2.0.1
Coverage:   dtm_05m
CRS:        EPSG:28992 (RD New — native voor AHN5)
Format:     image/tiff (GeoTIFF, 1×1 pixel)
```

Subset-query voor één punt `(x, y)` met buffer van 1 meter:

```
?SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage
&COVERAGEID=dtm_05m&SUBSETTINGCRS=EPSG:28992
&SUBSET=X(x-1,x+1)&SUBSET=Y(y-1,y+1)&FORMAT=image/tiff
```

### Library-keuze

- `httpx` voor HTTP (al in requirements)
- `rasterio` voor GeoTIFF uitlezen — toevoegen aan `requirements.txt`

### Foutafhandeling

`haal_maaiveld_op` geeft `None` terug bij:
- HTTP-fout (4xx, 5xx)
- Timeout (> 8 seconden)
- Lege of ongeldige GeoTIFF-response
- Pixelwaarde is NoData (`-9999.0` of `nan`)

Nooit een exception laten propageren — altijd `None` teruggeven en loggen via Python `logging`.

### Geen async

Synchroon via `def`-route (geen `async def`).

---

## 4. Datamodel

### Uitbreiding MaaiveldOverride

```python
MVin_bron    = Column(String, default="handmatig")   # "handmatig" | "ahn5" | "niet_beschikbaar"
MVuit_bron   = Column(String, default="handmatig")
MVin_ahn5_m  = Column(Float, nullable=True)           # AHN5-referentiewaarde, nooit gewist
MVuit_ahn5_m = Column(Float, nullable=True)
```

Bestaande kolommen `MVin_NAP_m`, `MVuit_NAP_m`, `bron` blijven ongewijzigd en functioneel.

### Alembic-migratie

Nieuw versiebestand met 4 ADD COLUMN statements voor bovenstaande velden.

---

## 5. Routes

### Nieuw

```
POST /api/v1/projecten/{project_id}/maaiveld/ahn5
```

Roept AHN5 WCS aan voor intree- en uittree-punt. Slaat resultaat op. Retourneert JSON (altijd HTTP 200):

```json
// Succes:
{"status": "ok", "MVin_NAP_m": 1.03, "MVuit_NAP_m": 1.29, "MVin_bron": "ahn5", "MVuit_bron": "ahn5"}

// Gedeeltelijk:
{"status": "partial", "MVin_NAP_m": 1.03, "MVuit_NAP_m": null, "MVin_bron": "ahn5", "MVuit_bron": "niet_beschikbaar", "melding": "..."}

// Volledig mislukt:
{"status": "fout", "melding": "AHN5 service niet bereikbaar — vul handmatig in"}

// Geen tracé:
{"status": "fout", "melding": "Geen intree- of uittree-punt gevonden — sla eerst het tracé op"}
```

### Gewijzigd

```
POST /api/v1/projecten/{project_id}/maaiveld
```

Zet `MVin_bron` en `MVuit_bron` op `"handmatig"`. Bewaart `MVin_ahn5_m` / `MVuit_ahn5_m` ongewijzigd.

---

## 6. Acceptatiecriteria

```
TC-ahn-A  haal_maaiveld_op(103896.9, 489289.5) → float ∈ [0.71, 1.31] NAP
          (pytest.mark.external — skip als SKIP_EXTERNAL_CALLS=1)

TC-ahn-B  haal_maaiveld_op(104118.8, 489243.7) → float ∈ [0.97, 1.57] NAP
          (pytest.mark.external)

TC-ahn-C  Timeout (gemockt > 8s) → None, geen exception

TC-ahn-D  HTTP 500 (gemockt) → None, geen exception

TC-ahn-E  NoData pixel -9999.0 (mock GeoTIFF) → None

TC-ahn-F  Route met mock (1.01, 1.27) → MaaiveldOverride correct opgeslagen,
          MVin_bron="ahn5", MVuit_bron="ahn5", MVin_ahn5_m=1.01, status="ok"

TC-ahn-G  Route mock (1.01, None) → status="partial", MVuit_bron="niet_beschikbaar"

TC-ahn-H  Route zonder tracépunten → status="fout", melding bevat "intree"

TC-ahn-I  Handmatige invoer na AHN5 → MVin_bron="handmatig", MVin_ahn5_m ongewijzigd

TC-ahn-J  Alembic migratie → 4 nieuwe kolommen aanwezig in maaiveld_overrides

TC-ahn-K  AHN5-route roept haal_maaiveld_op aan met RD-coördinaten (niet WGS84)
```

---

## 7. Testdata

```python
HDD11_INTREE  = (103896.9, 489289.5)   # type="intree"
HDD11_UITTREE = (104118.8, 489243.7)   # type="uittree"
MV_IN_VERWACHT  = 1.01   # NAP m
MV_UIT_VERWACHT = 1.27   # NAP m
TOLERANTIE_M    = 0.30
```

---

## 8. UI brondata.html

1. Knop "Ophalen via AHN5" — POST via HTMX of form, redirect na succes
2. Statusindicatie per waarde: badge `"AHN5 {datum}"` / `"Handmatig {datum}"` / `"Niet beschikbaar"`
3. Handmatig formulier altijd zichtbaar — override-principe
4. Foutmelding inline bij AHN5-fout
5. AHN5-referentiewaarde tonen als hint als gebruiker heeft overschreven

---

## 9. Nieuwe bestanden

| Bestand | Status |
|---------|--------|
| `app/geo/ahn5.py` | Nieuw |
| `tests/test_ahn5.py` | Nieuw |
| `app/project/models.py` | +4 kolommen MaaiveldOverride |
| `app/project/router.py` | +1 route, maaiveld_opslaan gewijzigd |
| `app/templates/project/brondata.html` | AHN5-knop + statusindicatie |
| `alembic/versions/xxxx_ahn5_maaiveld.py` | Nieuw |
| `requirements.txt` | +rasterio |

---

## 10. Bouwvolgorde

1. Tests schrijven (mocks voor extern)
2. Alembic migratie + TC-ahn-J verifiëren
3. `app/geo/ahn5.py` + TC-ahn-C t/m E
4. Route + TC-ahn-F t/m I, K
5. Template update
6. TC-ahn-A en B tegen echte PDOK (mark.external)
7. Volledige testsuite — bestaande tests groen houden
