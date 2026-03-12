# Builder Task — Sprint 7: Technische Berekeningen

**Sprint:** 7 | **Duur:** 2 weken | **Afhankelijkheden:** Sprint 6 compleet

---

## Doel

Optionele technische berekeningen uitvoeren: sterktecontrole, intrekkracht (pullback force) en boorvloeistofdruk (slurry). Resultaten koppelen aan het ontwerp en waarschuwingen tonen.

---

## Wat te bouwen

### Week 1 — CalcEngine

#### `app/models/berekening.py`

SQLAlchemy model voor `hdd.berekeningen`:
- `id` (UUID, PK)
- `project_id` (UUID FK → projecten)
- `ontwerp_id` (UUID FK → ontwerpen — berekening hoort bij specifieke ontwerp versie)
- `berekenings_type` (enum: STERKTE/INTREKKRACHT/SLURRYDRUK)
- `status` (enum: akkoord/waarschuwing/afgekeurd)
- `invoer` (JSONB — alle invoerparameters)
- `resultaat` (JSONB — alle uitvoerwaarden)
- `waarschuwingen` (JSONB — lijst van {bericht, waarde, norm})
- `aangemaakt_op` (datetime)
- `aangemaakt_door_id` (UUID FK → gebruikers)

#### `app/services/calc_engine.py`

Alle formules zijn deterministisch. Geen AI. Elke formule heeft een norm-referentie als commentaar.

**Sterktecontrole (`bereken_sterkte`):**

```python
# Ref: NEN 7245 / ISO 22553 voor PE, EN 10218 voor staal
def bereken_sterkte(
    leiding_materiaal: str,          # PE-100 / staal
    diameter_buiten_mm: float,
    wanddikte_mm: float,
    intrekkracht_N: float,
    min_boogstraal_m: float,
) -> SterkteResultaat:
    """
    A_dwarsdoorsnede = π/4 * (D²_buiten - D²_binnen)   [mm²]
    I_traagheid = π/64 * (D⁴_buiten - D⁴_binnen)       [mm⁴]

    σ_trek = F_intrek / A_dwarsdoorsnede                [MPa]
    σ_buig = E * (D_buiten/2) / R_min                   [MPa]
    σ_totaal = σ_trek + σ_buig                          [MPa]

    Toelaatbaar voor PE-100:  σ_toelaatbaar = 6.3 MPa (MRS/MDF = 1.25)
    Toelaatbaar voor staal:   σ_toelaatbaar = 0.5 * Rp0.2
    PE-100 Rp0.2 = 25 MPa → σ_toelaatbaar = 12.5 MPa
    Staal S235: Rp0.2 = 235 MPa → σ_toelaatbaar = 117.5 MPa

    utilisation_ratio = σ_totaal / σ_toelaatbaar

    Status:
      ratio ≤ 0.8 → AKKOORD
      0.8 < ratio ≤ 1.0 → WAARSCHUWING
      ratio > 1.0 → AFGEKEURD
    """
```

**Intrekkracht (`bereken_intrekkracht`):**

```python
# Ref: ASTM F1962 / HDD design guide
def bereken_intrekkracht(
    tracé_segmenten: list[Segment],  # elk segment heeft lengte_m, hoek_graden, type (recht/boog)
    diameter_buiten_mm: float,
    wanddikte_mm: float,
    leiding_materiaal: str,
    wrijvingsfactor: float = 0.3,    # default voor bentoniet slurry
    slurry_dichtheid_kg_m3: float = 1100.0,
) -> IntrekkrachtResultaat:
    """
    Per segment:
      gewicht_leiding = (A_dwarsdoorsnede * ρ_materiaal) * g * lengte
      gewicht_slurry_binnenin = A_binnenste * ρ_slurry * g * lengte
      opwaartse_kracht = A_buiten * ρ_slurry * g * lengte  (Archimedes)

      N_normaal = gewicht_netto * cos(hoek)  (normaalkracht op bodem)
      F_wrijving = μ * N_normaal * lengte

      Voor bogen: capstan vergelijking
      F_na_boog = F_voor_boog * e^(μ * θ_rad)

    Totale intrekkracht = som van F per segment
    Controle: totaal ≤ max_trekkracht_leiding
    """
```

**Bookvloeistofdruk (`bereken_slurrydruk`):**

```python
# Ref: Guidance on Shallow HDD Risks / Baumert et al.
def bereken_slurrydruk(
    max_diepte_m: float,
    diameter_boorput_mm: float,      # diameter van het geboorde gat (ca. 1.5x leiding diameter)
    diameter_leiding_mm: float,
    slurry_dichtheid_kg_m3: float = 1100.0,
    grond_type: str = "zand",        # zand/klei/veen
) -> SlurrydrukResultaat:
    """
    P_hydrostatisch = ρ_slurry * g * h_max      [Pa]

    Gronddruk parameters per grondtype:
      zand: K0=0.5, φ=30°, γ=18 kN/m³
      klei: K0=0.7, γ=16 kN/m³
      veen: K0=0.8, γ=12 kN/m³

    σ_v = γ_grond * h_max   (verticale grondspanning)
    P_frac = σ_v * K0       (frac-out grens, versimpeld)

    Risico_indicator = P_hydrostatisch / P_frac
      ratio < 0.7 → laag risico
      0.7-0.9 → gemiddeld risico
      > 0.9 → hoog risico (frac-out gevaar)
    """
```

