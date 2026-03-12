# Builder Task — Sprint 6: HDD Design Engine

**Sprint:** 6 | **Duur:** 3 weken | **Afhankelijkheden:** Sprint 5 compleet

---

## Doel

Automatisch een boorcurve genereren op basis van locatie, KLIC-data en eisenprofiel. Engineer kan het ontwerp beoordelen in kaart- en profielweergave, aanpassen en accorderen.

Dit is de zwaarste sprint — iteratief te bouwen in 3 weken.

---

## Wat te bouwen

### Week 1 — Algoritme fundament

#### `app/models/ontwerp.py`

SQLAlchemy modellen:

**`hdd.ontwerpen`:**
- `id` (UUID, PK)
- `project_id` (UUID FK → projecten)
- `versie_nummer` (int — 1, 2, 3, ...)
- `is_huidig` (bool — slechts 1 per project True)
- `status` (enum: berekend/akkoord/waarschuwing/afgekeurd)
- `geaccordeerd_door_id` (UUID FK → gebruikers, nullable)
- `geaccordeerd_op` (datetime, nullable)
- `tracé_lijn` (PostGIS LINESTRING 2D, SRID=28992 — bovenaanzicht)
- `aangemaakt_op` (datetime)
- `opmerking` (str, nullable)

**`hdd.ontwerp_parameters`** (één-op-één met ontwerp):
- `id` (UUID, PK)
- `ontwerp_id` (UUID FK → ontwerpen)
- `totale_lengte_m` (float)
- `maximale_diepte_m` (float)
- `intrede_hoek_graden` (float)
- `uittrede_hoek_graden` (float)
- `boogstraal_intrede_m` (float)
- `boogstraal_uittrede_m` (float)
- `lengte_horizontaal_m` (float)
- `lengte_intredeboog_m` (float)
- `lengte_uittredeboog_m` (float)

**`hdd.ontwerp_lengteprofiel_punten`:**
- `id` (UUID, PK)
- `ontwerp_id` (UUID FK → ontwerpen)
- `afstand_m` (float — afstand langs tracé)
- `diepte_m` (float — diepte in meters onder maaiveld, positief = dieper)
- `volgorde` (int)

**`hdd.ontwerp_validaties`:**
- `id` (UUID, PK)
- `ontwerp_id` (UUID FK → ontwerpen)
- `regel_type` (str)
- `status` (enum: OK/WAARSCHUWING/AFGEKEURD)
- `berekende_waarde` (float)
- `norm_waarde` (float)
- `bericht` (str)

**`hdd.ontwerp_conflicten`:**
- `id` (UUID, PK)
- `ontwerp_id` (UUID FK → ontwerpen)
- `klic_object_id` (UUID FK → klic_objecten)
- `minimale_afstand_m` (float)
- `ernst` (enum: KRITIEK/WAARSCHUWING/INFO)
- `dichtstbijzijnd_punt_ontwerp` (PostGIS POINT, SRID=28992)
- `dichtstbijzijnd_punt_klic` (PostGIS POINT, SRID=28992)

#### `app/services/design_engine.py`

**Hoofdfunctie:**
```python
def genereer_ontwerp(
    startpunt_rd: tuple[float, float],   # (x, y) in RD New
    eindpunt_rd: tuple[float, float],    # (x, y) in RD New
    min_diepte_m: float,                 # uit eisenprofiel
    max_boogstraal_m: float,             # uit leidingspecificaties
    intrede_hoek_graden: float = 12.0,  # default
    uittrede_hoek_graden: float = 12.0, # default
) -> OntwerpResultaat:
```

**Algoritme stappen:**

1. **Rechte lijn** tussen start en eindpunt (bovenaanzicht = 2D)

2. **Lengteprofiel berekenen** (zijaanzicht):

   Segment 1 — Intredeboog (van maaiveld naar werkdiepte):
   ```
   Boogstraal R_in = min_diepte / (1 - cos(θ_in))
   Valideer: R_in ≥ max_boogstraal_m (anders: vergroot hoek)
   Lengte intredeboog = R_in * sin(θ_in) (horizontale projectie)
   Diepte op einde intredeboog = min_diepte
   ```

   Segment 2 — Horizontaal segment:
   ```
   Lengte = totale horizontale afstand - lengte_intredeboog - lengte_uittredeboog
   Valideer: lengte > 0 (anders: project is te kort voor deze eisen)
   ```

   Segment 3 — Uittredeboog (van werkdiepte naar maaiveld):
   ```
   Spiegeling van intredeboog (zelfde R_uit = R_in tenzij anders opgegeven)
   ```

3. **Puntenreeks genereren** voor lengteprofiel:
   - Elke 1 meter een punt: `(afstand_m, diepte_m)`
   - Minimaal 50 punten

