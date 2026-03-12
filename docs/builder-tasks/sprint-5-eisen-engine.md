# Builder Task — Sprint 5: Eisen Engine

**Sprint:** 5 | **Duur:** 1 week | **Afhankelijkheden:** Sprint 4 compleet

---

## Doel

Eisenprofielen koppelen aan het te kruisen object. Beheerder kan profielen beheren. 4 standaard profielen worden als seed-data meegeleverd.

---

## Wat te bouwen

### Backend

#### `app/models/eisen.py`

SQLAlchemy modellen (tabellen bestaan al uit sprint 0 migratie):

**`hdd.eisenprofielen`:**
- `id` (UUID, PK)
- `naam` (str, not null, unique)
- `beheerder_type` (str — RWS/WATERSCHAP/GEMEENTE/PRORAIL/ANDERS)
- `object_type` (str — RIJKSWEG/WATERKERING/GEMEENTEWEG/SPOOR/ANDERS)
- `omschrijving` (str, nullable)
- `actief` (bool, default True)
- `aangemaakt_op` (datetime)

**`hdd.eisenprofiel_regels`:**
- `id` (UUID, PK)
- `eisenprofiel_id` (UUID FK → eisenprofielen)
- `regel_type` (str — MIN_DIEPTE/BESCHERMINGSZONE/MIN_BOOGSTRAAL/MAX_INTREDEHOEK/MAX_UITTREDEHOEK)
- `waarde` (float)
- `eenheid` (str — m/graden)
- `omschrijving` (str, nullable)

**`hdd.kruisingsobjecten`:**
- `id` (UUID, PK)
- `project_id` (UUID FK → projecten, unique)
- `object_type` (str — RIJKSWEG/WATERKERING/GEMEENTEWEG/SPOOR/ANDERS)
- `beheerder_type` (str — RWS/WATERSCHAP/GEMEENTE/PRORAIL/ANDERS)
- `naam` (str — bijv. "A10 Amsterdam")
- `breedte_m` (float — breedte van het te kruisen object)
- `eisenprofiel_id` (UUID FK → eisenprofielen, nullable — auto-gekoppeld)
- `aanvullende_eisen` (str, nullable — vrije tekst)
- `bijgewerkt_op` (datetime)

#### `app/services/rule_engine.py`

```python
def koppel_eisenprofiel(beheerder_type: str, object_type: str, db: Session) -> EisenProfiel | None:
    """
    Zoek het meest specifieke eisenprofiel voor deze combinatie.
    Prioriteit: exact match beheerder + object > object only > beheerder only
    """

def valideer_ontwerp_tegen_profiel(ontwerp: Ontwerp, profiel: EisenProfiel) -> list[ValidatieResultaat]:
    """
    Controleer alle regels uit het profiel.
    Per regel: status = OK / WAARSCHUWING / AFGEKEURD
    Return lijst van ValidatieResultaat objecten.
    Wordt gebruikt in design engine sprint.
    """

class ValidatieResultaat:
    regel_type: str
    status: Literal['OK', 'WAARSCHUWING', 'AFGEKEURD']
    waarde: float
    norm: float
    bericht: str
```

#### Seed data (`app/seed_eisen.py`)

Maak 4 standaard eisenprofielen aan als ze nog niet bestaan:

| Naam | Beheerder | Object | Regels |
|---|---|---|---|
| RWS Rijksweg | RWS | RIJKSWEG | min_diepte=3.0m, beschermingszone=5.0m, max_intredehoek=15°, max_uittredehoek=15° |
| Waterschap Waterkering | WATERSCHAP | WATERKERING | min_diepte=7.5m, beschermingszone=10.0m, max_intredehoek=10° |
| Gemeente Gemeenteweg | GEMEENTE | GEMEENTEWEG | min_diepte=1.25m, beschermingszone=1.0m |
| ProRail Spoor | PRORAIL | SPOOR | min_diepte=4.0m, beschermingszone=8.0m, max_intredehoek=12° |

Aanroepen in `lifespan` na seed gebruikers.

#### `app/routers/eisen.py`

**Kruisingsobject (per project, alle rollen):**
```
PUT /api/v1/projecten/{id}/kruisingsobject
  Body: {object_type, beheerder_type, naam, breedte_m, aanvullende_eisen}
  Actie: automatisch eisenprofiel koppelen via rule_engine.koppel_eisenprofiel()
  Response: {kruisingsobject + gekoppeld eisenprofiel met regels}

GET /api/v1/projecten/{id}/kruisingsobject
  Response: {kruisingsobject + gekoppeld eisenprofiel met regels}
```

