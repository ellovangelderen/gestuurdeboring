# Backlog — Excel Analyse: Martien's werkboek vs. Platform
**Datum: 18 maart 2026**
**Bron: Analyse van Martien's Excel werkboek (alle sheets)**

---

## Samenvatting

Martien's Excel bevat ~2300 rijen aan berekeningen verdeeld over 8+ sheets. Het platform heeft de kernfuncties al, maar de Excel bevat extra parameters en berekeningen die impact hebben op de nauwkeurigheid van tekeningen en berekeningen.

Hieronder staan alle gevonden gaps, gecategoriseerd als:
- **BESLISSING** — keuze nodig van Martien (conflict met huidige aanpak)
- **VERRIJKING** — extra data die we direct kunnen verwerken
- **TOEKOMSTIG** — nice-to-have, geen prioriteit

---

## BESLISSINGEN (voor Martien)

### B1 — Rv per segment apart vs. één Rv

| | Excel | Platform |
|---|---|---|
| **Nu** | Rv_intrede, Rv_horizontaal, Rv_uittrede apart instelbaar | Één Rv = 1200 × De voor alles |
| **Impact** | Profiel geometrie, DXF, PDF lengteprofiel | Kleine afwijking bij asymmetrische boringen |
| **Vraag** | Gebruikt Martien in de praktijk verschillende Rv per segment, of is 1200×De altijd voldoende? |

### B2 — Bundelfactor berekening Dg

| | Excel | Platform |
|---|---|---|
| **Nu** | Dg = bundelfactor × De × ruimfactor. Bundelfactor: 1×=1.0, 2×=2.0, 3×=2.15, 4×=2.73 | Dg is handmatig invoerveld (default 240mm) |
| **Impact** | Doorsnede boorgat op tekening, DXF BOORGAT cirkels, ruimfactoren | Bij bundel-boringen (2+ buizen) klopt Dg niet als handmatig ingevuld |
| **Vraag** | Willen we Dg automatisch berekenen uit aantal buizen + De? Of blijft handmatig OK? |

### B3 — Ruimfactoren per boringtype

| | Excel | Platform |
|---|---|---|
| **Nu** | Enkelbuis: 1.5, Bundel: 1.2, Boogzinker: 1.1 | Geen ruimfactor — Dg is vast |
| **Impact** | Boorgat diameter op tekening | Boogzinker boorgat is nu te groot (1.5 ipv 1.1) |
| **Vraag** | Moeten we ruimfactor automatisch toepassen op basis van boringtype? |

### B4 — Boormachine selectie

| | Excel | Platform |
|---|---|---|
| **Nu** | VermeerD40, Pers + tonnages, INSERT blok in DXF | Geen machineselectie, INSERT blok hardcoded |
| **Impact** | DXF bevat correct machineblok, tonnage bepaalt CKB-categorie | Minimaal — alleen visueel in DXF |
| **Vraag** | Is machineselectie nodig in het platform, of is dit AutoCAD-handwerk? |

### B5 — Type "W" (werkplan) als boringtype

| | Excel | Platform |
|---|---|---|
| **Nu** | W is een apart type naast B/N/Z/C in de orderlijst | W bestaat niet als boringtype, werkplan is een apart document |
| **Impact** | Bij migratie: sommige orders hebben "W,1" als aparte rij | Orders met alleen werkplan (geen tekening) |
| **Vraag** | Moet W een 5e boringtype worden, of is werkplan op order-niveau voldoende? |

### B6 — Standaard K&L indicatieve dieptes

| | Excel | Platform |
|---|---|---|
| **Nu** | LD-GAS: -0.70m, HD-GAS: -1.00m, BGI: -1.00m als fallback | Conflictcheck meldt "diepte onbekend" zonder fallback |
| **Impact** | Conflictcheck — met standaard dieptes kunnen we wél een afstandsberekening doen ipv alleen "onbekend" | Significante verbetering conflictcheck |
| **Vraag** | Mogen we standaard dieptes gebruiken als KLIC geen diepte levert? Met waarschuwing "indicatief"? |

---

## VERRIJKINGEN (direct verwerken)

### V1 — Klantcodes uitbreiden (18 → was 16)

Toevoegen aan `klantcodes.py`:

| Code | Naam | Akkoord contact |
|---|---|---|
| VB | Verbree Boogzinkers | M. Verbree |
| HV | Hogenhout | A. Hogenhout |
| LI | Liander | W. Meijer |
| DX | Direxta | S. Battaioui |
| KB | Kappert Boogzinkers | A. Kappert |
| VT | VTV | — |
| NV | NeijhofVisser | B. Neijhof |
| RV | RovoR | R. Bláha |
| CI | Circet Nederland | T. v. Rooten |
| AR | Artemis | E. Chatzidaki |
| EL | Eljes | — |
| VG | Van Gelder | — |
| VW | VWTelecom | M. v. Donselaar |
| BA | BAM Infra | — |

