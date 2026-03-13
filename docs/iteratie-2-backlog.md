# Iteratie 2 — Backlog

**Status:** Gepland — nog niet gebouwd
**Afhankelijkheid:** Iteratie 1 compleet en in gebruik

---

## Wat iteratie 2 toevoegt

Iteratie 1 levert de werkende kern. Iteratie 2 voegt de functies toe die engineeringteams na de eerste maanden van gebruik als meest waardevol identificeren.

---

## Features

### BGT API integratie

**Wat:** Topografische achtergrond ophalen via PDOK API voor het projectgebied (wegen, water, spoor, gebouwen).

**Waarom niet in iteratie 1:** Engineer gebruikt OSM als achtergrond — voldoende voor bovenaanzicht. BGT toevoegen is waardevolle verrijking maar geen blocker.

**Technisch:**
- ARQ async worker `haal_bgt_op` — PDOK WFS API aanroepen per collectie (wegdeel, waterdeel, spoor, pand)
- Bounding box uit project locatie als query-parameter
- BGT objecten opslaan in `bgt_object` tabel (PostGIS geometry)
- Redis toevoegen aan stack (job queue + status polling)
- Frontend: BGT kaartlaag met type-kleuring (wegen grijs, water blauw, etc.)

---

### Werkplan template

**Wat:** Automatisch samengesteld werkplan als PDF, gevuld vanuit projectdata.

**Waarom niet in iteratie 1:** Engineer schrijft werkplan nu handmatig op basis van de parameters die het systeem levert. Werkplan template is een tijdsbesparing, geen blocker.

**Technisch:**
- WeasyPrint template `werkplan.html` met vaste secties:
  1. Projectbeschrijving
  2. Tracébeschrijving
  3. Kruisingsbeschrijving
  4. Toepasselijke eisen
  5. Veiligheidsmaatregelen
  6. Materiaalstaat
- Alle velden gevuld vanuit `Project` + `Ontwerp` + `TeKruisenObject`
- Downloadbaar als PDF via bestaand output endpoint
- Checkbox "Werkplan" toevoegen aan output selectie

---

### Basis berekeningen: intrekkracht en buigstraalcontrole

**Wat:** Indicatieve berekening van de intrekkracht (pullback force) en controle op de buigstraal.

**Waarom niet in iteratie 1:** Engineer rekent nu buiten het systeem. Voor iteratie 2 worden de twee meest gevraagde berekeningen toegevoegd.

**Technisch (buigstraalcontrole):**
```
σ_buig = E * (D_buiten/2) / R_min
Toelaatbaar PE-100: 6.3 MPa
```

**Technisch (intrekkracht):**
```
F_intrek = Σ per segment:
  F_wrijving = μ * N_normaal
  F_boog = F_vorige * (e^(μ*θ) - 1) per boog
```

- Synchroon uitvoeren (< 2 seconden)
- Resultaten bewaren in `berekening` tabel (iteratie 1 tabel aanmaken als placeholder bij DB migratie iteratie 2)
- Waarschuwing als utilisation ratio > 0.9

---

### Versiebeheer ontwerp

**Wat:** Historische ontwerpen bewaren. Engineer kan oudere versies terugkijken en vergelijken.

**Waarom niet in iteratie 1:** In iteratie 1 is er één ontwerp per project dat overschreven wordt. Werkt prima voor een klein team.

**Technisch:**
- Kolom `versie_nummer` en `is_huidig` toevoegen aan `ontwerp` tabel
- Bij herberekening: nieuwe versie aanmaken, vorige `is_huidig=FALSE`
- API: `GET /ontwerp/versies` + `GET /ontwerp/versies/{nr}`
- Frontend: versie-dropdown in ontwerp tabblad

---

### Gebruikersrollen

**Wat:** Verschillende rollen met verschillende rechten: werkvoorbereider (intake), engineer (ontwerp + accorderen), beheerder (gebruikersbeheer + eisenprofielen).

**Waarom niet in iteratie 1:** Klein team van 2–5 engineers — iedereen doet alles. Rollen zijn overhead zonder waarde in iteratie 1.

**Technisch:**
- Kolom `rol` toevoegen aan `gebruiker` tabel (werkvoorbereider/engineer/beheerder)
- FastAPI dependency `require_rol(*rollen)` implementeren
- Accordeerfunctionaliteit: alleen engineer/beheerder
- Gebruikersbeheer UI: alleen beheerder
- Eisenprofielen beheren: alleen beheerder

---

## Wat iteratie 2 NIET bevat

- AI werkplanteksten → iteratie 3
- Eisenprofiel beheerscherm → iteratie 3
- Sterkte- en slurrydrukberekening → iteratie 3
- Meerdere workspaces actief → iteratie 3
- Geautomatiseerde KLIC-aanvraag → nooit (Won't have)
- 3D visualisatie → nooit (Won't have)
- Calculatie/offerte → nooit (expliciet buiten scope alle iteraties)
