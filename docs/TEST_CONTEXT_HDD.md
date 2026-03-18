# TEST_CONTEXT_HDD.md — HDD Ontwerp Platform
**Projectspecifieke testcontext voor gebruik met TEST_AGENT_v2.md**
Versie: 2.0 | 2026-03-18 (volledige backlog afgerond)

---

## Gebruik

Dit document wordt altijd gelezen **samen met TEST_AGENT_v2.md**.

`TEST_AGENT_v2.md` bevat het generieke test operating model (rollen, modi, checklists, rapportage).
Dit document bevat alles wat de Test Agent moet weten om dat model correct toe te passen op het HDD-platform.

**Aanroepformaat:**
```
Test HDD platform: http://localhost:8000 | modus: SMOKE
Test HDD platform: http://localhost:8000 | modus: FULL
Test HDD platform: http://localhost:8000 | modus: FEATURE | module: DXF output
Test HDD platform: https://hdd.inodus.nl | modus: PRODUCTION
```

---

## 1. Applicatieprofiel

| Eigenschap | Waarde |
|---|---|
| Type | Portal — authenticatie, 2 vaste gebruikers |
| URL lokaal | http://localhost:8000 |
| URL productie | https://hdd.inodus.nl |
| Backend | Python FastAPI + Jinja2 (server-side HTML) |
| Database | SQLite (bestand: hdd.db) |
| Auth | FastAPI HTTPBasic (.env wachtwoorden) |
| Hosting | Railway — autodeploy bij git push |
| DXF output | ezdxf R2013 formaat |
| PDF output | WeasyPrint + Jinja2 |

**Risicoprofiel:** HOOG op DXF/PDF output. Een fout in de tekening leidt tot een onjuiste vergunningsaanvraag. Domein-specifieke validaties (zie sectie 5) wegen zwaarder dan generieke UI-checks.

---

## 2. Gebruikers en testaccounts

| Gebruiker | Wachtwoord | Rol | Wanneer beschikbaar |
|---|---|---|---|
| `martien` | uit `.env` | Primaire gebruiker, eigenaar | Altijd |
| `visser` | uit `.env` | Tekenaar, accordeert tekeningen | Altijd |
| `test` | `test123` | Testgebruiker | **Alleen `ENV=development`** |

**Kritieke auth-testcase:** testgebruiker mag NOOIT actief zijn in productie (`ENV=production`). Dit is een NO-GO.

HTTPBasic betekent: browser toont een inlogdialoog. Bij automatische tests: Basic Auth header meesturen.
```
Authorization: Basic base64(gebruiker:wachtwoord)
```

---

## 3. Applicatiefasen en bijbehorende testmodus

| Fase | Situatie | Modus (TEST_AGENT_v2 §3.2) |
|---|---|---|
| Walking skeleton oplevering | Eerste werkende versie | `FULL` |
| Elke backlog oplevering | Nieuwe module toegevoegd | `FEATURE` + regressie DXF/PDF |
| Hotfix productie | Bug opgelost | `SMOKE` + gerichte regressie |
| Periodieke check productie | Wekelijkse health check | `PRODUCTION` |
| Skeleton go-live | Eerste keer naar hdd.inodus.nl | `FULL` |

---

## 4. Applicatieroutes (scope)

