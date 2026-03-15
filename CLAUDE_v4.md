# CLAUDE.md — HDD Ontwerp Platform
**LeanAI Platform · Architect Agent**
Versie: 4.0 | 2026-03-14

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
- Calculatie of offerte — expliciet buiten scope

---

## 2. Aanpak: walking skeleton + backlog

**Geen iteraties of fasen.** Één aanpak:

1. **Walking Skeleton** — eerste oplevering. Volledig werkend end-to-end systeem. Complexe stappen op override (handmatig invullen). Martien werkt er direct mee.
2. **Backlog** — geprioriteerde features. Één voor één bouwen, testen, uitrollen. Volgorde herijken met Martien na elke oplevering.

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

### Backlog (na skeleton, volgorde met Martien)

| # | Feature | Waarde | Override vervangt |
|---|---|---|---|
| 1  | KLIC IMKL 2.0 parser | KERN | Placeholder leidingen |
| 2  | AHN5 maaiveld PDOK WCS | KERN | Handmatig MVin/MVuit |
| 2b | **EV-zone DXF rendering + ontwerp-workflow** | ★★★★★ WETTELIJK | EV-waarschuwing handmatig |
| 3  | Werkplan generator Claude API | ★★★★★ Martien | ~2u schrijven |
| 4 | Boorprofiel geometrie ARCs + tangentiaal | KERN | Handmatige hoeken |
| 5 | Sleufloze leidingen detectie KLIC PDF | ★★★★ Martien | Handmatig uitzoeken |
| 6 | GWSW riool BOB + gemeente-mail auto | ★★★★ Martien | Handmatig mailen |
| 7 | Conflictcheck K&L 3D afstand | KERN | Altijd WAARSCHUWING |
| 8 | Dinoloket sonderingen REST API | ★★★ Martien | Handmatig Dinoloket |
| 9 | GEF/CPT parser + Robertson classificatie | OPTIONEEL | Handmatig grondtype |
| 10 | Tracévarianten vergelijken + PDF | ★★★★ Martien | Telefonisch overleg |
| 11 | Intrekkrachtberekening NEN 3651 | OPTIONEEL | Handmatig Sigma |

---

## 3. LeanAI principes

- **Lean first.** Skeleton is zo klein mogelijk terwijl het end-to-end werkt.
- **Modulaire monoliet.** Één FastAPI backend, intern gescheiden per domein.
- **Deterministisch.** Berekeningen zijn expliciete Python code, nooit AI-prompts.
- **Workspace-ready dag één.** `workspace_id` op alle entiteiten. Eén workspace, onzichtbaar.
- **Override altijd beschikbaar.** Geen automatisering zonder handmatige fallback.
- **Testcases per module.** Geïsoleerd, draaien bij elke commit. Testdata = echte projecten.
- **First Time Right.** Liever langzamer en correct.

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
| AI tekst | Anthropic Claude API (backlog 3) | Werkplan generator |
| Auth | FastAPI HTTPBasic + `.env` | 2 vaste gebruikers, geen token overhead |
| Hosting | Railway — hdd.inodus.nl | Managed, autodeploy bij git push |
| CI/CD | Railway autodeploy (git push → live) | Geen Docker, geen pipeline file |

---

## 5. Projectstructuur