#### Unit tests (`tests/test_calc_engine.py`)

Verifieer alle formules met handmatige referentieberekeningen:

- Sterktecontrole PE-100, D=250mm, t=22.7mm, F=50kN, R=150m
  - A = 16,731 mm², I = ...
  - Verwacht: σ_totaal ≈ X MPa, utilisation_ratio ≈ Y
- Intrekkracht voor recht tracé 200m horizontaal
  - Eenvoudige geval: F = μ * gewicht_netto * lengte
- Slurrydruk max diepte 3m, zand
  - P_hydro vs P_frac berekening

---

### Week 2 — API en Frontend

#### `app/routers/berekeningen.py`

Alle berekeningen zijn synchroon (< 2 seconden):

```
POST /api/v1/projecten/{id}/berekeningen/sterkte
  Auth: Bearer vereist (engineer of beheerder)
  Body: {wrijvingsfactor: float (optioneel)}
  Vereiste: ontwerp aanwezig, leiding specs aanwezig
  Actie:
    1. Haal ontwerp parameters op (min_boogstraal, lengte)
    2. Haal leiding specs op (materiaal, diameter, wanddikte)
    3. Haal intrekkracht resultaat op als al berekend (anders: bereken eerst)
    4. Roep calc_engine.bereken_sterkte() aan
    5. Sla op in hdd.berekeningen
  Response: berekening object met resultaten

POST /api/v1/projecten/{id}/berekeningen/intrekkracht
  Auth: Bearer vereist (engineer of beheerder)
  Body: {wrijvingsfactor: float, slurry_dichtheid: float} (optioneel)
  Response: berekening object

POST /api/v1/projecten/{id}/berekeningen/slurrydruk
  Auth: Bearer vereist (engineer of beheerder)
  Body: {grond_type: string, slurry_dichtheid: float} (optioneel)
  Response: berekening object

GET /api/v1/projecten/{id}/berekeningen
  Response: lijst van alle berekeningen voor dit project (alle versies, alle types)

GET /api/v1/projecten/{id}/berekeningen/{berekening_id}
  Response: volledig berekening object
```

#### `src/pages/Berekeningen.tsx`

Tabblad "Berekeningen" in `ProjectDetail.tsx` (stap 6 van workflow).

Alleen zichtbaar als "Technische berekeningen" is geselecteerd in gewenste output.

**Sterktecontrole sectie:**
- Invoerpanel: wrijvingsfactor (slider, 0.1-0.5, default 0.3)
- "Bereken sterkte" knop
- Resultaten tabel:
  | Parameter | Waarde | Eenheid |
  |---|---|---|
  | Trekkracht | X | kN |
  | Buigspanning | X | MPa |
  | Totale spanning | X | MPa |
  | Toelaatbare spanning | X | MPa |
  | Utilisation ratio | X | - |
- Status badge (groen/oranje/rood)

**Intrekkracht sectie:**
- Invoer: wrijvingsfactor, slurry dichtheid
- Resultaten: F per segment als staafdiagram (recharts BarChart)
- Totale intrekkracht in grote tekst
- Status badge

**Slurrydruk sectie:**
- Invoer: grond type (dropdown: zand/klei/veen)
- Resultaten:
  - Hydrostatische druk vs frac-out grens
  - Gauge-meter voor risico-indicator (groen-geel-rood)
  - Getallen: P_hydro, P_frac, ratio
- Hoog risico → rode waarschuwing: "Frac-out risico hoog. Overweeg andere grondbehandeling of aangepaste slurrydruk."

**Historische berekeningen:**
- Accordion: eerder uitgevoerde berekeningen per type
- Koppeling aan ontwerp versienummer zichtbaar

---

## Data in / Data uit

**In:**
- Ontwerp parameters (lengte, diepte, boogstralen, hoeken)
- Leiding specs (materiaal, diameter, wanddikte)
- Invoer parameters (wrijvingsfactor, grondtype, etc.)

**Uit:**
- Berekening object met status en alle tussenwaarden
- Waarschuwingen als grenswaarden overschreden worden

---

## Modules geraakt

- `app/main.py` — berekeningen router registreren
- `app/services/calc_engine.py` — nieuw bestand
- `ProjectDetail.tsx` — "Berekeningen" tabblad activeren

---

## Acceptatiecriteria

- [ ] Sterktecontrole PE-100 D=250mm t=22.7mm geeft correct resultaat (verifieerbaar met handberekening)
- [ ] Intrekkracht berekening geeft F per segment én totaal
- [ ] Frac-out risico-indicator toont "hoog" als P_hydro > 90% van P_frac
- [ ] Waarschuwing bij utilisation ratio > 0.9
- [ ] Berekening is altijd gekoppeld aan specifieke ontwerp versie
- [ ] Slurry berekening werkt voor zand, klei en veen
- [ ] Alle formules zijn traceerbaar (invoer + formule zichtbaar in resultaat JSON)

---

## User Stories

- Epic 5 Must have: "Als engineer wil ik een sterktecontrole kunnen uitvoeren"
- Epic 5 Must have: "Als engineer wil ik de intrekkracht kunnen berekenen"
- Epic 5 Must have: "Als engineer wil ik de boorvloeistofdruk kunnen berekenen"
- Epic 5 Should have: "Als engineer wil ik een waarschuwing krijgen als een waarde buiten de norm valt"
