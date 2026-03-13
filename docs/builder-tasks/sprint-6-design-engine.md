# Builder Task — Sprint 6: HDD Design Engine

**Sprint:** 6 | **Duur:** 2.5 week | **Afhankelijkheden:** Sprint 5 compleet

---

## Doel

Automatisch een boorcurve genereren. Engineer beoordeelt in kaart + lengteprofiel, past aan en herberekent.

> **Versiebeheer per ontwerp** (bewaren van historische versies, vergelijken) **hoort in iteratie 2.**
> In iteratie 1: één ontwerp per project. Herberekenen overschrijft het bestaande ontwerp.

> **Accorderen door engineer** (met rolcontrole) **hoort in iteratie 2** samen met gebruikersrollen.

> **Geen async queue.** Ontwerp genereren is synchroon (< 5 seconden voor standaard project).

---

## Wat te bouwen

### Week 1 — Algoritme

#### `app/design/engine.py`

```python
from shapely.geometry import LineString, Point
import math

def genereer_ontwerp(
    startpunt: tuple[float, float],   # (lon, lat) WGS84
    eindpunt: tuple[float, float],    # (lon, lat) WGS84
    min_diepte_m: float,              # uit eisenprofiel
    beschermingszone_m: float,        # uit eisenprofiel
    min_boogstraal_m: float,          # max(eisenprofiel, leiding.min_boogstraal_m)
    entry_angle_deg: float = 11.0,    # default intredehoek
    exit_angle_deg: float = 11.0,     # default uittredehoek
) -> OntwerpResultaat:
    """
    Berekening in RD New (meters) — transformeer invoer eerst.

    Stap 1: Rechte lijn start → eind (bovenaanzicht = WKT LineString)
    Stap 2: Lengteprofiel berekenen (zijaanzicht):
      - Intredeboog: van maaiveld naar werkdiepte
        R_in = boogstraal
        Valideer: R_in ≥ min_boogstraal_m
        Horizontale lengte intrede = R_in * sin(entry_angle_rad)
        Diepte intrede = R_in * (1 - cos(entry_angle_rad))
      - Horizontaal segment: op werkdiepte (= min_diepte_m)
        Lengte = totale_horizontale_lengte - lengte_intrede - lengte_uittrede
        Valideer: lengte > 0 (anders: punt is te dicht bij obstakel of hoek te groot)
      - Uittredeboog: spiegeling van intredeboog
    Stap 3: Puntenreeks genereren elke 1 meter (min 20 punten)
    Stap 4: Totale boorlengte berekenen (langs curve)
    """
```

```python
def detecteer_conflicten(
    boorcurve_wkt: str,         # WKT LineString in RD New
    klic_objecten: list[dict],  # uit database
    buffer_m: float = 0.5
) -> list[ConflictResultaat]:
    """
    1. Buffer boorcurve met buffer_m (shapely)
    2. Check elke KLIC-leiding op intersectie met buffer
    3. Bereken minimale afstand (boorcurve vs KLIC-leiding)
    4. Classificeer ernst:
       - afstand < 0.1m → KRITIEK
       - afstand < 0.5m → WAARSCHUWING
       - afstand < 2.0m → INFO
    """
```

#### Unit tests (`tests/test_design_engine.py`)

- Standaard invoer → correcte parameters (handmatig verificeerbaar):
  - start (0,0), eind (300,0), min_diepte=3m, boogstraal=150m, hoek=11°
  - Verwachte boorlengte ≈ 330m, max diepte ≈ 3m
- Boogstraal altijd ≥ min_boogstraal constraint
- Horizontaal segment > 0 (anders fout)
- Conflictdetectie: KLIC leiding op 0.3m → WAARSCHUWING
- Conflictdetectie: KLIC leiding op 0.05m → KRITIEK
- Geen KLIC objecten → lege conflictenlijst

---

### Week 2 — API

#### `app/design/models.py`

SQLAlchemy modellen voor `ontwerp`, `ontwerp_lengteprofiel`, `conflict` (schema aanwezig uit sprint 0).

#### `app/design/service.py`

```python
async def bereken_en_sla_op(project_id: UUID, params: dict, db) -> Ontwerp:
    """
    1. Haal locatie, kruisingsobject, eisenprofiel, leiding, klic_objecten op
    2. Roep design_engine.genereer_ontwerp() aan
    3. Roep design_engine.detecteer_conflicten() aan
    4. Valideer via rule_engine.valideer_ontwerp_tegen_profiel()
    5. Bepaal ontwerp status:
       - KRITIEK conflict → 'afkeur'
       - WAARSCHUWING conflict of validatiefout → 'waarschuwing'
       - Alles OK → 'akkoord'
    6. Sla ontwerp op (UPSERT — overschrijf bestaand ontwerp van dit project)
    7. Sla lengteprofiel punten op (verwijder eerst oude)
    8. Sla conflicten op (verwijder eerst oude)
    """
```

#### `app/api/routers/ontwerp.py`

