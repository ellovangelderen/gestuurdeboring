# CLAUDE.md — HDD Ontwerp Platform
**LeanAI Platform · Architect Agent**
Versie: 6.0 | 2026-03-17

---

## 1. Jouw rol

Je bent de **Architect Agent** voor het HDD Ontwerp Platform, gebouwd door Inodus voor Martien Luijben (GestuurdeBoringTekening.nl). Hij ontwerpt gestuurde boringen (HDD) voor kabels en leidingen in opdracht van netbeheerders (Liander, Stedin, e.a.).

```
Model Agent → Architect Agent (jij) → Builder Agent → Release Agent
```

**Jouw verantwoordelijkheden:**
- Technisch ontwerp bewaken en documenteren
- Builder-taken schrijven die geïsoleerd testbaar zijn
- Bewaken dat de walking skeleton klein en werkend blijft
- Backlog prioriteit verdedigen op basis van klantwaarde

**Nooit jouw verantwoordelijkheid:**
- Productiecode schrijven (Builder Agent)
- Scope uitbreiden zonder Ello's goedkeuring

**Type C (losse calculatie / Sigma berekeningen) is een geldig product, niet buiten scope.**

---

## 2. Aanpak: walking skeleton + backlog

**Geen iteraties of fasen.** Eén aanpak:

1. **Walking Skeleton** — eerste oplevering. Volledig werkend end-to-end systeem. Complexe stappen op override (handmatig invullen). Martien werkt er direct mee.
2. **Backlog** — geprioriteerde features. Eén voor één bouwen, testen, uitrollen. Volgorde herijken met Martien na elke oplevering.

**Override principe:** elke complexe stap heeft een handmatige fallback die altijd blijft werken. Automatisering vervangt de override, verwijdert hem nooit. Override-waarden worden gemarkeerd en opgeslagen met datum.

### Walking Skeleton scope

| Module | Inhoud | Override |
|---|---|---|
| Project | naam, opdrachtgever, ordernummer, leidingparameters | — |
| Locatie | RDNAP A/B + tussenpunten + Rh per segment, Leaflet oriëntatie | kaart = oriëntatie |
| KLIC | ZIP uploaden → placeholder leidingen tonen | geen echte parsing |
| Maaiveld | MVin / MVuit handmatig invoeren | AHN5 API later |
| Grondtype | dropdown Zand/Klei/Veen | GEF parser later |
| Intrekkracht | handmatig invoeren uit Sigma | NEN 3651 berekening later |
| DXF output | exacte laagnamen HDD28, ezdxf | — |
| PDF output | situatie + profiel + doorsnede + titelblok | — |
| Drive sync | input ophalen, output wegschrijven | handmatig upload fallback |
| Auth | HTTPBasic, 2 gebruikers in `.env`, test-user alleen in development | — |

### Backlog — Status per 18 maart 2026

| # | Feature | Status | Tests |
|---|---|---|---|
| 0 | Datamodel refactor: Order → Boring[] | **DONE** | 57 |
| 1 | Werkplan generator (Claude API) | **DONE** | — |
| 2 | Cockpit UI — orderoverzicht | **DONE** | 67 |
| 3 | KLIC IMKL 2.0 parser | **DONE** | 82 |
| 3b | EV-zone DXF rendering | **DONE** | 87 |
| 4 | Statusmail concepten (kopieerbaar) | **DONE** | 136 |
| 5 | GWSW riool BOB + gemeente-mail | **DONE** | 164 |
| 6 | Sleufloze leidingen detectie | **DONE** | 171 |
| 7 | Conflictcheck K&L 3D | **DONE** | 146 |
| 8 | Boogzinker profiel (type Z) | **DONE** | 126 |
| 9 | Boorprofiel geometrie ARCs | **DONE** | 99 |
| 10 | AHN5 maaiveld + PDOK + waterschap | **DONE** | 116 |
| 11 | Topotijdreis historische kaarten | **DONE** | 154 |
| 12 | Tracévarianten vergelijken | **DONE** | 178 |
| 13 | SnelStart concept-factuur | **DONE** | 183 |
| 14 | Vergunningscheck (link-out portalen) | **DONE** | 190 |
| 15 | Dinoloket sonderingen (link-out) | **DONE** | 199 |
| 16 | GEF/CPT parser | OPTIONEEL | — |
| 17 | NEN 3651 berekeningen | OPTIONEEL | — |
| 18 | As-Built revisietekeningen | **DONE** | 199 |

### Volgende backlog — Excel-analyse (docs/Backlog/BACKLOG_EXCEL_ANALYSE.md)

| # | Item | Type |
|---|---|---|
| B1 | Rv per segment apart | BESLISSING Martien |
| B2 | Bundelfactor Dg berekening | BESLISSING Martien |
| B3 | Ruimfactoren per boringtype | BESLISSING Martien |
| B4 | Boormachine selectie | BESLISSING Martien |
| B5 | Type W als boringtype | BESLISSING Martien |
| B6 | Standaard K&L dieptes fallback | BESLISSING Martien |
| V1-V6 | Klantcodes, EV handmatig, PDOK URLs | VERRIJKING |
| T1-T5 | CSV export, AutoCAD script, horizontale bocht | TOEKOMSTIG |

Noten:
- Item 0: MOET EERST. Alles hangt af van het nieuwe datamodel.
- Item 1: Hoogste ROI volgens Martien. Kan standalone gebouwd worden, onafhankelijk van datamodel refactor.
- Item 2: Vervangt de lineaire workflow. "Cockpit" = startpagina met alle orders, één klik naar alles.
- Item 3b: Wettelijk kritisch, direct na item 3 bouwen.
- Item 4: Wekelijks automatisch overzicht per opdrachtgever van openstaande akkoorden.
- Item 8: Boogzinker heeft fundamenteel ander profiel dan B/N (1 boog i.p.v. 5 segmenten).
- Item 13: SnelStart REST API koppeling voor facturatie.

---

## 3. LeanAI principes

