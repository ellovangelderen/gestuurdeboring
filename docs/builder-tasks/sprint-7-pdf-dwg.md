# Builder Task — Sprint 7: PDF & DWG Output

**Sprint:** 7 | **Duur:** 1.5 week | **Afhankelijkheden:** Sprint 6 compleet

---

## Doel

PDF tekening en DWG tekening genereren vanuit het ontwerp. Engineer kan bestanden downloaden.

> **Werkplan template hoort in iteratie 2.**
> **AI werkplanteksten hoort in iteratie 3.**
> **Berekening PDF hoort in iteratie 2/3.**
> **Geen async queue** — generatie is synchroon. PDF < 3 seconden, DWG < 5 seconden voor standaard project.

---

## Wat te bouwen

### Week 1 — Generators

#### `app/documents/pdf_generator.py`

```python
def genereer_pdf_tekening(project, ontwerp, klic_objecten) -> bytes:
    """
    WeasyPrint + Jinja2 HTML template → PDF bytes

    Template: backend/templates/pdf_tekening.html
    Formaat: A3 landscape

    Pagina 1 — Situatietekening (bovenaanzicht):
      - Titelblok rechtsonder (zie hieronder)
      - SVG situatietekening (zie genereer_situatie_svg)
      - Legenda linksboven
      - Noordpijl

    Pagina 2 — Lengteprofiel (zijaanzicht):
      - Titelblok rechtsonder
      - SVG lengteprofiel (zie genereer_lengteprofiel_svg)
      - Maatvoering: boorlengte, max diepte

    Titelblok bevat:
      - Projectnaam
      - Opdrachtgever
      - Datum (vandaag)
      - Schaal (automatisch: tracélengte / A3 breedte → afgerond op 1:500/1:1000/1:2000/1:5000)
      - Tekenaar (naam ingelogde gebruiker — meegeven als parameter)
      - Revisie (versie nummer uit output_document)
      - Tekeningnummer (project.id[:8].upper())
    """
```

```python
def genereer_situatie_svg(tracé_wgs84, klic_objecten, bounding_box) -> str:
    """
    SVG string van bovenaanzicht.

    - Viewport = bounding_box + 10% marge
    - Schaal coördinaten: WGS84 → SVG units (lineaire benadering, precies genoeg voor kaartschalen)
    - BGT ontbreekt in iteratie 1 — alleen OSM tiles als achtergrond (geen tiles in SVG,
      gebruik lichte achtergrondkleur)
    - KLIC objecten: lijnkleur per type (gas=geel, elektra=rood, water=blauw, telecom=oranje, riool=bruin)
    - Tracé: groene lijn, dikte 2px
    - Start/eindpunt: gevulde cirkels met labels "Start" en "Eind"
    - Conflictmarkers: ⚠ icoon op conflictpunt
    - Maatvoering: pijl + tekst voor tracébreedte bij kruisingsobject
    """
```

```python
def genereer_lengteprofiel_svg(lengteprofiel_punten, min_diepte_m, boorlengte_m) -> str:
    """
    SVG string van lengteprofiel.

    - X-as: 0 tot boorlengte_m (meter), tick elke 50m
    - Y-as: 0 (maaiveld) tot max_diepte + 1m, Y-as omgekeerd
    - Maaiveldlijn: zwarte doorgetrokken lijn op y=0
    - Tracélijn: blauwe lijn door puntenreeks
    - Minimale dieptegrens: rode stippellijn op y=min_diepte_m
    - Labels: "Maaiveld", "Min. diepte: {min_diepte_m}m"
    - Maatpijl: verticale pijl voor max diepte
    - Grid: lichte grijze lijnen elke 50m horizontaal, elke 1m verticaal
    """
```

#### `app/documents/dwg_generator.py`

