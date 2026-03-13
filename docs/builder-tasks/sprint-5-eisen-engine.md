# Builder Task — Sprint 5: Eisen Engine

**Sprint:** 5 | **Duur:** 0.5 week | **Afhankelijkheden:** Sprint 4 compleet

---

## Doel

Te kruisen object definiëren en het juiste eisenprofiel koppelen. Eisenprofielen zijn hardcoded seed data — geen beheerscherm in iteratie 1.

> **Eisenprofiel beheerscherm (UI voor aanmaken/bewerken/verwijderen van profielen) hoort in iteratie 3.**

---

## Wat te bouwen

### Backend

#### `app/rules/models.py`

SQLAlchemy modellen voor `eisenprofiel`, `te_kruisen_object`, `nieuwe_leiding` (schema aanwezig uit sprint 0).

#### `app/rules/service.py`

```python
async def koppel_eisenprofiel(
    beheerder_type: str,
    object_type: str,
    workspace_id: UUID,
    db: AsyncSession
) -> EisenProfiel | None:
    """
    Zoek het juiste eisenprofiel.
    Zoekprioriteit:
    1. Workspace-specifiek profiel (workspace_id match)
    2. Globaal profiel (workspace_id is NULL)
    Eerste exacte match op beheerder_type + object_type.
    """

async def valideer_ontwerp_tegen_profiel(
    ontwerp_params: dict,
    profiel: EisenProfiel
) -> list[ValidatieResultaat]:
    """
    Controleer ontwerp-parameters tegen eisenprofiel regels.
    Wordt aangeroepen vanuit design engine (sprint 6).
    """
```

#### `app/api/routers/eisen.py`

```
# Eisenprofielen — alleen ophalen (geen CRUD in iteratie 1)
GET /api/v1/eisenprofielen
  Auth: Bearer vereist
  Response: lijst van alle beschikbare profielen (globaal + workspace)

# Te kruisen object
PUT /api/v1/projecten/{id}/kruisingsobject
  Auth: Bearer vereist
  Body: {type, naam, breedte_m, beheerder_type, aanvullende_eisen}
  Actie: automatisch eisenprofiel koppelen via rule_engine
  Response: {kruisingsobject + gekoppeld eisenprofiel}

GET /api/v1/projecten/{id}/kruisingsobject
  Response: {kruisingsobject + gekoppeld eisenprofiel}

# Nieuwe leiding
PUT /api/v1/projecten/{id}/leiding
  Auth: Bearer vereist
  Body: {materiaal, buitendiameter_mm, wanddikte_mm, max_trekkracht_kn, min_boogstraal_m, met_mantelbuis}
  Response: leiding object

GET /api/v1/projecten/{id}/leiding
  Response: leiding object
```

#### Tests (`tests/test_eisen.py`)

- Kruisingsobject RWS + RIJKSWEG → profiel "RWS Rijksweg" (min 3.0m) gekoppeld
- Kruisingsobject GEMEENTE + GEMEENTEWEG → profiel "Gemeente Gemeenteweg"
- Onbekende combinatie → profiel null, geen fout
- Profiel ophalen → 4 profielen beschikbaar na seed

---

### Frontend

#### `src/components/KruisingsobjectFormulier.tsx`

Workflowstap "Eisen" in `ProjectDetail.tsx`:

**Te kruisen object:**
- Type (dropdown): Rijksweg / Waterkering / Provinciale weg / Gemeenteweg / Spoorweg / Anders
- Beheerder (dropdown): Rijkswaterstaat / Waterschap / Provincie / Gemeente / ProRail / Anders
- Naam (tekst, bijv. "A10 Amsterdam")
- Breedte in meters
- Aanvullende eisen (textarea)
- Submit → PUT → toon gekoppeld eisenprofiel

**Gekoppeld eisenprofiel weergave:**
- Naam profiel, beheerder, min. diepte, beschermingszone, min. boogstraal
- Als geen profiel gevonden: gele melding "Geen standaard profiel — gebruik aanvullende eisen"

#### `src/components/LeidingFormulier.tsx`

Formulier voor nieuwe leiding:
- Materiaal (dropdown): PE / HDPE / Staal / PVC / Anders
- Buitendiameter (mm)
- Wanddikte (mm)
- Max. trekkracht (kN)
- Min. boogstraal (m)
- Met mantelbuis (checkbox)

Integreer beide formulieren als tabblad "Eisen" in `ProjectDetail.tsx`.

---

## Data in / Data uit

**In:** beheerder_type + object_type → eisenprofiel opzoeken
**Uit:** kruisingsobject + eisenprofiel (min_diepte, beschermingszone, min_boogstraal) beschikbaar voor design engine

---

## Modules geraakt

- `app/rules/service.py` — nieuw, wordt aangeroepen door design engine (sprint 6)
- `app/main.py` — eisen router registreren

---

## Acceptatiecriteria

- [ ] RWS + Rijksweg → min. 3.0m diepte automatisch gekoppeld
- [ ] Gemeente + Gemeenteweg → min. 1.2m diepte gekoppeld
- [ ] Onbekende combinatie → geen crash, aanvullende eisen invoerbaar
- [ ] 4 seed-profielen aanwezig na deployment
- [ ] Leidinggegevens bewaard

---

## User Stories

- Epic 3 Must have: "Als engineer wil ik het te kruisen object kunnen definiëren"
- Epic 3 Must have: "Als engineer wil ik een eisenprofiel laden per beheerder"