```
hdd-platform/
├── backend/
│   └── app/
│       ├── core/           # workspace middleware, auth, config
│       ├── project/        # project CRUD
│       ├── geo/            # KLIC GML parser, geometrie, conflict
│       ├── rules/          # eisenprofielen seed
│       ├── design/         # boorprofiel geometrie engine
│       ├── calculations/   # LEEG → backlog 11
│       ├── documents/      # PDF + DXF generator
│       ├── ai_assist/      # LEEG → backlog 3
│       ├── drive/          # Google Drive sync
│       └── api/            # FastAPI routes
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
               # 1 workspace in skeleton, seed via migratie

Project        id · workspace_id · naam · opdrachtgever · ordernummer
               leidingmateriaal · De_mm · SDR · medium · Db_mm · Dp_mm · Dg_mm

Boring         id · project_id · naam · status · intreehoek · uittreehoek

TracePunt      id · boring_id · volgorde · type(intree/tussenpunt/uittree)
               RD_x · RD_y · Rh_m  # Rh alleen bij tussenpunten

BoorProfiel    id · boring_id · L_totaal_m · L_hor_m · geometrie(WKT)
               sensorpunten(JSON [{label, RD_x, RD_y, NAP_z}])

KLICLeiding    id · boring_id · beheerder · leidingtype · geometrie_wkt(TEXT)
               diepte_m(NULL!) · diepte_override_m · bron_pdf_url

MaaiveldProfiel id · boring_id · punten(JSON [{afstand_m, NAP_m, override}])

Doorsnede      id · boring_id · afstand_m · NAP_m · grondtype
               GWS_m · phi_graden · E_modulus · override_vlag

Berekening     id · boring_id · Ttot_N(override) · bron(sigma/platform)

Document       id · boring_id · type(pdf/dxf) · versie · drive_url · created_at
```

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

### Werkplan stijlreferenties (4 stuks)

```
3D25V700_Werkplan_HDD11.docx                → Haarlem nov-2025, Liander MS
voorbeeld 3D23V322-01 Werkplan Katwoude.pdf → Trekvaart mei-2024
voorbeeld VV25V307-01 Werkplan Schalsum.pdf → Rijksweg A31 apr-2025, glasvezel
voorbeeld 3D25V647 Werkplan Amersfoort.pdf  → Rijksweg A1 jun-2025, RWS
```

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
    ├── [ordernr]-rev.[n].dxf
    ├── [ordernr]-rev.[n].pdf
    └── [ordernr]-werkplan-rev.[n].pdf
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
B3  TC-4.3.A  Werkplan HDD11 → 7 hoofdstukken + bijlagen A-G aanwezig
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

**Werkplan deels automatisch.** Bespaart Martien's eigen tijd (niet die van zijn collega). Secties die volledig automatisch kunnen: inleiding, 2.3 KLIC-samenvatting, 2.3 geotechniek, 4 berekeningen samenvatting, 5 kwel standaard, 6.1 CKB-klasse, 6.3 tijdsplanning. Locatiespecifiek (2.1, 2.2, 2.4) vereist Martien's input. Martien levert stijlreferentie-werkplannen aan vóór start backlog 3.

**Tracévarianten — formaat.** Simpel houden: 1 kaartje met knelpunt + 1-2 alternatieve lijnen + beknopte onderbouwing. Geen uitgebreid vergelijkingsdocument. Formaat: eenvoudig PDF-kaartje (A4).

**Opdrachtketen.** Liander (eindopdrachtgever) → aannemer (bijv. DMMB) → 3D-Drilling → GestuurdeBoringTekening.nl (Martien). Alle lagen vermeldenswaardig in titelblok + werkplan.

**Intrekkracht optioneel.** Alleen als opdrachtgever vraagt. Martien: "nice-to-have." Backlog positie 11.

**DWG output bestandsversie.** Genereer DXF R2013 (AC1027) — compatibel met AutoCAD 2014+. Martien gebruikt AutoCAD Map 3D 2023 maar R2013 is veilige minimum.

---

## 14. Buiten scope (altijd)

- Calculatiemodule / offertegenerator
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

# Backlog 3 (werkplan generator)
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
ANTHROPIC_API_KEY=[indien backlog 3 actief]
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
3. Begin met module `project/` (CRUD) als eerste
4. Schrijf testcases **vóór** implementatie per module
5. Gebruik uitsluitend testdata uit `docs/input_data_14maart/`
6. Vraag akkoord van Architect Agent vóór elke nieuwe module
7. Bij twijfel over scope: signaleer en wacht op goedkeuring

**First Time Right.** Elke module volledig afgerond (inclusief testcases) voor de volgende begint.