```
# Cockpit
GET  /orders/                                          Cockpit (orderlijst + stats)
GET  /orders/export/csv                                CSV export
GET  /orders/statusmail                                Statusmail concepten per klant
GET  /orders/nieuw                                     Nieuw order formulier
POST /orders/nieuw                                     Order aanmaken

# Order
GET  /orders/{id}                                      Order detail
POST /orders/{id}/update                               Order bewerken
GET  /orders/{id}/factuur                              Factuur concept (SnelStart)
POST /orders/{id}/klic                                 KLIC ZIP/XML/GML uploaden

# Boring
GET  /orders/{id}/boringen/{volgnr}                    Boring detail
POST /orders/{id}/boringen/{volgnr}/update             Boring bewerken
GET  /orders/{id}/boringen/{volgnr}/trace              Tracé invoer (kaart-klik)
POST /orders/{id}/boringen/{volgnr}/trace              Tracé opslaan

# Brondata
GET  /orders/{id}/boringen/{volgnr}/brondata           KLIC + maaiveld + doorsneden
POST /orders/{id}/boringen/{volgnr}/maaiveld           Maaiveld handmatig
POST /orders/{id}/boringen/{volgnr}/maaiveld/ahn5      AHN5 ophalen (JSON)

# Analyse-tools
GET  /orders/{id}/boringen/{volgnr}/conflictcheck      Conflictcheck K&L 3D
GET  /orders/{id}/boringen/{volgnr}/sleufloze           Sleufloze leidingen
GET  /orders/{id}/boringen/{volgnr}/gwsw               GWSW riool BOB
GET  /orders/{id}/boringen/{volgnr}/topotijdreis        Historische kaarten
GET  /orders/{id}/boringen/{volgnr}/vergunning          Vergunningscheck
GET  /orders/{id}/boringen/{volgnr}/sonderingen         Dinoloket/BRO

# Varianten + As-Built
GET  /orders/{id}/boringen/{volgnr}/varianten           Tracévarianten vergelijken
POST /orders/{id}/boringen/{volgnr}/varianten/nieuw     Variant toevoegen
GET  /orders/{id}/boringen/{volgnr}/asbuilt             As-Built invoer
POST /orders/{id}/boringen/{volgnr}/asbuilt             As-Built opslaan

# Downloads
GET  /orders/{id}/boringen/{volgnr}/dxf                DXF download
GET  /orders/{id}/boringen/{volgnr}/pdf                PDF download (A3 4-zone)
```

Alle routes vereisen HTTPBasic auth. Zonder auth → 401 + `WWW-Authenticate: Basic` header.
Huidige test suite: **199 tests groen, 15 skipped (KLIC testdata).**

---

## 5. Domein-specifieke testcases

Dit zijn testcases die **niet** in de generieke checklists van TEST_AGENT_v2 staan maar cruciaal zijn voor dit platform. Altijd uitvoeren — ook bij SMOKE.

### 5.1 DXF output (hoogste prioriteit)

Referentie: `docs/input_data_14maart/3D26V810-28 HDD28 Velsen-Noord.dxf` (218 lagen, gevalideerd)

| Code | Test | Verwacht | Fout = |
|---|---|---|---|
| DXF-01 | DXF download response | Content-Disposition: attachment, bestandsnaam eindigt op .dxf | BLOCKER |
| DXF-02 | ezdxf parse: `ezdxf.readfile(downloaded.dxf)` | Geen parse errors | BLOCKER |
| DXF-03 | DXF versie | `doc.dxfversion == "AC1027"` (R2013) | HIGH |
| DXF-04 | Laag BOORLIJN aanwezig | ACI-kleur=1, lijntype=Continuous | BLOCKER |
| DXF-05 | Laag BOORGAT aanwezig | ACI-kleur=5, lijntype=DASHDOT | BLOCKER |
| DXF-06 | Laag MAAIVELD aanwezig | ACI-kleur=122 | HIGH |
| DXF-07 | Laag MAATVOERING aanwezig | ACI-kleur=170 | HIGH |
| DXF-08 | Laag MAATVOERING-GRIJS aanwezig | ACI-kleur=251 | HIGH |
| DXF-09 | Laag ATTRIBUTEN aanwezig | ACI-kleur=252 | HIGH |
| DXF-10 | Laag TITELBLOK_TEKST aanwezig | ACI-kleur=7 | HIGH |
| DXF-11 | K&L lagen aanwezig | LAAGSPANNING(190) MIDDENSPANNING(130) LD-GAS(50) WATERLEIDING(170) RIOOL-VRIJVERVAL(210) | HIGH |
| DXF-12 | NLCS lijntype-definities | KL-LS-N, KL-MS-N, KL-HS-N, KL-GAS-LD-N, KL-WATER-N aanwezig in doc.linetypes | HIGH |
| DXF-13 | BOORLIJN heeft entiteiten | `msp.query('* [layer=="BOORLIJN"]')` niet leeg | BLOCKER |
| DXF-14 | BOORGAT cirkels HDD11 | r1 = Dg/2 = 120mm, r2 = De/2 = 80mm | HIGH |
| DXF-15 | Sensorpunt label "A" aanwezig | TEXT entiteit op laag ATTRIBUTEN met tekst "A" | MEDIUM |
| DXF-16 | Totaal lagen ≥ 15 | Minimaal alle gedefinieerde lagen | HIGH |

