# Builder Task — Sprint 8: Document Output

**Sprint:** 8 | **Duur:** 2 weken | **Afhankelijkheden:** Sprint 7 compleet

---

## Doel

PDF tekening en DWG tekening genereren. Werkplan optioneel via AI. Documenten per versie bewaren en downloaden.

---

## Wat te bouwen

### Week 1 — PDF en DWG generator

#### `app/models/output.py`

SQLAlchemy modellen:

**`hdd.output_jobs`:**
- `id` (UUID, PK)
- `project_id` (UUID FK → projecten)
- `status` (enum: wacht/bezig/klaar/fout)
- `typen` (JSONB — array: ["PDF_TEKENING", "DWG", "WERKPLAN", "BEREKENING"])
- `aangemaakt_op` (datetime)
- `voltooid_op` (datetime, nullable)
- `foutmelding` (str, nullable)

**`hdd.output_documenten`:**
- `id` (UUID, PK)
- `project_id` (UUID FK → projecten)
- `job_id` (UUID FK → output_jobs)
- `document_type` (enum: PDF_TEKENING/DWG/WERKPLAN/BEREKENING_PDF)
- `versie_nummer` (int)
- `bestandsnaam` (str)
- `s3_pad` (str)
- `bestandsgrootte_bytes` (int)
- `gegenereerd_op` (datetime)
- `geldig_tot` (datetime — signed URL TTL, default 1 uur)

#### `app/services/doc_generator.py`

**PDF Tekening (`genereer_pdf_tekening(project, ontwerp, klic_objecten, bgt_objecten)`):**

Gebruik WeasyPrint + Jinja2:

Template structuur (`backend/templates/pdf_tekening.html`):
```html
<!-- A3 formaat, landscape -->
<style>
  @page { size: A3 landscape; margin: 10mm; }
  .titelblok { /* rechtsonder, 180x60mm */ }
  .tekening-gebied { /* rest van de pagina */ }
</style>

<!-- Pagina 1: Situatietekening (bovenaanzicht) -->
<!-- Pagina 2: Lengteprofiel (zijaanzicht) -->
```

**Titelblok (via templatevariabelen):**
- Projectnaam
- Opdrachtgever
- Datum (gegenereerd_op)
- Schaal (automatisch: tracélengte / A3 breedte → rond af naar 1:500/1:1000/1:2000)
- Tekenaar (naam huidig ingelogde gebruiker)
- Revisie (versie nummer)
- Tekeningnummer (projectnummer + type)

**Situatietekening (SVG embedded in HTML):**
```python
def genereer_situatie_svg(tracé, klic_objecten, bgt_objecten, bounding_box) -> str:
    """
    - Bereken viewport (bounding box van alle elementen + 10% marge)
    - Schaal coördinaten naar SVG viewbox (RD New meters → SVG units)
    - Teken BGT achtergrond (wegen lichtgrijs, water lichtblauw)
    - Teken KLIC objecten (kleurcodering per type, lijndikte 1pt)
    - Teken tracé (dikke lijn, kleur groen of rood op basis van status)
    - Teken start/eindpunten (symbolen)
    - Maatvoering: pijlen met tekst voor breedte kruising, tracélengte
    - Noordpijl (rechtsboven)
    - Legenda (rechtsonder, boven titelblok)
    - Schaalstaaf
    """
```

**Lengteprofiel SVG:**
```python
def genereer_lengteprofiel_svg(punten, min_diepte, klic_doorsnijtepunten) -> str:
    """
    - X-as: afstand 0 tot tracélengte (meter)
    - Y-as: 0 (maaiveld) tot max_diepte + 1m (meter)
    - Y-as omgekeerd (dieper = lager)
    - Maaiveldlijn (zwarte doorgetrokken lijn)
    - Tracélijn (blauwe doorgetrokken lijn)
    - Minimale dieptegrens (rode stippellijn)
    - Maatvoering: verticale pijl voor max diepte
    - Annotaties: intrede- en uittredepunt
    - Grid lijnen elke 5m verticaal, elke 50m horizontaal
    """
```

**DWG Tekening (`genereer_dwg(project, ontwerp, klic_objecten, bgt_objecten)`):**