- **Lean first.** Skeleton is zo klein mogelijk terwijl het end-to-end werkt.
- **Modulaire monoliet.** Eén FastAPI backend, intern gescheiden per domein.
- **Deterministisch.** Berekeningen zijn expliciete Python code, nooit AI-prompts.
- **Workspace-ready dag één.** `workspace_id` op alle entiteiten. Eén workspace, onzichtbaar.
- **Override altijd beschikbaar.** Geen automatisering zonder handmatige fallback.
- **Testcases per module.** Geïsoleerd, draaien bij elke commit. Testdata = echte projecten.
- **First Time Right.** Liever langzamer en correct.
- **Wij zijn de bron.** Platform is het systeem of record. GSheets verdwijnt na migratie. Export en backup altijd beschikbaar.

---

## 4. Stack

| Laag | Keuze | Reden |
|---|---|---|
| Frontend | HTMX + Jinja2 + Alpine.js | Geen build tool, server-side HTML, formulieren native |
| Kaart | Leaflet + OpenStreetMap + PDOK lagen | Werkt standalone, geen React nodig |
| Coördinaten | pyproj EPSG:28992 (RD↔WGS84) | Standaard, één library |
| Backend | Python FastAPI | Snel, goed gedocumenteerd |
| Database | SQLite + SQLAlchemy | 2 gebruikers, 100 projecten/jaar — geen server nodig |
| File opslag | Railway volumes | Bestanden per project als gewone map |
| PDF | WeasyPrint + Jinja2 | Template-gebaseerd, al in gebruik |
| DXF | ezdxf | Enige mature Python DXF library |
| Drive sync | Downloadknop (skeleton) → Drive API (backlog) | Eerst simpel |
| AI tekst | Anthropic Claude API (backlog 1) | Werkplan generator |
| Auth | FastAPI HTTPBasic + `.env` | 2 vaste gebruikers, geen token overhead |
| Hosting | Railway — hdd.inodus.nl | Managed, autodeploy bij git push |
| CI/CD | Railway autodeploy (git push → live) | Geen Docker, geen pipeline file |
| SnelStart | Concept-factuur (kopieerbaar) | Martien voert zelf in via webportal |
| SVG→PNG | cairosvg | SVG rendering voor PDF (WeasyPrint ondersteunt geen inline SVG) |

---

## 5. Projectstructuur

```
hdd-platform/
├── app/
│   ├── core/               # workspace middleware, auth, config, database
│   ├── project/            # project CRUD (legacy)
│   ├── order/              # order CRUD + cockpit + alle boring routes
│   │   ├── router.py       # ~1700 regels: cockpit, trace, brondata, AHN5,
│   │   │                   #   conflictcheck, topotijdreis, GWSW, sleufloze,
│   │   │                   #   varianten, asbuilt, vergunning, sonderingen,
│   │   │                   #   factuur, statusmail, DXF/PDF download
│   │   ├── models.py       # Order, Boring, TracePunt, MaaiveldOverride,
│   │   │                   #   KLICUpload, KLICLeiding, AsBuiltPunt, etc.
│   │   └── klantcodes.py   # 16+ klantcodes + contactpersonen + logo's
│   ├── geo/                # geospatiale services
│   │   ├── ahn5.py         # AHN5 PDOK WCS maaiveld ophalen
│   │   ├── coords.py       # RD ↔ WGS84 (pyproj)
│   │   ├── profiel.py      # 5-segment + boogzinker geometrie
│   │   ├── conflictcheck.py # 3D afstand boortracé vs K&L
│   │   ├── klic_parser.py  # IMKL 2.0 ZIP/GML parser
│   │   ├── gwsw.py         # PDOK GWSW riool BOB API
│   │   ├── waterschap.py   # waterschap detectie via PDOK WMS
│   │   └── pdok_urls.py    # PDOK URL generatie
│   ├── documents/          # PDF (WeasyPrint) + DXF (ezdxf) generatie
│   ├── rules/              # eisenprofielen seed
│   └── templates/          # Jinja2 HTML templates
│       ├── order/          # 15+ pagina's (cockpit, trace, brondata, etc.)
│       └── documents/      # tekening.html (A3 4-zone PDF layout)
├── static/logos/           # Logo3D.jpg, gbt_logo.svg, Mook BV.jpg
├── tests/                  # 199 tests, 15+ testbestanden
├── docs/                   # architectuur, backlog, testhandleiding, mails
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── map/        # Leaflet kaart
│       │   ├── profile/    # Lengteprofiel NAP
│       │   └── drawing/    # Tekening preview
│       └── pages/
├── docs/
│   ├── input_data_14maart/ # Alle testdata van Martien (zie sectie 9)
│   └── backlog/            # Builder-taakinstructies per backlog item
├── tests/                  # Geïsoleerde testcases per module
├── CLAUDE.md               # Dit bestand
└── README.md
```

---

## 6. Datamodel (kern)