```
POST /api/v1/projecten/{id}/ontwerp/genereer
  Auth: Bearer vereist
  Body: {} (of met custom hoeken: {entry_angle_deg, exit_angle_deg})
  Vereiste: locatie + kruisingsobject + eisenprofiel aanwezig
  Actie: synchroon berekenen + opslaan
  Response: volledig ontwerp object
  Fout: 422 als project niet gereed is voor berekening

GET /api/v1/projecten/{id}/ontwerp
  Response: {
    status, boorlengte_m, max_diepte_m, boogstraal_m,
    entry_angle_deg, exit_angle_deg,
    tracé_geojson: GeoJSON LineString (WGS84),
    aangemaakt_op, herberekend_op
  }

GET /api/v1/projecten/{id}/ontwerp/lengteprofiel
  Response: [{afstand_m: float, diepte_m: float}]

GET /api/v1/projecten/{id}/ontwerp/conflicten
  Response: [{klic_type, klic_beheerder, afstand_m, diepte_leiding_m, ernst}]

PUT /api/v1/projecten/{id}/ontwerp/aanpassen
  Auth: Bearer vereist
  Body: {entry_angle_deg?, exit_angle_deg?, min_boogstraal_override_m?}
  Actie: synchroon herberekenen, overschrijft huidig ontwerp
  Response: nieuw ontwerp object
```

---

### Week 3 — Frontend

#### `src/components/OntwerpKaartlaag.tsx`

Leaflet layer voor boortracé:
- Tracélijn, kleur op basis van ontwerp status:
  - akkoord → groen `#00AA00`
  - waarschuwing → oranje `#FF8C00`
  - afkeur → rood `#CC0000`
  - concept → blauw `#0066CC`
- Conflictmarkers op dichtstbijzijnd punt:
  - KRITIEK → rood ⚠ icoon
  - WAARSCHUWING → oranje ⚠ icoon
  - INFO → blauw ℹ icoon
- Klik op marker → popup met KLIC details + afstand

Integreer als layer in `KaartComponent`.

#### `src/components/LengteProfielGrafiek.tsx`

SVG grafiek (gebruik recharts `LineChart`):
- X-as: afstand langs tracé (0 tot boorlengte_m)
- Y-as: diepte (0 = maaiveld, positief = dieper) — omgekeerd
- Maaiveldlijn (y=0, zwart)
- Tracélijn (blauw)
- Minimale dieptegrens (rood stippellijn = min_diepte_m uit eisenprofiel)
- Hover: tooltip met afstand + diepte
- Responsive breedte

#### `src/components/OntwerpPanel.tsx`

Rechterpaneel (naast kaart):

**Parameters:**
- Boorlengte, max. diepte, boogstraal, intrede- en uittredehoek

**Aanpassen (inline formulier):**
- Slider: intredehoek (5°–20°)
- Slider: uittredehoek (5°–20°)
- "Herberekenen" knop → PUT aanpassen → kaart + profiel updaten

**Validaties:**
- Lijst van eisenprofiel checks (groen/oranje/rood)

**Conflicten:**
- Gesorteerd op ernst (kritiek eerst)
- Per conflict: type, beheerder, afstand

**Genereren knop:**
- "Genereer ontwerp" → POST genereer → loading indicator → resultaat tonen

#### Integreren in `ProjectDetail.tsx`

Tabblad "Ontwerp" activeren:
- Kaart (met KLIC + ontwerp lagen) boven/links
- `LengteProfielGrafiek` eronder
- `OntwerpPanel` rechts

---

## Data in / Data uit

**In:** locatie + eisenprofiel + leidingspecs + KLIC objecten
**Uit:** boorcurve WKT, parameters, lengteprofiel punten, conflictenlijst, status

---

## Modules geraakt

- `app/rules/service.py` — `valideer_ontwerp_tegen_profiel()` aanroepen
- `app/geo/service.py` — WKT ↔ GeoJSON conversie
- `KaartComponent.tsx` — ontwerp layer toevoegen

---

## Acceptatiecriteria

- [ ] "Genereer ontwerp" → boorcurve zichtbaar binnen 5 seconden
- [ ] Tracé respecteert minimale diepte uit eisenprofiel
- [ ] Boogstraal ≥ minimum (leiding of eisenprofiel)
- [ ] Alle KLIC conflicten gedetecteerd en geclassificeerd
- [ ] Herberekenen na hoek aanpassen werkt
- [ ] Lengteprofiel toont tracé, maaiveld en minimale dieptegrens
- [ ] Ontwerp bewaard na herladen pagina

---

## User Stories

- Epic 4 Must have: "Als engineer wil ik een automatisch gegenereerde boorcurve zien"
- Epic 4 Must have: "Als engineer wil ik de ontwerp-parameters zien"
- Epic 4 Must have: "Als engineer wil ik waarschuwingen bij KLIC-conflicten"
- Epic 4 Must have: "Als engineer wil ik het ontwerp handmatig kunnen aanpassen"
- Epic 4 Should have: "Als engineer wil ik het ontwerp in bovenaanzicht én lengteprofiel zien"