4. **Bovenaanzicht tracé** als rechte lijn (simplificatie voor MVP):
   - LineString van startpunt naar eindpunt in RD New

**Conflictdetectie (`detecteer_conflicten`):**
```python
def detecteer_conflicten(
    tracé_lijn: LineString,         # PostGIS geometry
    klic_objecten: list[KlicObject],
    buffer_m: float = 0.5
) -> list[Conflict]:
    """
    1. Buffer tracé met 0.5m (shapely)
    2. Controleer welke KLIC objecten de buffer snijden (spatiale query PostGIS)
    3. Bereken minimale afstand per conflict
    4. Classificeer ernst:
       - afstand < 0.3m → KRITIEK
       - afstand < 1.0m → WAARSCHUWING
       - afstand < 2.0m → INFO
    5. Bepaal dichtstbijzijnde punten (voor weergave)
    """
```

**Unit tests voor design engine (`tests/test_design_engine.py`):**
- Bekende invoer → verwachte outputparameters (handmatig berekend)
- Boogstraal altijd ≥ max_boogstraal constraint
- Horizontaal segment altijd positief
- Conflictdetectie: overlappende geometrie → KRITIEK conflict
- Geen KLIC objecten → geen conflicten

---

### Week 2 — API en async

#### `app/workers/design_worker.py`

```python
async def genereer_ontwerp_worker(ctx, project_id: str, parameters: dict):
    """
    1. Haal locatie, eisenprofiel, KLIC objecten op
    2. Roep design_engine.genereer_ontwerp() aan
    3. Sla Ontwerp, OntwerpParameters, lengteprofiel punten op
    4. Roep rule_engine.valideer_ontwerp_tegen_profiel() aan
    5. Sla validatieresultaten op
    6. Sla conflicten op
    7. Bepaal ontwerp status (akkoord/waarschuwing/afgekeurd)
    8. Update async_jobs status
    max_tries = 1 (niet retrien, deterministische berekening)
    timeout = 60
    """
```

#### `app/routers/ontwerp.py`

```
POST /api/v1/projecten/{id}/ontwerp/genereer
  Auth: Bearer vereist
  Body: {} of {intrede_hoek_graden: float, uittrede_hoek_graden: float}
  Vereiste: locatie en kruisingsobject moeten aanwezig zijn
  Response: {"job_id": str, "status": "gestart"}
  Actie: ARQ worker starten

GET /api/v1/projecten/{id}/ontwerp/genereer/{job_id}/status
  Response: {"status": "wacht/bezig/klaar/fout", "ontwerp_id": str}

GET /api/v1/projecten/{id}/ontwerp
  Response: volledig ontwerp object met parameters, validaties, conflicten

GET /api/v1/projecten/{id}/ontwerp/lengteprofiel
  Response: [{afstand_m: float, diepte_m: float}] (puntenreeks)

GET /api/v1/projecten/{id}/ontwerp/tracé
  Response: GeoJSON LineString (WGS84)

PUT /api/v1/projecten/{id}/ontwerp/aanpassen
  Auth: Bearer vereist (engineer of beheerder)
  Body: {intrede_hoek_graden, uittrede_hoek_graden, max_diepte_m} (alle optioneel)
  Actie: SYNCHROON herberekenen (< 5 sec), nieuwe versie aanmaken, vorige is_huidig=False
  Response: nieuw ontwerp object

GET /api/v1/projecten/{id}/ontwerp/versies
  Response: [{versie_nummer, status, aangemaakt_op, opmerking}]

GET /api/v1/projecten/{id}/ontwerp/versies/{versie_nummer}
  Response: volledig historisch ontwerp

PUT /api/v1/projecten/{id}/ontwerp/accordeer
  Auth: engineer of beheerder vereist
  Body: {} (optioneel opmerking)
  Vereiste: ontwerp status is niet 'afgekeurd'
  Response: bijgewerkt ontwerp

GET /api/v1/projecten/{id}/ontwerp/conflicten
  Response: lijst van conflicten met klic object details
```

---

### Week 3 — Frontend

#### `src/components/OntwerKaartlaag.tsx`

Leaflet layer voor het boortracé:
- Tracé lijn, kleur op basis van validatiestatus:
  - Akkoord → groen
  - Waarschuwing → oranje
  - Afgekeurd → rood
  - Berekend (nog niet gevalideerd) → blauw
- Conflictmarkers:
  - KRITIEK → rood uitroepteken
  - WAARSCHUWING → oranje waarschuwingsdriehoek
  - INFO → blauw info-icoontje
- Klik op conflict → sidebar met details (KLIC object info, afstand)