```python
Workspace      id · naam · created_at

Order          id · workspace_id · ordernummer · locatie · klantcode
               opdrachtgever · status · ontvangen_op · deadline
               geleverd_op · vergunning(P/W/R/-) · prio(bool) · notitie
               tekenaar(default="martien") · google_maps_url · pdok_url
               waterkering_url · oppervlaktewater_url · peil_url

Boring         id · order_id · volgnummer(int) · type(B/N/Z/C) · naam
               # Leidingparameters (alleen B/N/Z)
               materiaal · SDR · De_mm · dn_mm · medium · Db_mm · Dp_mm · Dg_mm
               # Hoeken (B/N)
               intreehoek_gr · uittreehoek_gr
               # Boogzinker params (Z)
               booghoek_gr · stand
               status · aangemaakt_door · aangemaakt_op

KLICUpload     id · order_id · meldingnummer · versie(int) · type(orientatie/graaf/hermelding)
               bestandsnaam · bestandspad · upload_datum · verwerkt
               aantal_leidingen · aantal_beheerders · verwerk_fout · verwerkt_op

BoringKLIC     boring_id · klic_upload_id  # many-to-many koppeltabel
               # Engineer kiest welke KLIC-versie per boring

KLICLeiding    id · klic_upload_id · beheerder · leidingtype · thema · dxf_laag
               geometrie_wkt · diepte_m · diepte_override_m
               sleufloze_techniek · bron_pdf_url · imkl_feature_id
               ev_verplicht · ev_contactgegevens

TracePunt      id · boring_id · volgorde · type(intree/tussenpunt/uittree)
               RD_x · RD_y · Rh_m · label

MaaiveldOverride  id · boring_id · MVin_NAP_m · MVuit_NAP_m · bron
               MVin_bron · MVuit_bron · MVin_ahn5_m · MVuit_ahn5_m

Doorsnede      id · boring_id · volgorde · afstand_m · NAP_m · grondtype
               GWS_m · phi_graden · E_modulus · override_vlag

Berekening     id · boring_id · Ttot_N · bron · override_datum

BoorProfiel    id · boring_id · type(5segment/boogzinker)
               L_totaal_m · L_hor_m · geometrie_wkt
               sensorpunten_json

Document       id · boring_id · type(pdf/dxf/werkplan) · versie · drive_url · created_at

EVPartij       id · order_id · naam · type(EV1-EV5)
EmailContact   id · order_id · naam · type(Email1-Email6)

OrderStatus    enum: order_received / in_progress / delivered / waiting_for_approval / done / cancelled
BoringType     enum: B (gestuurde boring) / N (nano) / Z (boogzinker) / C (calculatie)
Vergunning     enum: P (provincie) / W (waterschap) / R (RWS) / - (geen)
```

Regels:
- Bestandsnamen: `{ordernummer}-{volgnummer:02d}-rev.{n}.dxf/pdf`
- KLIC op order-niveau, boring verwijst naar specifieke KLIC-versie via BoringKLIC
- Type C boring: alleen Berekening, geen TracePunten/DXF/PDF
- EV-partijen en EmailContacten als aparte tabellen (max 5 resp. 6)

---

## 7. DXF laagnamen (gevalideerd HDD28 Velsen-Noord)

Exacte laagnamen uit `3D26V810-28 HDD28.dxf` (114.046 regels, 218 lagen):

```
Laagnaam              ACI  Lijntype          Entiteiten
BOORLIJN              1    Continuous        LWPolyline + ARCs + LINEs + POINTs
BOORGAT               5    DASHDOT           2× CIRCLE (r=boorgat, r=buis)
MAAIVELD              122  Continuous        LWPolyline (695 punten)
MAATVOERING           170  Continuous        DIMENSION, TEXT, MTEXT
MAATVOERING-GRIJS     251  Continuous        TEXT afstandslabels
ATTRIBUTEN            252  Continuous        INSERT blokken + sensorpunt TEXT labels
TITELBLOK_TEKST       7    Continuous        tekst titelblok
LAAGSPANNING          190  KL-LS-N           HATCH
MIDDENSPANNING        130  KL-MS-N           HATCH
HOOGSPANNING          10   KL-HS-N           HATCH
LD-GAS                50   KL-GAS-LD-N       HATCH
WATERLEIDING          170  KL-WATER-N        HATCH
RIOOL-VRIJVERVAL      210  RI-OVERIG         HATCH
PERSRIOOL             210  RI-PERS           HATCH
KADASTER              150  KG-PERCEEL        lijnen
WEGDEK                252  Continuous        TEXT + lijn
```

NLCS lijntype-definities (hardcoden in ezdxf output):
```python
NLCS_LINETYPES = {
    "KL-LS-N":     "ELECTRA LAAGSPANNING VOLGENS NLCS",
    "KL-MS-N":     "ELECTRA MIDDENSPANNING VOLGENS NLCS",
    "KL-HS-N":     "ELECTRA HOOGSPANNING VOLGENS NLCS",
    "KL-GAS-LD-N": "GAS LAGEDRUK VOLGENS NLCS",
    "KL-WATER-N":  "WATERLEIDING VOLGENS NLCS",
    "RI-OVERIG":   "OVERIGE LEIDINGEN",
    "RI-PERS":     "PERSLEIDING",
    "KG-PERCEEL":  "KADASTRALE PERCEELGRENS",
}
```

INSERT blokken op laag ATTRIBUTEN:
- `VermeerD40` — boormachine
- `Aboorgat3x1` — intrede boorgat symbool
- `Bboorgat3x1` — uittrede boorgat symbool
- `1xBuis` — buis doorsnede
- `VRACHTWAGEN` — vrachtwagen

Sensorpunt labels als TEXT op ATTRIBUTEN: `Tv1 Tv2 Th1 Th2 Th3 Tv3 Th4 Tv4`

---

## 8. PDF tekening — verplichte elementen

Bevestigd door Martien:

```
Bovenaanzicht      1:4000, Noorden boven
Situatietekening   1:250, NLCS-kleuren, tracé A→B zichtbaar
Lengteprofiel      1:250 op NAP, maatvoering bij elk sensorpunt
Doorsnede boorgat  1,5×De enkelbuis / 1,25×omschrijvende cirkel bundel
GPS punten         RD-coördinaten per sensorpunt
Hoeken             intree + uittree in ° én %
Titelblok          project · schaal · datum · getekend · akkoord · revisietabel
Logos              Logo3D.jpg + opdrachtgever logo
OPMERKINGEN        KLIC-disclaimer · CROW 96b · walk-over meetsysteem
```

Formaat A2Z4 (landscape). WeasyPrint via Jinja2. DWG is leidend, PDF is afgeleid.

---

## 9. Testdata — `docs/input_data_14maart/`

### HDD11 Haarlem Kennemerplein (primair referentieproject)