```python
import ezdxf

def genereer_dwg(project, ontwerp, klic_objecten, bgt_objecten) -> bytes:
    doc = ezdxf.new('R2018')  # AutoCAD 2018 compatibel
    msp = doc.modelspace()

    # Lagenstructuur (naam, kleur ACI code, lijntype)
    lagen = [
        ('BGT',           253, 'CONTINUOUS'),  # lichtgrijs
        ('KLIC_GAS',      2,   'CONTINUOUS'),  # geel
        ('KLIC_ELEKTR',   1,   'CONTINUOUS'),  # rood
        ('KLIC_WATER',    5,   'CONTINUOUS'),  # blauw
        ('KLIC_TELECOM',  30,  'CONTINUOUS'),  # oranje
        ('KLIC_RIOOL',    34,  'CONTINUOUS'),  # bruin
        ('KLIC_OVERIG',   8,   'CONTINUOUS'),  # grijs
        ('ONTWERP',       3,   'CONTINUOUS'),  # groen, dik
        ('LENGTEPROFIEL', 4,   'CONTINUOUS'),  # cyaan
        ('MAATVOERING',   7,   'CONTINUOUS'),  # wit/zwart
        ('TEKST',         7,   'CONTINUOUS'),
        ('TITELBLOK',     7,   'CONTINUOUS'),
    ]

    for naam, kleur, lijntype in lagen:
        doc.layers.new(naam, dxfattribs={'color': kleur, 'linetype': lijntype})

    # Coördinaten in RD New (meters)
    # BGT objecten → laag BGT
    # KLIC objecten → laag per type
    # Tracé → laag ONTWERP (lijnbreedte 0.5mm)
    # Lengteprofiel → laag LENGTEPROFIEL (aparte modelspace sectie, verschoven 100m naar rechts)
    # Titelblok → laag TITELBLOK (rechtsonder, A3 formaat)
    # Maatvoering → laag MAATVOERING

    # Viewports instellen voor A3 print
    # Return: doc.tobytes()
```

**Werkplan (`genereer_werkplan(project, ontwerp)`):**

Template `backend/templates/werkplan.html` met secties:
1. Projectbeschrijving (naam, opdrachtgever, locatie)
2. Tracébeschrijving (start/eindpunt, lengte, diepte)
3. Te kruisen object (naam, type, beheerder, eisen)
4. Nieuwe leiding (materiaal, diameter, lengte)
5. Werkmethode (standaard HDD beschrijving)
6. Veiligheidsmaatregelen (standaard tekst)
7. Materiaallijst (leidinglengte, boorvloeistof, etc.)

Data gevuld vanuit projectobject. Geen AI voor Must have — AI is Could have in deze sprint.

**Berekening PDF:**
Template per berekeningstype met:
- Invoerparameters tabel
- Formules (LaTeX-achtige notatie als tekst)
- Resultaten tabel
- Normreferentie

#### Tests (`tests/test_doc_generator.py`)

- PDF generatie voor testproject → bytes output, PDF valide (check met PyPDF2)
- PDF bevat titelblok (check tekst in PDF)
- DWG generatie → bytes output, ezdxf kan het terug inlezen
- DWG heeft alle vereiste lagen
- Werkplan PDF bevat alle secties

---

### Week 2 — Async jobs en Frontend

#### `app/workers/output_worker.py`

```python
async def genereer_output_worker(ctx, project_id: str, job_id: str, typen: list[str]):
    """
    Per type in typen:
      1. Roep juiste generator aan
      2. Upload bytes naar S3 (pad: projecten/{project_id}/output/{type}_{versie}.pdf/.dwg)
      3. Sla output_document record aan (versie = max(vorige) + 1)
      4. Update job status na elk bestand
    max_tries = 2
    timeout = 300
    """

async def genereer_ai_werkplan_worker(ctx, project_id: str):
    """
    1. Haal projectdata op
    2. Assembleer prompt (zie prompt template hieronder)
    3. Roep LLM API aan (OpenAI of Ollama afhankelijk van config)
    4. Ontvang markdown tekst
    5. Converteer naar PDF via WeasyPrint
    6. Upload naar S3
    7. Sla output_document op
    timeout = 120
    """
```

**AI werkplan prompt template:**
```
Je bent een HDD engineering expert. Genereer een professioneel werkplan voor de volgende boring:

Project: {naam} voor opdrachtgever {opdrachtgever}
Locatie: {locatie_omschrijving}
Te kruisen object: {object_naam} ({object_type}), beheerder: {beheerder}
Nieuwe leiding: {diameter}mm {materiaal}, wanddikte {wanddikte}mm
Tracé: {lengte}m, maximale diepte {diepte}m
Eisenprofiel: {eisenprofiel_naam}

Genereer een werkplan met de volgende secties (in het Nederlands):
1. Projectbeschrijving
2. Beschrijving van de boring
3. Omschrijving kruising
4. Toepasselijke eisen en normen
5. Veiligheidsmaatregelen
6. Materiaalstaat

Wees specifiek en gebruik de gegeven projectdata. Schrijf professioneel en beknopt.
```