#### `src/components/LengteProfiel.tsx`

SVG-grafiek (gebruik recharts of D3):
- X-as: afstand langs tracé in meters
- Y-as: diepte t.o.v. maaiveld (0 = maaiveld, positief = dieper)
- Y-as omgekeerd (dieper is lager in grafiek)
- Maaiveldlijn (y=0, horizontale lijn)
- Tracélijn (uit lengteprofiel punten)
- Minimale dieptegrens (rode stippellijn = min_diepte_m uit eisenprofiel)
- KLIC object doorsnijtepunten (als beschikbaar: verticale lijn op afstand)
- Hover: tooltip met afstand en diepte
- Interactief: zoom via scroll, pan via drag

#### `src/components/OntwerpPanel.tsx`

Rechterpaneel:
- **Parameters sectie:**
  - Totale boorlengte
  - Maximale diepte
  - Intredehoek / uittredehoek
  - Boogstraal intrede / uittrede
  - Horizontale lengte

- **Aanpassen sectie (engineer):**
  - Slider: intredehoek (0-30°)
  - Slider: uittredehoek (0-30°)
  - Invoerveld: maximale diepte (m)
  - "Herberekenen" knop → PUT aanpassen → update kaart + profiel

- **Validaties sectie:**
  - Tabel: regel, berekende waarde, norm, status (groen/oranje/rood icoon)

- **Conflicten sectie:**
  - Lijst van conflicten, gesorteerd op ernst
  - Per conflict: klic type, beheerder, afstand
  - Klik → zoom op kaart naar conflict

- **Accorderen sectie (engineer/beheerder):**
  - "Accordeer ontwerp" knop (disabled als afgekeurd)
  - Waarschuwing als status WAARSCHUWING: "Ontwerp bevat waarschuwingen. Weet u zeker dat u wilt accorderen?"

#### Integratie in `ProjectDetail.tsx`

Tabblad "Ontwerp" (stap 4-5 van workflow):
- "Genereer ontwerp" knop → polling tot klaar
- Laad kaart (locatie + KLIC + BGT + ontwerp lagen)
- Lengteprofiel grafiek eronder
- `OntwerpPanel` aan de rechterkant
- Versiehistorie: dropdown om oudere versies te bekijken (readonly)

---

## Data in / Data uit

**In:**
- startpunt + eindpunt (uit locatie)
- min_diepte_m, max_intredehoek, beschermingszone (uit eisenprofiel)
- leiding specs: min_boogstraal (uit nieuwe_leiding)
- KLIC objecten (uit database)

**Uit:**
- Ontwerp met versienummer
- OntwerpParameters (lengte, diepte, hoeken, boogstralen)
- Lengteprofiel puntenreeks
- Tracé GeoJSON
- Validatieresultaten (per eisenprofiel regel)
- Conflicten lijst

---

## Modules geraakt

- `app/services/rule_engine.py` — `valideer_ontwerp_tegen_profiel()` aanroepen
- `app/services/geo_service.py` — spatiale queries voor conflictdetectie
- `app/workers/settings.py` — `genereer_ontwerp_worker` toevoegen
- `ProjectDetail.tsx` — "Ontwerp" tabblad activeren

---

## Acceptatiecriteria

- [ ] "Genereer ontwerp" klikken → ontwerp verschijnt binnen 30 seconden
- [ ] Tracé respecteert minimale diepte uit eisenprofiel
- [ ] Boogstraal is altijd ≥ minimum boogstraal uit leidingspecificaties
- [ ] Alle KLIC conflicten gedetecteerd en geclassificeerd
- [ ] Engineer kan intredehoek aanpassen → herberekening < 5 seconden → versie 2 aangemaakt
- [ ] Versie 1 blijft bewaard en bekijkbaar na aanpassing
- [ ] Lengteprofiel grafiek toont tracé, maaiveld en minimale dieptegrens
- [ ] Accordering alleen mogelijk voor engineer/beheerder rol
- [ ] Accordering geeft waarschuwing bij ontwerp-status WAARSCHUWING

---

## User Stories

- Epic 4 Must have: "Als engineer wil ik een automatisch gegenereerde boorcurve zien"
- Epic 4 Must have: "Als engineer wil ik de berekende ontwerp-parameters zien"
- Epic 4 Must have: "Als engineer wil ik waarschuwingen zien bij conflicten met KLIC"
- Epic 4 Must have: "Als engineer wil ik het ontwerp handmatig kunnen aanpassen"
- Epic 4 Should have: "Als engineer wil ik het ontwerp in bovenaanzicht én lengteprofiel zien"
- Epic 4 Should have: "Als engineer wil ik een statusindicatie van het ontwerp zien"