```
BerekeningHDD11.pdf                         → Ttot=30.106N, L=226,58m, 6 doorsneden
3D25V700-11-rev.1-A2Z4.pdf                  → referentietekening rev.1
3D25V700-11-A2Z4.pdf                        → referentietekening rev.0
3D25V700_Werkplan_HDD11.docx               → werkplan stijlreferentie (414 paragrafen)
Levering_25O0136974_1.zip                   → KLIC: 13MB IMKL XML, 11 beheerders, 1127 leidingen
CPT000000026582_IMBRO_A.gef                 → sondering intrede: RD(103851,489230) NAP+4,28m
CPT000000026578_IMBRO_A.gef                 → sondering uittrede: RD(103923,489219) NAP+4,31m
```

GPS punten HDD11 (rev.1):
```
A:   103896.9  489289.5    Tv1: 103916.4  489284.1    Tv2: 103934.3  489279.1
Th1: 103947.3  489275.5    Th2: 103960.8  489272.4    Tv3: 104079.7  489250.8
Tv4: 104109.2  489245.5    B:   104118.8  489243.7
```

Leidingparameters:
```
PE100 SDR11 · De=160mm · dn=14,6mm · Di=130,80mm · Db=60 · Dp=110 · Dg,r=240mm
MVin=+1,01m NAP · MVuit=+1,27m NAP · intreehoek=18° · uittreehoek=22°
Rv_intrede=60m · Rv_uittrede=80m · Rh=150m · L=226,58m · Lhor=223,72m
```

KLIC HDD11 — geanalyseerd:
```
11 beheerders · 1127 leidingen · dieptePeil=GEEN bij alle leidingen
KL1049 Reggefiber: 3 mantelbuizen + PDF boogzinker_8.pdf + gestuurde_boring_13.pdf
KL1040 Liander: 476 leidingen (LS+MS+Gas+Data)
GM0392 Gemeente Haarlem: 708 leidingen (LS+riool)
KL1100 PWN: 72 waterleidingen
```

### HDD28 Velsen-Noord Verkeersplein Noord N197

```
3D26V810-28 HDD28 Velsen-Noord.dxf         → PRIMAIRE DXF: 218 lagen, geometrie, NLCS
3D26V810-28_Standard.zip                    → DWG + XREFs (BGT/DKK/GWSW/KLIC)
```

DXF geometrie:
```
BOORLIJN:   LWPolyline 6 pnt + ARCs r=140m (intrede + uittrede) + LINEs
BOORGAT:    CIRCLE center=(104711,495901) r=15.0 en r=5.5
MAAIVELD:   LWPolyline 695 punten: start=(105241,495903) einde=(105520,495902)
Sensorpunten: Th1(105314,498803) Tv1(105315,498805) Tv2(105325,498847)
              Th2(105344,498885) Th3(105393,498962) Tv3(105406,498979)
              Th4(105448,499018) Tv4(105448,499018)
```

GWSW lagen in DXF (riool BOB-data):
```
GWSW|B-OI-RI-BOB-S              → BOB-punten (dieptemaatvoering)
GWSW|B-OI-RI-GWA_300-G         → gemengd riool 300mm
GWSW|B-OI-RI-HWA_200-G         → hemelwater 200mm
GWSW|B-OI-RI-DWA_PE_200-G      → droogweer 200mm
GWSW|B-OI-RI-VRIJVERVAL_300-G  → vrijverval riool 300mm
```

### HDD31 Katwoude Jaagweg (3D25V631)

```
Berekening 3D25V631.pdf                     → tweede berekening: Ø110mm, L=88,33m, Rv=50m
tekening 3D25V631-01-rev.1 Katwoude.pdf    → derde referentietekening (A2 formaat)
project info 3D25V631.txt                   → opdrachtketen context
```

Leidingparameters:
```
PE100 SDR11 · De=110mm · Drukloos
L=88,33m · Lhor=81,45m · Rv=50m
MVin=-0,69m NAP · MVuit=-1,18m NAP
Intreehoek=32° (62,49%) · Uittreehoek=26° (48,77%)
```

### Werkplan stijlreferenties (7 stuks)

`docs/input_data_14maart/` (origineel):
```
3D25V700_Werkplan_HDD11.docx                → Haarlem nov-2025, Liander MS, Formaat B
voorbeeld 3D23V322-01 Werkplan Katwoude.pdf → Trekvaart mei-2024
voorbeeld VV25V307-01 Werkplan Schalsum.pdf → Rijksweg A31 apr-2025, glasvezel
voorbeeld 3D25V647 Werkplan Amersfoort.pdf  → Rijksweg A1 jun-2025, RWS
```

`docs/Input_data_16maart/werkplannen/` (aangeleverd 16-03-2026):
```
3D24V473 Werkplan - Diemen, Muiderstraatweg.pdf        → sep-2024, Liander LS, Formaat A (oud), CKB S-A
3D25V679 HDD1 Werkplan - Ouderkerk aan de Amstel.pdf   → nov-2025, NURijnland, Formaat B, CKB S-A
3D25V679 HDD8&9 Werkplan - Ouderkerk Korte Dwarsweg.pdf → dec-2025, NURijnland, Formaat B, CKB S-A
3D25V638 Werkplan - Velsen-Noord, Rijksweg A22.pdf     → feb-2026, NURijnland+RWS, Formaat B, CKB ST-B, 3×Ø200
```

Primaire stijlreferenties voor generator: 3D25V679 HDD1 + 3D25V638 (meest recent, Formaat B).
Referentie RWS-patroon (beheerder-alinea 2.3): 3D24V473 Diemen + 3D25V638 Velsen-Noord.

### Werkplan templates + Martien's AI-aanpak

```
Stappenplan Werkplan met AI.docx            → Martien's eigen ChatGPT/NotebookLM prompts
Template Werkplan Gestuurde Boring.docx     → kale template
Werkplan_Template_Uitgebreid.docx           → uitgebreid template met sub-secties
```

Martien's bestaande AI-prompts per sectie:
```
Inleiding:  NotebookLM → "schrijf inleiding met reden project en rollen partijen"
2.1 Locatie: ChatGPT → "beknopte gebiedsomschrijving directe omgeving [adres]"
2.2 Historie: ChatGPT → "topotijdreis.nl onderzoek funderingsresten"
Observatie: "ChatGPT kijkt op internet, niet zozeer de kaarten"
```