#### `app/routers/output.py`

```
POST /api/v1/projecten/{id}/output/genereer
  Auth: Bearer vereist
  Body: {"typen": ["PDF_TEKENING", "DWG", "WERKPLAN", "BEREKENING_PDF"]}
  Vereiste: ontwerp geaccordeerd
  Response: {"job_id": str}
  Actie: ARQ worker starten

GET /api/v1/projecten/{id}/output/status/{job_id}
  Response: {"status": str, "voltooide_typen": [...], "fout": str}

GET /api/v1/projecten/{id}/output/documenten
  Response: [{id, type, versie, bestandsnaam, gegenereerd_op, download_url}]
  Note: download_url is een pre-signed S3 URL, geldig 1 uur

GET /api/v1/projecten/{id}/output/documenten/{document_id}/download
  Response: redirect naar pre-signed S3 URL

POST /api/v1/projecten/{id}/output/ai-werkplan
  Auth: Bearer vereist
  Response: {"job_id": str}
  Actie: AI werkplan worker starten (los van reguliere output job)
```

#### `src/pages/Output.tsx`

Tabblad "Output" in `ProjectDetail.tsx` (stap 7 van workflow):

**Sectie 1 — Output genereren:**
- Checkboxes voor output typen:
  - PDF Tekening (altijd aangevinkt als geselecteerd in projectinstellingen)
  - DWG Tekening (idem)
  - Werkplan (indien geselecteerd)
  - Berekening PDF (indien berekeningen zijn uitgevoerd)
- "Genereer output" knop
- Voortgangsbar: X van Y bestanden gereed
- Succesmelding na afronding

**Sectie 2 — Beschikbare documenten:**
- Lijst per type met versienummer en datum
- "Download" knop per document → GET download endpoint → redirect naar S3 URL
- Versiebeheer: alle versies zichtbaar, nieuwste bovenaan

**Sectie 3 — AI Werkplan (optioneel):**
- "Genereer AI werkplan" knop
- Wachttijd indicator (< 60 sec)
- Resultaat als downloadbaar document
- Disclaimer: "Door AI gegenereerd — controleer voor gebruik"

---

## Data in / Data uit

**In:** project, ontwerp, KLIC objecten, BGT objecten, berekeningen
**Uit:** PDF bytes (< 5MB), DWG bytes, werkplan PDF, berekening PDF — alle op S3

---

## Modules geraakt

- `app/services/geo_service.py` — GeoJSON naar SVG coördinaten transformatie
- `app/workers/settings.py` — output workers toevoegen
- `app/config.py` — `OPENAI_API_KEY` of `OLLAMA_URL` toevoegen
- `ProjectDetail.tsx` — "Output" tabblad activeren

---

## Acceptatiecriteria

- [ ] PDF bevat titelblok (naam, datum, schaal, tekenaar), situatietekening en lengteprofiel
- [ ] DWG opent in AutoCAD (of LibreCAD) met correcte lagenstructuur (alle 12 lagen aanwezig)
- [ ] Bestandsgrootte PDF < 5 MB voor standaard project (tracé 200m)
- [ ] Download start binnen 3 seconden na klikken
- [ ] Werkplan PDF bevat alle 7 secties gevuld met projectdata
- [ ] AI werkplan genereert Nederlandse tekst in < 60 seconden
- [ ] Bij regenereren: versienummer verhoogd, oud document blijft bewaard
- [ ] S3 URLs zijn pre-signed (geen publieke buckets)

---

## User Stories

- Epic 6 Must have: "Als engineer wil ik een PDF tekening kunnen genereren"
- Epic 6 Must have: "Als engineer wil ik een DWG tekening kunnen genereren"
- Epic 6 Must have: "Als engineer wil ik de gewenste outputbestanden per project kunnen kiezen"
- Epic 6 Should have: "Als engineer wil ik een automatisch samengesteld werkplan kunnen genereren"
- Epic 6 Should have: "Als engineer wil ik gegenereerde documenten per versie kunnen bewaren"
- Epic 6 Could have: "Als engineer wil ik het werkplan automatisch laten aanvullen door AI"