```python
import ezdxf

def genereer_dwg(project, ontwerp, klic_objecten) -> bytes:
    """
    ezdxf → DWG bytes (AutoCAD R2018 compatibel)

    Coördinaten: RD New (meters) — zodat 1:1000 schaal klopt in AutoCAD

    Lagenstructuur (naam, ACI kleur, lijntype):
      HDD-BORING       3  CONTINUOUS   # groen — het boortracé
      HDD-KLIC-GAS     2  CONTINUOUS   # geel
      HDD-KLIC-ELEKTRA 1  CONTINUOUS   # rood
      HDD-KLIC-WATER   5  CONTINUOUS   # blauw
      HDD-KLIC-TELECOM 30 CONTINUOUS   # oranje
      HDD-KLIC-RIOOL   34 CONTINUOUS   # bruin
      HDD-KLIC-OVERIG  8  CONTINUOUS   # grijs
      HDD-OBJECT       4  CONTINUOUS   # cyaan — te kruisen object
      HDD-PROFIEL      6  CONTINUOUS   # magenta — lengteprofiel sectie
      HDD-MAATVOERING  7  CONTINUOUS   # zwart/wit
      HDD-TEKST        7  CONTINUOUS
      HDD-TITELBLOK    7  CONTINUOUS

    Inhoud modelspace:
      - KLIC objecten als LWPOLYLINE per type → juiste laag
      - Boortracé als LWPOLYLINE → laag HDD-BORING
      - Te kruisen object breedte als lijn → laag HDD-OBJECT
      - Lengteprofiel als LWPOLYLINE (Y = diepte, X = afstand) → laag HDD-PROFIEL
        Geplaatst 100m rechts van situatietekening om te scheiden
      - Maatvoering: DIMENSION entiteiten
      - Titelblok: TEXT entiteiten rechtsonder

    Return: doc.tobytes()
    """
```

#### Tests (`tests/test_doc_generator.py`)

- PDF generatie → bytes output, is geldig PDF (check magic bytes `%PDF`)
- PDF > 10KB (bevat inhoud)
- DWG generatie → bytes output, ezdxf kan het terug inlezen
- DWG bevat alle 12 lagen
- DWG heeft LWPOLYLINE entiteiten op laag HDD-BORING

---

### Week 2 — API + Frontend

#### Bestandsopslag op Railway volume

```python
# config: STORAGE_PATH = "/storage" (Railway volume)
# Pad: {STORAGE_PATH}/projecten/{project_id}/output/{type}_{versie}.{ext}
# type: "pdf_tekening" of "dwg_tekening"

def sla_output_op(project_id, type, inhoud: bytes, extensie: str) -> str:
    """Sla bestand op op volume, return relatief pad"""
```

#### `app/api/routers/output.py`

```
POST /api/v1/projecten/{id}/output/genereer
  Auth: Bearer vereist
  Body: {"typen": ["pdf_tekening", "dwg_tekening"]}
  Vereiste: ontwerp aanwezig (status niet 'concept')
  Actie (synchroon):
    1. Genereer gevraagde bestanden
    2. Sla op op Railway volume
    3. Sla output_document records op
  Response: [{type, versie, bestandsnaam, gegenereerd_op}]
  Fout: 422 als ontwerp ontbreekt

GET /api/v1/projecten/{id}/output/documenten
  Response: [{id, type, versie, bestandsnaam, gegenereerd_op}]

GET /api/v1/projecten/{id}/output/documenten/{document_id}/download
  Response: FileResponse (streaming download)
  Headers: Content-Disposition: attachment; filename="{bestandsnaam}"
```

#### `src/pages/Output.tsx`

Tabblad "Output" in `ProjectDetail.tsx`:

**Genereer sectie:**
- Checkboxes: PDF Tekening, DWG Tekening
- "Genereer" knop → loading indicator → succesmelding
- Foutmelding als ontwerp ontbreekt: "Genereer eerst een ontwerp"

**Documenten sectie:**
- Lijst van gegenereerde bestanden per type
- Meest recent bovenaan
- "Download" knop per document → GET download endpoint → bestand downloaden
- Versienummer en datum zichtbaar

---

## Data in / Data uit

**In:** project + ontwerp + KLIC objecten (uit database)
**Uit:** PDF bytes + DWG bytes op Railway volume, download via API

---

## Modules geraakt

- `app/geo/service.py` — WKT → SVG coördinatenconversie
- `app/main.py` — output router registreren
- `ProjectDetail.tsx` — "Output" tabblad activeren

---

## Acceptatiecriteria

- [ ] PDF bevat titelblok (naam, datum, schaal, tekenaar), situatietekening en lengteprofiel
- [ ] DWG opent in AutoCAD/LibreCAD met correcte lagenstructuur (12 lagen aanwezig)
- [ ] DWG bevat boortracé op laag HDD-BORING en KLIC objecten op juiste lagen
- [ ] PDF generatie < 5 seconden
- [ ] DWG generatie < 10 seconden
- [ ] Download werkt direct (geen pre-signed URL nodig — Railway volume is server-lokaal)
- [ ] Bij opnieuw genereren: versienummer omhoog, oud document blijft beschikbaar

---

## User Stories

- Epic 6 Must have: "Als engineer wil ik een PDF tekening kunnen genereren"
- Epic 6 Must have: "Als engineer wil ik een DWG tekening kunnen genereren"
- Epic 6 Must have: "Als engineer wil ik de gewenste outputbestanden per project kiezen"