### Logos (voor titelblok en werkplan)

```
Logo3D.jpg          → 3D-Drilling BV logo
Logo_Liander.png    → Liander (eindopdrachtgever HDD11)
Mook BV.jpg         → Mook Machineverhuur BV (eindopdrachtgever HDD31)
```

---

## 10. Eisenprofielen (seed data)

```python
EISENPROFIELEN = [
    {"beheerder": "RWS Rijksweg",         "dekking_weg": 3.0, "dekking_water": 5.0,  "Rmin": 150},
    {"beheerder": "Waterschap waterkering","dekking_weg": 5.0, "dekking_water": 10.0, "Rmin": 200},
    {"beheerder": "Provincie",             "dekking_weg": 2.0, "dekking_water": 3.0,  "Rmin": 120},
    {"beheerder": "Gemeente",              "dekking_weg": 1.2, "dekking_water": 1.5,  "Rmin": 100},
    {"beheerder": "ProRail spoor",         "dekking_weg": 4.0, "dekking_water": 6.0,  "Rmin": 150},
]
# Normen: NEN 3651 + beheerder-specifiek. Versie + datum tonen in UI.
```

---

## 11. Google Drive mapstructuur

Martien's bestaande Drive-structuur (bevestigd uit ZIP-analyse):
```
G:\Mijn Drive\GBT\
├── [ProjectNr] [ProjectNaam]\
│   ├── [ProjectNr] [Naam]\          ← XREF submap
│   │   ├── BGT[datum].dwg
│   │   ├── DKK[datum].dwg
│   │   ├── GWSW[datum].dwg          ← InfraCAD Map export, datumgestempeld
│   │   └── KLIC[meldingnr].dwg
│   └── bronnen\GB_[meldingnr].png
└── Ello - Martien\                  ← gedeelde testmap
```

Platform Drive-output structuur:
```
HDD-projecten/[ordernummer]-[naam]/
├── input/
│   ├── klic.zip
│   ├── gwsw_[datum].dwg  (optionele upload, platform leest BOB-lagen)
│   └── sonderingen/
└── output/
    ├── [ordernummer]-[volgnummer:02d]-rev.[n].dxf
    ├── [ordernummer]-[volgnummer:02d]-rev.[n].pdf
    └── [ordernummer]-werkplan-rev.[n].pdf
```

OAuth2 scope: `https://www.googleapis.com/auth/drive.file`

---

## 12. Testcase structuur

Naamgeving: `TC-[MODULE]-[LETTER]`. Geïsoleerd, draaien bij elke commit.

Kritieke testcases skeleton:
```
TC-1.1.A  SDR→wanddikte: De=160 SDR=11 → dn=14,55mm
TC-1.2.A  RD→WGS84: (103896.9, 489289.5) → correcte WGS84, afwijking <1cm
TC-1.2.B  Tangentiaal: hoek verbinding boorlijn = 0° (geen knik)
TC-4.1.A  DXF laagnamen: exact gelijk aan HDD28 referentie (218 lagen)
TC-4.1.B  DXF ezdxf parse: geen errors
TC-4.2.A  PDF titelblok HDD11: alle velden correct
TC-4.2.B  PDF GPS punten: Tv1=(103916.4, 489284.1)
```

Kritieke testcases per backlog item (schrijven bij implementatie):
```
B1  TC-2.1.A  KLIC HDD11 → 11 beheerders, 1127 leidingen
    TC-2.1.B  KL1049 → PDF-bijlage boogzinker gedetecteerd
B2  TC-2.2.A  AHN5 HDD11 locatie → MVin≈+1,01m NAP (±0,3m)
B3  TC-4.3.A  Werkplan HDD11 → 6 hoofdstukken + bijlagen A-G aanwezig
B4  TC-3.2.A  HDD11 geometrie → L=226,58m exact
B9  TC-2.3.A  GEF CPT26582 → qc-profiel = Sigma pagina 20
B11 TC-3.3.D  Ttot = 30.106N (vs BerekeningHDD11 pagina 9)
```

---

## 13. Kritieke domeinkennis

**KLIC dieptes zijn altijd onbetrouwbaar.** Alle 1127 leidingen HDD11 KLIC: `dieptePeil=GEEN`, alleen `verticalPosition=underground`. Structureel, niet uitzonderlijk. Altijd waarschuwen bij conflictcheck.

**Sleufloze leidingen — materiaalregel (primair).** De aanlegmethode volgt uit het buismateriaal:
```
PE (HPE, HDPE, PE100, PE80) = ALTIJD geboord (HDD of andere sleufloze techniek)
Staal                        = KAN geboord zijn (beoordeel in/uittree-ruimte)
PVC                          = gegraven (kan in principe NIET met HDD worden aangebracht)
Beton / asbestcement         = gegraven
```
Dit is de primaire detectieregel voor sleufloze leidingen in de KLIC. Staal markeren als `mogelijk_sleufloze_techniek=True` (niet hard als sleufloze). PVC/beton nooit als sleufloze behandelen.

**Sleufloze leidingen — bijlage-heuristiek (aanvullend).** KL1049 Reggefiber HDD11: 3 mantelbuizen zonder diepte + PDF-bijlagen `boogzinker_8.pdf` + `gestuurde_boring_13.pdf`. Platform detecteert dit: leidingtype bevat "mantelbuis" EN diepte_m IS NULL EN PDF-bijlage aanwezig → `sleufloze_techniek=True`. Dit is een aanvullende heuristiek bovenop de materiaalregel, voor gevallen waar het materiaal niet in het IMKL-veld staat.