**Let op:** sommige codes conflicteren mogelijk met bestaande (VB, VG, KB al aanwezig). Codes bevestigen met Martien.

### V2 — Boogzinker standen hulptabel

Excel bevat een complete hulptabel: alle 10 standen × alle booghoeken met berekende lengtes. Dit kunnen we gebruiken voor validatie van `bereken_boorprofiel_z()`.

### V3 — Opdrachtgever/aannemer keten

Excel: "Opdrachtgever selectie (1 of 2 — titelblok kiezen)". Soms staat het boorbedrijf als opdrachtgever, soms de aannemer. Dit bepaalt welke logo's op het titelblok staan.

**Impact:** PDF titelblok logo selectie. Nu tonen we klantcode-logo + GBT. Moet er een 3e logo (aannemer) bij?

### V4 — EV-partijen handmatig invoerbaar

Excel: EV1-EV5 als handmatige kolommen (bijv. "Liander: HS", "PWN: water"). Platform extraheert EV alleen uit KLIC parser.

**Impact:** Bij orders zonder KLIC upload (of als EV handmatig bekend is) kan Martien nu geen EV invoeren.

### V5 — Email-contacten per EV-partij

Excel: Email1-6 kolommen gekoppeld aan EV-partijen. Platform heeft `EmailContact` model maar niet gekoppeld aan specifieke EV.

### V6 — PDOK URL met specifieke lagen

Excel: PDOK URLs bevatten uitgebreide laagconfiguratie (GWSW, BRO lagen). Platform genereert simpele URL.

**Impact:** Bij migratie de oorspronkelijke PDOK URL overnemen.

---

## TOEKOMSTIGE BACKLOG ITEMS

### T1 — CSV GPS export (boorlijn per meter)

Excel genereert 880 punten (1 per meter) voor de volledige boorlijn. Dit gaat naar AutoCAD als CSV-import.

**Impact:** Workflow verbetering — Martien hoeft niet meer handmatig te exporteren.
**Effort:** Klein — bereken punten langs het 5-segment profiel, exporteer als CSV.

### T2 — AutoCAD script (.scr) generator

Excel genereert AutoCAD commando's:
```
_LAYER _Set BOORLIJN ;
_PLINE x1,y1 x2,y2 ...
_INSERT VermeerD40 0,0
```

**Impact:** Grote tijdsbesparing als Martien de .scr kan laden ipv handmatig tekenen.
**Effort:** Middel — templategebaseerd, vergelijkbaar met DXF generator.

### T3 — Horizontale bocht berekening

Excel TOOLS sheet: alternatieve hellingshoek, max horizontale bocht, radius check.

**Impact:** Ontwerpvalidatie — waarschuwen als bocht te scherp is.
**Effort:** Klein — wiskundige check toevoegen.

### T4 — BGT/KLIC/DKK laadscripts

Excel genereert InfraCAD Map commando's voor het laden van ondergronddata in AutoCAD.

**Impact:** Workflow — maar ons platform vervangt dit al grotendeels met de webkaart + KLIC parser.
**Effort:** Klein maar niche.

### T5 — Contactpersonen via klantbestanden

Excel: `VERT.ZOEKEN` naar CC-MASTER.xlsm, KB-MASTER.xlsm etc. voor contactpersonen per klant.

**Impact:** Al deels opgelost met `klantcodes.py` akkoord_contact lookup.

---

## Impact op bestaande features

### PDF lengteprofiel
- **B1 (Rv per segment)** → ja, impact op curve-vorm in profiel
- **B2 (bundelfactor)** → ja, impact op doorsnede boorgat tekening
- **B3 (ruimfactor)** → ja, impact op Dg label
- **B6 (standaard dieptes)** → nee, alleen conflictcheck

### DXF tekening
- **B4 (boormachine)** → INSERT blok in bovenaanzicht
- **B2 (bundelfactor)** → BOORGAT cirkel diameters
- **T2 (AutoCAD script)** → alternatief voor DXF

### Conflictcheck
- **B6 (standaard dieptes)** → significante verbetering — van "onbekend" naar "indicatief -0.70m"

### Migratie (GSheets → Platform)
- **V1 (klantcodes)** → nodig voor import
- **V4 (EV handmatig)** → nodig voor orders zonder KLIC
- **V6 (PDOK URLs)** → URLs overnemen

---

## Volgende stap

1. **Beslissingen B1-B6 voorleggen aan Martien** bij eerstvolgende bespreking
2. **Verrijkingen V1-V6 direct verwerken** zodra klantcodes bevestigd
3. **Toekomstige items T1-T5** op de backlog zetten, prioriteren met Martien