**Volledige laagnamenlijst ter referentie:**
```
BOORLIJN(1) BOORGAT(5) MAAIVELD(122) MAATVOERING(170) MAATVOERING-GRIJS(251)
ATTRIBUTEN(252) TITELBLOK_TEKST(7) LAAGSPANNING(190) MIDDENSPANNING(130)
HOOGSPANNING(10) LD-GAS(50) WATERLEIDING(170) RIOOL-VRIJVERVAL(210)
PERSRIOOL(210) KADASTER(150) WEGDEK(252)
```

---

### 5.2 PDF output

Referentie: `docs/input_data_14maart/3D25V700-11-rev.1-A2Z4.pdf`

| Code | Test | Verwacht | Fout = |
|---|---|---|---|
| PDF-01 | PDF download response | Content-Type: application/pdf, niet leeg | BLOCKER |
| PDF-02 | PDF niet corrupt | PDF opent zonder errors (pypdf of pdftotext) | BLOCKER |
| PDF-03 | Titelblok: project naam aanwezig | Projectnaam zichtbaar in PDF tekst | BLOCKER |
| PDF-04 | Titelblok: getekend=M.Luijben | Tekst "M.Luijben" aanwezig | HIGH |
| PDF-05 | Titelblok: akkoord=M.Visser | Tekst "M.Visser" aanwezig | HIGH |
| PDF-06 | GPS punten tabel aanwezig | "A:" gevolgd door RD-coördinaten | HIGH |
| PDF-07 | GPS punt A HDD11 | "103896.9" en "489289.5" aanwezig | HIGH |
| PDF-08 | Intreehoek aanwezig | "18°" en "32%" aanwezig (HDD11) | HIGH |
| PDF-09 | KLIC-disclaimer aanwezig | Tekst "indicatief" of "KLIC" in OPMERKINGEN | HIGH |
| PDF-10 | Doorsnede boorgat sectie aanwezig | Sectie/label "DOORSNEDE BOORGAT" aanwezig | MEDIUM |
| PDF-11 | Logo 3D-Drilling aanwezig | Afbeelding aanwezig in PDF (niet lege img) | MEDIUM |
| PDF-12 | Geen WeasyPrint errors in server logs | Geen "ERROR" in logs bij generatie | HIGH |

---

### 5.3 Berekeningen en validaties

| Code | Test | Input | Verwacht | Fout = |
|---|---|---|---|---|
| CALC-01 | SDR→wanddikte | De=160, SDR=11 | dn=14.5mm (afgerond 14.6mm zoals BerekeningHDD11) | BLOCKER |
| CALC-02 | Inwendige diameter | De=160, dn=14.6 | Di=130.8mm | HIGH |
| CALC-03 | Intreehoek naar % | 18° | 32% (tan(18°)×100 = 32.49 → 32%) | HIGH |
| CALC-04 | Uittreehoek naar % | 22° | 40% (tan(22°)×100 = 40.40 → 40%) | HIGH |
| CALC-05 | Boorgat radius | De=160, factor=1.5 | Dg=240mm, r_boorgat=120mm | HIGH |
| CALC-06 | SDR→wanddikte klein project | De=110, SDR=11 | dn=10.0mm (3D25V631 referentie) | MEDIUM |

---

### 5.4 Coördinaten (RD↔WGS84)

Referentie: GPS punten HDD11 uit `3D25V700-11-rev.1-A2Z4.pdf`

| Code | Test | RD input | Verwacht WGS84 | Tolerantie | Fout = |
|---|---|---|---|---|---|
| COORD-01 | Punt A HDD11 | (103896.9, 489289.5) | (52.3875°N, 4.6358°O) | < 1cm | BLOCKER |
| COORD-02 | Punt B HDD11 | (104118.8, 489243.7) | correcte WGS84 | < 1cm | BLOCKER |
| COORD-03 | Punt Tv1 HDD11 | (103916.4, 489284.1) | correcte WGS84 | < 1cm | HIGH |
| COORD-04 | Punt Tv1 HDD28 | (105315.0, 498805.0) | correcte WGS84 | < 1cm | HIGH |
| COORD-05 | Round-trip RD→WGS84→RD | (103896.9, 489289.5) | Afwijking < 0.01m | HIGH |

---

### 5.5 Formuliervalidatie