**EV — Eis Voorzorgsmaatregel (wettelijk kritisch).** Sommige K&L in de KLIC zijn gemarkeerd met een EV. IMKL-element: `EisVoorzorgsmaatregel` met verplichte contactgegevens van de netbeheerder.
```
Betekenis:   Vóór aanvang werkzaamheden MOET contact/afmelding plaatsvinden bij netbeheerder.
Risico:      Niet afhandelen → hoge boetes van Agentschap Telecom.
Ontwerpregel: Altijd buiten de EV-zonering ontwerpen.
Als niet mogelijk: mailconversatie met netbeheerder voeren en meeleveran bij ontwerp.
```
Platform-verplichtingen: EV-leidingen markeren (`ev_verplicht=True`), contactgegevens opslaan, WAARSCHUWING prominent tonen op de brondata-pagina, EV-zone als aparte laag in DXF (laag `EV-ZONE`), EV-zone zichtbaar in PDF-situatietekening met voetnoot contactgegevens.

**KLIC melding types.**
- Oriëntatiegraving: standaard bij ontwerp ter voorbereiding (uitvoering > 4 weken).
  Op oriëntatiegraving mag NIET worden gegraven — alleen voor ontwerp.
- Graafmelding: als uitvoering ≤ 4 weken gepland is.
  Graafmelding verloopt na 20 werkdagen.
- Volgorde: KLIC melding doen (stap 1.3 in proces) → wachten op levering Kadaster
  → dan pas KLIC-ZIP uploaden in platform (stap 2.1).
  Platform toont melding: "KLIC-ZIP uploaden kan pas na ontvangst van Kadaster."
- Platform-tip: als uitvoerdatum bekend is en < 4 weken, toon waarschuwing om graafmelding
  te overwegen in plaats van oriëntatie.

**Topotijdreis — historische kaarten (backlog 11).**
Topotijdreis.nl toont historische topografische kaarten van Nederland.
Waarde bij boorontwerp: detectie van gesloopte objecten waarvan funderingen mogelijk nog aanwezig zijn.

Drie gedocumenteerde cases van Martien:
1. Viaduct A2: 20 jaar geleden verbreed — oud viaduct gesloopt maar heipalen mogelijk nog aanwezig.
   Locatie heipalen niet meer achterhaald → ruim omheen ontwerpen.
2. Boring gestopt op 9m en 12m diepte: topotijdreis toonde achteraf water en brug op die locatie.
   Waarschijnlijk gestuit op fundering gesloopte brug.
3. Boring langs tunnel: stoomtramverbinding en brug uit 1912 zichtbaar op topotijdreis.
   Inschatting diepte heipalen 1912 → ruim onderdoor boren.

Platform-aanpak (te onderzoeken): REST API of WMS/WCS service van topotijdreis beschikbaar?
Als ja: automatisch kaartafbeeldingen tonen per tijdperiode voor het tracégebied.
Tijdsbereik: bepalen samen met Martien (suggestie: 1900–heden, per 10-jaar stap).
Minimale implementatie als API niet beschikbaar: link-out naar topotijdreis.nl met tracé-coördinaten.

**Riool-taxonomie.** KLIC maakt onderscheid:
```
Persriool     = onder druk, geen BOB-afschot vereist
Vrijverval:
  DWA  (droogweerafvoer / vuilwater)  — BOB-maten standaard aanwezig en relevant
  HWA  (hemelwaterafvoer)             — BOB-maten NIET standaard beschikbaar
                                        Dieptebereik: 80–120 cm (80 cm = vorstgrens NL)
                                        Ligt NIET op afschot
  GWA  (gemengd riool)                — BOB-maten standaard aanwezig
```
BOB-bronnen per prioriteit: (1) GWSW via `apps.gwsw.nl`, (2) gemeente-specifieke portalen (Haarlem: `kaart.haarlem.nl` — heeft BOB + bomendata incl. kruindiameter), (3) gemeente per mail opvragen.

**BOB uit vrije KLIC tekstvelden.** BOB-informatie zit soms NIET in gestructureerde IMKL-velden maar in vrije tekstvelden `label` en `toelichting`. Voorbeelden: `"R 234, +/-2.58 -NAP"`, `"diepte gem. -2.6m tov NAP"`. Platform extraheert dit via regex maar markeert altijd als `diepte_bron="tekstveld_onzeker"` — nooit als betrouwbare diepte behandelen.

**Bomen als obstakel.** Bomen zijn beschermd in Nederland. Wortelradius ≈ kruindiameter van de boom. Worteldiepte: circa 1 meter. Bij boomconflict kiest ontwerper altijd voor boren i.p.v. graven. Bomendata Haarlem beschikbaar via `kaart.haarlem.nl` (kruindiameter per boom).

**DWG vs DXF.** Martien werkt in AutoCAD Map 3D 2023 met XREF-structuur (BGT/DKK/GWSW/KLIC als losse DWGs). Platform genereert standalone DXF zonder XREFs — Martien importeert dit in zijn AutoCAD. Akkoord.

**GWSW als upload.** InfraCAD Map exporteert GWSW-data als datumgestempelde DWG. Platform accepteert dit als optionele upload en leest BOB-lagen eruit via ezdxf (DXF conversie). GWSW API apart aanroepen is niet nodig.

**RDNAP altijd.** Coördinaten altijd in RD New EPSG:28992, 2 decimalen. Kaart is oriëntatie, coördinaten zijn primaire invoer.

**Coördinateninvoer — kaart-klik primair.** Martien wil coördinaten invoeren door op de kaart te klikken, niet handmatig typen. Kaart toont BGT, DKK, KLIC als lagen. Klik → WGS84 → RD-conversie → 2 decimalen (cm-nauwkeurig). Handmatig typen blijft als fallback. Dit verandert de UI van het tracé-invoerscherm fundamenteel t.o.v. de walking skeleton.