**Eisenprofielen CRUD (beheerder only):**
```
GET    /api/v1/eisenprofielen               → lijst (ook niet-beheerder voor dropdown)
POST   /api/v1/eisenprofielen               → aanmaken (beheerder only)
GET    /api/v1/eisenprofielen/{id}          → ophalen met regels
PUT    /api/v1/eisenprofielen/{id}          → bijwerken (beheerder only)
DELETE /api/v1/eisenprofielen/{id}          → deactiveren (beheerder only, actief=False)

POST   /api/v1/eisenprofielen/{id}/regels   → regel toevoegen (beheerder only)
PUT    /api/v1/eisenprofielen/{id}/regels/{regel_id} → regel bijwerken
DELETE /api/v1/eisenprofielen/{id}/regels/{regel_id} → regel verwijderen
```

#### Tests

- Kruisingsobject aanmaken met `RWS + RIJKSWEG` → automatisch profiel "RWS Rijksweg" gekoppeld
- Kruisingsobject aanmaken met `GEMEENTE + GEMEENTEWEG` → profiel "Gemeente Gemeenteweg"
- Onbekende combinatie → profiel null, geen fout
- Beheerder kan profiel aanmaken met regels
- Niet-beheerder kan geen profiel aanmaken → 403
- Seed levert 4 profielen na eerste start

---

### Frontend

#### `src/pages/Eisenprofielen.tsx` (beheerder only, admin sectie)

- Lijst van alle eisenprofielen (naam, beheerder_type, object_type, actief badge)
- "Nieuw profiel" knop → formulier modal
- Profiel bewerken: klik op rij → detail view
- Per profiel: regels tabel (type, waarde, eenheid)
- Regel toevoegen/bewerken/verwijderen via inline formulier

#### `src/components/KruisingsobjectFormulier.tsx`

Workflowstap 3 in `ProjectDetail.tsx`:

**Formulier:**
- Object type (dropdown): Rijksweg / Waterkering / Gemeenteweg / Spoorweg / Anders
- Beheerder type (dropdown): Rijkswaterstaat / Waterschap / Gemeente / ProRail / Anders
- Naam (tekst, bijv. "A10 Amsterdam")
- Breedte in meters (numeriek)
- Aanvullende eisen (textarea, vrije tekst)

**Na opslaan:**
- Automatisch gekoppeld eisenprofiel tonen in "Gekoppelde eisen" sectie
- Tabel met regels: type, waarde, eenheid, omschrijving
- Als geen profiel gevonden: gele melding "Geen standaard eisenprofiel gevonden. Voer aanvullende eisen handmatig in."

---

## Data in / Data uit

**In:** object_type + beheerder_type → automatisch eisenprofiel opzoeken
**Uit:** kruisingsobject + eisenprofiel regels (min_diepte, beschermingszone, etc.)

---

## Modules geraakt

- `app/main.py` — eisen router en seed_eisen aanroep in lifespan
- `app/services/rule_engine.py` — nieuw bestand, wordt aangesproken door design engine (sprint 6)

---

## Acceptatiecriteria

- [ ] "RWS rijksweg" selecteren → min. 3m diepte en 5m beschermingszone automatisch geladen
- [ ] Beheerder kan nieuw eisenprofiel aanmaken met regels
- [ ] Niet-beheerder ziet eisenprofielen (readonly) maar kan niet aanmaken
- [ ] Aanvullende projectspecifieke eisen opslaan als vrije tekst
- [ ] 4 seed-profielen aanwezig na eerste start
- [ ] Eisenprofiel deactiveren verbergt het uit de dropdowns (maar bestaande koppelingen blijven)

---

## User Stories

- Epic 3 Must have: "Als engineer wil ik het te kruisen object kunnen definiëren"
- Epic 3 Must have: "Als engineer wil ik een eisenprofiel kunnen laden per beheerder"
- Epic 3 Must have: "Als engineer wil ik de breedte en naam van het object kunnen opgeven"
- Epic 3 Should have: "Als beheerder wil ik eisenprofielen kunnen beheren en aanpassen"
- Epic 7 Should have: "Als beheerder wil ik eisenprofielen en normbibliotheken kunnen beheren"