| Code | Test | Actie | Verwacht |
|---|---|---|---|
| FORM-01 | Project naam verplicht | POST /projecten/nieuw zonder naam | 422 of formulierfout zichtbaar |
| FORM-02 | SDR validatie | SDR=0 | Validatiefout |
| FORM-03 | De_mm validatie | De_mm=-10 | Validatiefout |
| FORM-04 | RD_x buiten NL | RD_x=0, RD_y=0 | Waarschuwing of fout |
| FORM-05 | Project aanmaken happy path | Alle velden correct | 200 redirect naar detail |

---

### 5.6 Eisenprofielen (seed data)

| Code | Test | Verwacht |
|---|---|---|
| SEED-01 | 5 eisenprofielen aanwezig na seed | RWS, Waterschap, Provincie, Gemeente, ProRail |
| SEED-02 | RWS waarden | dekking_weg=3.0m, dekking_water=5.0m, Rmin=150m |
| SEED-03 | Waterschap waarden | dekking_weg=5.0m, dekking_water=10.0m, Rmin=200m |
| SEED-04 | Seed twee keer draaien | Geen duplicaten, geen errors (idempotent) |

---

## 6. Referentiedata voor validatie

Alle bestanden staan in `docs/input_data_14maart/`:

| Bestand | Gebruik in tests |
|---|---|
| `BerekeningHDD11.pdf` | CALC-01 t/m 06: leidingparameters en berekeningen valideren |
| `3D25V700-11-rev.1-A2Z4.pdf` | PDF-03 t/m 11: referentietekening voor layout en inhoud |
| `3D26V810-28 HDD28 Velsen-Noord.dxf` | DXF-01 t/m 16: laagnamen en structuur valideren |
| `CPT000000026582_IMBRO_A.gef` | GEF parsing tests (backlog 9) |
| `Levering_25O0136974_1.zip` | KLIC parsing tests (backlog 1) |
| `Logo3D.jpg` | PDF-11: logo aanwezig in output |

**Aanvullende werkplan stijlreferenties** (`docs/Input_data_16maart/werkplannen/`):

| Bestand | Gebruik in tests |
|---|---|
| `3D24V473 Werkplan - Diemen, Muiderstraatweg.pdf` | Werkplan structuur Formaat A (oud), RWS-beheerder-alinea |
| `3D25V679 HDD1 Werkplan - Ouderkerk aan de Amstel.pdf` | Werkplan structuur Formaat B (huidig), NURijnland-boilerplate |
| `3D25V679 HDD8&9 Werkplan - Ouderkerk Korte Dwarsweg.pdf` | Werkplan Formaat B, waterkering-sectie |
| `3D25V638 Werkplan - Velsen-Noord, Rijksweg A22.pdf` | Werkplan Formaat B, CKB ST-B, 3-buis bundel, EV aanwezig |
| `Order overview shared with Ello.xlsx` | Projectregistratie-structuur, EV-tracking, klantcodes seed-data |

**Correctie werkplan testcase (TC-4.3.A):** 6 hoofdstukken + bijlagen A-G (niet 7 hoofdstukken).

**HDD11 leidingparameters (testinput):**
```
naam:           HDD11 Haarlem Kennemerplein
ordernummer:    3D25V700
opdrachtgever:  Liander / DMMB
De_mm:          160
SDR:            11
dn_mm:          14.6  (verwacht bij SDR=11)
medium:         Drukloos
Db_mm:          60
Dp_mm:          110
Dg_mm:          240
intreehoek:     18°  (= 32%)
uittreehoek:    22°  (= 40%)
MVin_NAP:       +1.01m
MVuit_NAP:      +1.27m
L_totaal:       226.58m
```

**GPS punten HDD11 (verwachte output in PDF en DXF):**
```
A:   103896.9  489289.5
Tv1: 103916.4  489284.1
Tv2: 103934.3  489279.1
Th1: 103947.3  489275.5
Th2: 103960.8  489272.4
Tv3: 104079.7  489250.8
Tv4: 104109.2  489245.5
B:   104118.8  489243.7
```

---

## 7. Go / No-Go criteria HDD-platform

### NO-GO (release geblokkeerd)