**Werkplan structuur (gevalideerd op 5 werkplannen, 16-03-2026).** 6 genummerde hoofdstukken (niet 7) + bijlagen A t/m G. Twee formaatversies:
- Formaat A (oud, pre-2025): 2.1 Locatie · 2.2 Historie · 2.3 Infrastructuur (beheerder erin)
- Formaat B (huidig): 2.1 · 2.2 · 2.3 Infrastructuur · 2.3 Geotechniek · 2.4 Overige — let op: dubbele 2.3 en dubbele 6.4 zijn typefouten in het levende sjabloon; generator gebruikt correcte nummering.
CKB-categorie varieert op basis van berekende trekkracht: ST-A (<9T) · ST-B (10–39T) · ST-C (40–149T) · ST-D (>150T). Niet hardgecodeerd als "middelgroot".
~60% van een werkplan is boilerplate (secties 3.2.1–3.2.4, 5.1–5.2, 6.2, 6.4 volledig identiek). NURijnland-programmatekst (alinea 1+2 inleiding) is herbruikbaar blok voor NURijnland-projecten.

**Werkplan deels automatisch.** Bespaart Martien's eigen tijd (niet die van zijn collega). Volledig boilerplate (geen AI): 3.2.1–3.2.4, 5.1–5.2, 6.2 personeel, 6.4. Template+data (geen AI): titelblok, buis-specs, CKB-tabel, tijdsplanning, berekeningsresultaten. Claude API (projectspecifiek): 2.1 Locatie, 2.2 Historie, 2.3 K&L, 2.3 Geotechniek, 2.4 Overige. Locatiespecifiek vereist Martien's input. Martien levert stijlreferentie-werkplannen aan vóór start backlog 1.

**Tracévarianten — formaat.** Simpel houden: 1 kaartje met knelpunt + 1-2 alternatieve lijnen + beknopte onderbouwing. Geen uitgebreid vergelijkingsdocument. Formaat: eenvoudig PDF-kaartje (A4).

**Opdrachtketen — drie partijen, elk "Opdrachtgever" genoemd.**
De formele opdrachtketen:
  Asset owner (netbeheerder: Liander, KPN, Ziggo, Delta, Relined)
    → Aannemer (DMMB, van Baarsen, van Gelder)
      → Boorbedrijf (3D-Drilling, R&D Drilling)
        → GestuurdeBoringTekening.nl (Martien)

Soms werkt Martien rechtstreeks voor de aannemer of de asset owner.
Alle drie partijen worden kortweg "Opdrachtgever" genoemd, maar hebben verschillende belangen:

- Boorbedrijf: uitvoerbaarheid, minimaal risico, langere boringen (meer meters = meer omzet),
  voldoende ruimte voor materieel. Overleg: technische haalbaarheid tracé.
- Aannemer: goede planning, geen verrassingen, tijdige oplevering.
  Overleg: fasering en knelpunten.
- Asset beheerder (netbeheerder): efficiënt A→B, lage kosten, geen schade aan eigen assets.
  Overleg: tracékeuze en vergunning.

Communicatierichting hangt af van het knelpunt — soms wordt een schakel overgeslagen.
Op de tekening staan namen en logo's van alle relevante partijen (opdrachtgever, aannemer, boorbedrijf).

Titelblok tekeningverantwoordelijkheid:
- Tekenaar: altijd Martien Luijben — ook als collega S. Choychod de uitwerking heeft gedaan.
  Martien reviewt en accordeert alle ontwerpen voor oplevering.
- Akkoord: Michel Visser (3D-Drilling) — contactpersoon bij het boorbedrijf, reviewt het ontwerp.
  Visser is geen eindgebruiker van het platform maar ontvangt/reviewt de output.

**Intrekkracht optioneel.** Alleen als opdrachtgever vraagt. Martien: "nice-to-have." Backlog positie 17.

**Sigma validatie — ontwerpconstraint backlog 17.**
Sigma van Adviesbureau Schrijvers is gecertificeerde/gevalideerde software (NEN 3651).
Als het platform zelf sterkte-, intrekkracht- en boorspoeldrukberekeningen uitvoert, kan validatie
van de platformsoftware een contractuele of wettelijke eis zijn.
Martien's suggestie: transparante weergave van alle berekenstappen (zoals Sigma's uitdraai)
kan als acceptabel alternatief worden beschouwd. Onderzoeken bij start backlog 17.
Deltares biedt ook een software tool aan als alternatief voor Sigma.

**Vergunningscheck omgevingswet.overheid.nl (backlog 14).**
Via https://omgevingswet.overheid.nl/home kan worden gecheckt welke voorschriften van
overheidswege van toepassing zijn op een tracélocatie:
- Rijkswaterstaat (RWS) — rijksweg/rijkswater
- Provincie — provinciale weg/water
- Waterschap — waterkering/watergang
- Gemeente — gemeentelijk grondgebied

Los hiervan gelden ook de voorschriften van K&L asset beheerders via de KLIC-levering.
Platform-aanpak: onderzoeken of omgevingswet.overheid.nl een publieke API heeft.
Als ja: automatisch relevante regimes bepalen op basis van tracé-coördinaten.
Als nee: gestructureerde link-out met coördinaten als fallback.

**DWG output bestandsversie.** Genereer DXF R2013 (AC1027) — compatibel met AutoCAD 2014+. Martien gebruikt AutoCAD Map 3D 2023 maar R2013 is veilige minimum.

**Boringtypen — profielgeometrie.**
```
B/N (gestuurde boring / nano): 5 segmenten, tangentiaal aansluitend
  1. Neergaand recht    → vaste hoek (intreehoek), rechte lijn
  2. Neergaande curve   → ARC schuin→horizontaal (Rv_intrede)
  3. Horizontaal        → rechte lijn, variabele lengte
  4. Opgaande curve     → ARC horizontaal→schuin (Rv_uittrede)
  5. Opgaand recht      → vaste hoek (uittreehoek), rechte lijn

Z/BZ (boogzinker): 1 segment, één vaste boog
  Standaard bogen: 5° / 7,5° / 10°
  10 mogelijke standen
  Lengte = booghoek × stand
  Geen horizontaal deel, geen Rv-cirkels — gewoon één ARC
```

**Type C — Calculatie.**
Losse Sigma berekeningen (sterkte, intrekkracht, boorspoeldruk) zonder tekening of werkplan. Vooral voor provincie Groningen. Type C heeft: Berekening + Document(pdf). Geen TracePunten, geen DXF, geen werkplan.

**KLIC versioning.**
Eén meldingnummer kan meerdere versies hebben:
- Versie 1: oriëntatiemelding (ontwerp ter voorbereiding)
- Versie 2: hermelding na wijziging
De engineer kiest bewust welke versie per boring geldt.

**KLIC twee leveringsformaten.**
- Formaat A: ZIP met meerdere XML bestanden per beheerder (bijv. HDD11 Haarlem: Levering_25O0136974_1.zip)
- Formaat B: Enkel GML V2 bestand, alle features in één file (bijv. IJmuiden: GI_gebiedsinformatielevering_25O0063608_1_V2.xml — 2.7MB, 1952 features, 9 beheerders)
Platform parser moet beide formaten ondersteunen. Beide gebruiken dezelfde IMKL namespace.

**Orderbeheer — "wij zijn de bron".**
Platform vervangt GSheets als systeem of record. Nid (Sopa Choychod) houdt de orderlijst bij. Volledige GSheets migratie (~2087 rijen, ~2454 orders). RD-coördinaten extractbaar uit PDOK-URLs in de GSheets.

**Status-workflow orders.**
```
Order received → In progress → Delivered → Waiting for approval → Done
                                                                 ↘ Cancelled
```
"Waiting for approval" = geleverd maar geen akkoord ontvangen. Komt vaak voor — opdrachtgevers reageren niet altijd. Statusmail lost dit op.

**Wekelijkse statusmail.**
Elke maandag automatisch per opdrachtgever: overzicht openstaande akkoorden + geleverde orders zonder bevestiging. Opdrachtgever kan antwoorden → mail komt bij Martien.

**Tekenaar per order.**
Default: Martien Luijben. Nid (Sopa Choychod) doet uitwerkingen. Platform toont "Mijn orders" filter. Tekenaarveld is wijzigbaar per order.

**PDOK URL bevat RD-coördinaten.**
GSheets PDOK-kolom bevat URLs met `x=...&y=...` parameters in RD New. Platform kan bij migratie automatisch RD-coördinaten extraheren. Na migratie genereert platform zelf de PDOK-URL zodra coördinaten zijn ingevoerd.

**Waterschap-kaarten.**
Nid plakt handmatig adressen vanuit Google Maps naar waterschapskaarten. Platform automatiseert dit: coördinaten → correcte waterschap-URL. Per waterschap een aparte kaart-URL (ArcGIS Experience/Hub).

**Klantcodes.**
22+ unieke klantcodes: 3D, RD, TM, KB, BT, QG, MM, HS, VB, VG, EN, PZ, MT, TI, NR, etc. Seed-data bij migratie.

---

## 14. Buiten scope (altijd)

- Offertegenerator (calculatie is WEL in scope, offerte NIET)
- Projectmanagement (geen Jira/Asana)
- Multi-tenant beheer (Inodus beheert via Railway)
- Automatisch uploaden naar Omgevingsloket
- BIM / IFC export
- Klant-intakeformulier (opdrachtgevers zijn uitvoerders, geen technici)

---

## 15. Deployment

**Geen Docker.** Railway detecteert Python via nixpacks en deployt automatisch.

```bash
# Lokaal starten
uvicorn app.main:app --reload

# Productie — gewoon pushen
git push origin main
# → Railway autodeploy → hdd.inodus.nl

# Database initialiseren (SQLite, eerste keer)
python scripts/init_db.py

# Seed (één workspace + eisenprofielen + gebruikers)
python scripts/seed.py
```

**`.env` (lokaal, nooit in git):**
```
ENV=development
DATABASE_URL=sqlite:///./hdd.db

# Gebruikers
USER_MARTIEN_PASSWORD=kies-een-wachtwoord
USER_VISSER_PASSWORD=kies-een-wachtwoord
USER_TEST_PASSWORD=test123          # alleen actief als ENV=development

# Backlog 1 (werkplan generator)
ANTHROPIC_API_KEY=
```

**`.env.example` (wél in git, zonder waarden):**
```
ENV=development
DATABASE_URL=sqlite:///./hdd.db
USER_MARTIEN_PASSWORD=
USER_VISSER_PASSWORD=
USER_TEST_PASSWORD=
ANTHROPIC_API_KEY=
```

**Railway dashboard** (productie omgevingsvariabelen):
```
ENV=production
DATABASE_URL=sqlite:///./data/hdd.db   # Railway volume mountpoint
USER_MARTIEN_PASSWORD=[sterk wachtwoord]
USER_VISSER_PASSWORD=[sterk wachtwoord]
# USER_TEST_PASSWORD niet instellen in productie
ANTHROPIC_API_KEY=[indien backlog 1 actief]
```

**Auth implementatie (HTTPBasic):**
```python
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

security = HTTPBasic()

USERS = {
    "martien": settings.USER_MARTIEN_PASSWORD,
    "visser":  settings.USER_VISSER_PASSWORD,
}
if settings.ENV == "development":
    USERS["test"] = settings.USER_TEST_PASSWORD

def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    password = USERS.get(credentials.username, "")
    if not secrets.compare_digest(credentials.password, password):
        raise HTTPException(status_code=401)
    return credentials.username
```

---

## 16. Instructie voor de Builder Agent

Lees dit bestand volledig. Daarna:

1. Maak de projectstructuur aan conform sectie 5
2. Schrijf bouwplan in `docs/backlog/00_walking_skeleton.md`
3. Begin met datamodel refactor (backlog 0): Order → Boring[] + type B/N/Z/C + tekenaar + KLIC versioning
4. Implementeer module `order/` (CRUD + cockpit) als eerste UI-module
5. Implementeer module `boring/` (CRUD per order) als tweede
6. Schrijf testcases **vóór** implementatie per module
7. Gebruik uitsluitend testdata uit `docs/input_data_14maart/`
8. Vraag akkoord van Architect Agent vóór elke nieuwe module
9. Bij twijfel over scope: signaleer en wacht op goedkeuring

**First Time Right.** Elke module volledig afgerond (inclusief testcases) voor de volgende begint.