- DXF niet te openen (ezdxf parse error)
- Laagnaam afwijkt van NLCS referentie (DXF-04 t/m DXF-11)
- GPS punten afwijken meer dan 1cm van invoer (COORD-01/02)
- PDF niet gegenereerd of lege pagina (PDF-01/02)
- Auth: testgebruiker actief in `ENV=production` (AUTH-kritisch)
- Auth: directe URL toegankelijk zonder credentials (401 ontbreekt)
- SDR→wanddikte berekening fout (CALC-01)

### CONDITIONAL GO (met expliciete goedkeuring Ello)

- Titelblok layout afwijkt visueel (geen data-fout)
- Doorsnede symbool iets verschoven (< 5mm op schaal)
- KLIC-disclaimer tekst iets anders geformuleerd
- Logo kleiner of groter dan referentie

### GO

- Alle BLOCKER testcases groen
- Alle HIGH testcases groen of CONDITIONAL GO geaccepteerd
- Auth correct: martien/visser werkt, test NIET in productie
- DXF download en PDF download responses correct
- Geen server errors (500) in logs

---

## 8. Regressieset — altijd draaien

Na **elke** backlog oplevering altijd de volledige regressieset draaien:

```
Groep A — Auth (altijd)
  AUTH-01  GET / zonder credentials → 401
  AUTH-02  GET / met martien/wachtwoord → 200
  AUTH-03  GET / met fout wachtwoord → 401
  AUTH-04  ENV=production: testgebruiker → 401

Groep B — Project CRUD (altijd)
  PROJ-01  Project aanmaken HDD11 parameters → 200
  PROJ-02  SDR=11, De=160 → dn=14.6mm
  PROJ-03  Projectenlijst toont nieuw project

Groep C — DXF output (altijd, zwaarste gewicht)
  DXF-01 t/m DXF-16 (zie sectie 5.1)

Groep D — PDF output (altijd)
  PDF-01 t/m PDF-12 (zie sectie 5.2)

Groep E — Coördinaten (altijd)
  COORD-01 t/m COORD-05 (zie sectie 5.4)

Groep F — Berekeningen (altijd)
  CALC-01 t/m CALC-06 (zie sectie 5.3)
```

Groep G — EV-detectie (na backlog 1 uitbreiding)
  EV-01  KLIC met EV-leiding → ev_verplicht=True, contactgegevens niet leeg
  EV-02  Brondata-pagina met EV → WAARSCHUWING-blok zichtbaar
  EV-03  Brondata-pagina zonder EV → geen WAARSCHUWING-blok

Groep H — EV-zone DXF (na backlog 2b)
  EVDXF-01  DXF met EV-leidingen → laag "EV-ZONE" aanwezig met entiteiten
  EVDXF-04  Review-pagina met EV → rood WAARSCHUWING-blok + contactgegevens
  EVDXF-07  DXF regressie → alle bestaande lagen nog aanwezig na toevoeging EV-ZONE

Nieuwe modules voegen een nieuwe groep toe aan de regressieset. Bestaande groepen worden nooit verkleind.

---

## 9. Testomgeving

**Lokaal (development):**
```bash
# Start
uvicorn app.main:app --reload

# Verifieer ENV
curl -u test:test123 http://localhost:8000/
# → 200 als ENV=development, 401 als ENV=production
```

**Productie:**
```
URL:   https://hdd.inodus.nl
Auth:  martien of visser (wachtwoorden via Railway dashboard)
Let op: geen destructive tests, geen testdata aanmaken die Martien ziet
```

**Testdata aanmaken (lokaal):**
```bash
python scripts/init_db.py    # DB aanmaken
python scripts/seed.py       # workspace + eisenprofielen
# Dan via browser inloggen als test/test123 en HDD11 project aanmaken
```

---

## 10. Scope out (wat NIET getest wordt)

- Performance / load testing — 2 gebruikers, geen concurrency-issues verwacht
- Accessibility — geen publieke website, 2 professionele gebruikers
- Cross-browser — Martien en Visser gebruiken Chrome / Edge
- Mobile responsive — desktopapplicatie voor engineers
- SEO — geen publieke URL
- KLIC GML parsing (backlog 1) — niet in skeleton
- AHN5 API (backlog 2) — niet in skeleton
- Google Drive API — niet in skeleton

---

## 11. Backlog-specifieke testuitbreidingen

Bij elke backlog oplevering wordt dit document uitgebreid met een nieuwe sectie. Template:

```markdown
### Backlog [nummer] — [naam]

**Nieuwe testcases:**
| Code | Test | Input | Verwacht | Fout = |
|---|---|---|---|---|
| [MODULE]-01 | ... | ... | ... | BLOCKER/HIGH/MEDIUM |

**Regressie:** voeg toe aan sectie 8 Groep [letter].

**Specifieke testdata:** [bestandsnaam uit docs/input_data_14maart/]

**Go/No-Go aanvulling:** [eventuele nieuwe NO-GO criteria]
```

---

### Backlog 1 uitbreiding — EV-detectie, materiaalregel, BOB tekstveld

**Nieuwe testcases:**

| Code | Test | Input | Verwacht | Fout = |
|---|---|---|---|---|
| EV-01 | KLIC met EV-leiding → KLICLeiding records | Mock EV-leiding | `ev_verplicht=True`, `ev_contactgegevens` niet leeg | BLOCKER |
| EV-02 | Brondata-pagina met EV-leidingen | Project met EV | WAARSCHUWING-blok zichtbaar, bevat "EV" | BLOCKER |
| EV-03 | Brondata-pagina zonder EV-leidingen | Project zonder EV | Geen WAARSCHUWING-blok | HIGH |
| MAT-01 | Leiding materiaal PE100 | Mock leiding | `sleufloze_techniek=True` | HIGH |
| MAT-02 | Leiding materiaal PVC | Mock leiding | `sleufloze_techniek=False`, `mogelijk_sleufloze=False` | HIGH |
| MAT-03 | Leiding materiaal Staal | Mock leiding | `sleufloze_techniek=False`, `mogelijk_sleufloze=True` | MEDIUM |
| BOB-01 | Label "+/-2.58 -NAP" | Mock tekstveld | `diepte_m=2.58`, `diepte_bron="tekstveld_onzeker"` | MEDIUM |
| BOB-02 | Label zonder dieptepatroon | Mock tekstveld | `diepte_m=None`, geen crash | HIGH |
| BOB-03 | Leiding met gestructureerde diepte + label met diepte | Mock | Gestructureerde diepte wint, `diepte_bron` ongewijzigd | HIGH |

**Regressie:** voeg EV-01 t/m EV-03 toe aan sectie 8 als Groep G.

**Go/No-Go aanvulling:**
- NO-GO: EV-leidingen aanwezig maar geen WAARSCHUWING getoond op brondata-pagina
- NO-GO: `ev_verplicht=True` maar `ev_contactgegevens` leeg

---

### Backlog 2b — EV-zone DXF rendering

**Nieuwe testcases:**

| Code | Test | Input | Verwacht | Fout = |
|---|---|---|---|---|
| EVDXF-01 | DXF met EV-leidingen | Project met EV | Laag "EV-ZONE" aanwezig, bevat entiteiten | BLOCKER |
| EVDXF-02 | DXF zonder EV-leidingen | Project zonder EV | Laag "EV-ZONE" aanwezig maar leeg | HIGH |
| EVDXF-03 | DXF EV-ZONE laageigenschappen | Project met EV | kleur=1 (rood), lijntype="DASHDOT" | HIGH |
| EVDXF-04 | Review-pagina met EV | Project met EV | Rood WAARSCHUWING-blok + contactgegevens zichtbaar | BLOCKER |
| EVDXF-05 | Review-pagina zonder EV | Project zonder EV | Geen WAARSCHUWING-blok | HIGH |
| EVDXF-06 | PDF met EV-leidingen | Project met EV | Tekst "EV-ZONE" aanwezig in PDF | HIGH |
| EVDXF-07 | DXF regressie na EV-ZONE toevoeging | Bestaand project | Alle bestaande lagen nog aanwezig (DXF-04 t/m DXF-11) | BLOCKER |

**Regressie:** voeg EVDXF-01 en EVDXF-04 toe aan sectie 8 als Groep H.

**Go/No-Go aanvulling:**
- NO-GO: DXF met EV-leidingen maar laag "EV-ZONE" ontbreekt of leeg
- NO-GO: Review-pagina met EV maar geen WAARSCHUWING-blok zichtbaar

---

*TEST_CONTEXT_HDD.md — HDD Ontwerp Platform | Inodus*
*Gebruik altijd samen met TEST_AGENT_v2.md*
*Versie 1.1 — Walking Skeleton + Backlog 1 EV/Materiaal + Backlog 2b EV-zone*
