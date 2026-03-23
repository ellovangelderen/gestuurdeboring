# BACKLOG v6 — HDD Ontwerp Platform
**Versie 6.0 | 2026-03-17**
**Walking Skeleton: AFGEROND (40/40 tests groen)**

---

## Prioriteitsbepaling
Volgorde bepaald op basis van:
- Martien's feedback (17 maart 2026): werkplan generator = hoogste ROI
- Ello's beslissingen: platform = bron, cockpit UI, migratie alles
- Architectuurafhankelijkheden: datamodel refactor moet eerst

---

### Backlog 0 — Datamodel refactor: Order → Boring[]

**Waarde:** FUNDAMENT
**Vervangt:** Huidige 1-project=1-boring model
**Afhankelijk van:** Walking Skeleton (done)
**Status:** Todo

**Scope:**
- Rename Project → Order
- Nieuw Boring model met volgnummer + type (B/N/Z/C)
- KLICUpload verhuist naar Order-niveau
- Nieuwe koppeltabel BoringKLIC (many-to-many met versie)
- KLIC versioning (meldingnummer + versie)
- Tekenaar veld op Order (default "martien")
- EVPartij en EmailContact tabellen
- Status enum (6 waarden)
- Vergunning veld (P/W/R/-)
- Prio boolean + notitie veld
- Alembic migratie van bestaande data
- Alle routes aanpassen
- Alle templates aanpassen
- Alle tests aanpassen

**Acceptatiecriteria:**
- Order aanmaken met meerdere boringen
- Boring heeft type B/N/Z/C
- KLIC upload op order-niveau, koppelbaar aan specifieke boring
- Bestaande testdata (HDD11) werkt nog na migratie
- Alle 40 skeleton tests passen of zijn aangepast en groen

**Testcases (eerste opzet):**
```
TC-datamodel-A  Order aanmaken met 3 boringen (B, N, Z)
TC-datamodel-B  KLIC upload koppelen aan specifieke boring
TC-datamodel-C  Migratie HDD11 → data intact na migratie
TC-datamodel-D  Alle 40 skeleton tests groen na migratie
```

---

### Backlog 1 — Werkplan generator (standalone, Claude API)

**Waarde:** ★★★★★ (hoogste ROI Martien, bespaart ~2u per werkplan)
**Vervangt:** Handmatig schrijven met ChatGPT/NotebookLM
**Afhankelijk van:** Geen (kan parallel aan item 0)
**Status:** Todo

**Scope:**
- Claude API integratie (Anthropic SDK)
- 6 hoofdstukken + bijlagen A-G
- Boilerplate secties: template-gebaseerd, geen AI
- Projectspecifieke secties: Claude API (2.1 Locatie, 2.2 Historie, 2.3 K&L, 2.3 Geotechniek)
- Formaat B (huidig, niet Formaat A)
- CKB-categorie op basis van trekkracht (ST-A/B/C/D)
- NURijnland herbruikbaar blok
- PDF output (WeasyPrint)
- Stijlreferenties: 3D25V679 HDD1 + 3D25V638 (meest recent)

**Acceptatiecriteria:**
- Werkplan HDD11 gegenereerd met alle 6 hoofdstukken
- Boilerplate secties identiek aan referentie
- CKB-tabel correct op basis van Ttot
- PDF output zonder errors

**Testcases (eerste opzet):**
```
TC-werkplan-A  HDD11 → 6 hoofdstukken + bijlagen A-G aanwezig
TC-werkplan-B  Boilerplate 3.2.1-3.2.4 identiek aan referentie
TC-werkplan-C  CKB ST-B bij Ttot=30106N
TC-werkplan-D  PDF generatie zonder errors
```

---

### Backlog 2 — Cockpit UI

**Waarde:** ★★★★★ (Ello: "cockpit = startpagina")
**Vervangt:** Lineaire stap-voor-stap workflow
**Afhankelijk van:** Backlog 0 (datamodel)
**Status:** Todo

**Scope:**
- Ordertabel als landing page na login
- Stats-balk: over deadline, urgent, in uitvoering, wacht akkoord, totaal
- Quick-actions per order: tekening, berekening, werkplan, KLIC, kaart
- Filteren: alles, actief, wacht akkoord, geleverd, mijn orders
- Zoeken op ordernummer, locatie, klant
- Sorteren op deadline, datum, klant, status
- Per order: boringen tonen met type-badges
- EV-waarschuwing prominent
- PRIO-vlag
- Tekenaar avatar
- Export naar CSV
- Kaart-klik coördinateninvoer: klik op kaart → RD-coördinaten (primaire invoermethode)
- Kaartlagen: BGT, DKK, KLIC, luchtfoto als schakelbare lagen
- Handmatige RD-invoer als fallback

**Acceptatiecriteria:**
- Na login → cockpit als eerste scherm
- Alle orders zichtbaar met correcte status
- Één klik naar tekening/berekening/werkplan/KLIC/kaart per boring
- Zoeken en filteren werkt
- Export genereert valide CSV

**Testcases (eerste opzet):**
```
TC-cockpit-A  Na login → cockpit als eerste scherm
TC-cockpit-B  Ordertabel toont alle orders met correcte status
TC-cockpit-C  Quick-action tekening → juiste boring geopend
TC-cockpit-D  Filter "wacht akkoord" → alleen relevante orders
TC-cockpit-E  CSV export bevat alle zichtbare orders
```

---

### Backlog 3 — KLIC IMKL 2.0 parser

**Waarde:** KERN
**Vervangt:** Placeholder leidingen
**Afhankelijk van:** Backlog 0 (datamodel)
**Status:** Todo

**Scope:**
- IMKL 2.0 XML parsing
- Twee KLIC formaten ondersteunen: ZIP met meerdere XMLs (Formaat A) én enkel GML V2 bestand (Formaat B)
- Leidingen extraheren met beheerder, type, geometrie
- Diepte uit gestructureerde en vrije tekstvelden
- Sleufloze techniek detectie (materiaalregel + bijlage-heuristiek)
- EV-markering + contactgegevens
- DXF-lagen toewijzen per leidingtype

**Acceptatiecriteria:**
- HDD11 KLIC → 11 beheerders, 1127 leidingen
- KL1049 Reggefiber → sleufloze techniek gedetecteerd
- EV-leidingen gemarkeerd met contactgegevens

**Testcases (eerste opzet):**
```
TC-klic-A  HDD11 ZIP → 11 beheerders, 1127 leidingen
TC-klic-B  KL1049 → PDF-bijlage boogzinker gedetecteerd
TC-klic-C  EV-leidingen → ev_verplicht=True + contactgegevens
TC-klic-D  Diepte uit tekstveld → diepte_bron="tekstveld_onzeker"
TC-klic-E  IJmuiden GML V2 (enkel bestand) → 9 beheerders, 1952 features
TC-klic-F  HDD11 ZIP (meerdere XMLs) → 11 beheerders, 1127 leidingen
```

---

### Backlog 3b — EV-zone DXF rendering

**Waarde:** ★★★★★ WETTELIJK
**Vervangt:** EV-waarschuwing handmatig
**Afhankelijk van:** Backlog 3 (KLIC parser)
**Status:** Todo

**Scope:**
- EV-zone als DXF-laag + PDF-situatietekening + prominente waarschuwing

**Acceptatiecriteria:**
- EV-zone zichtbaar als aparte DXF-laag
- PDF-situatietekening bevat EV-zone
- Prominente waarschuwing in UI bij EV-leidingen

**Testcases (eerste opzet):**
```
TC-evzone-A  EV-leiding → DXF bevat EV-zone laag
TC-evzone-B  PDF-situatietekening toont EV-zone correct
```

---

### Backlog 4 — Wekelijkse statusmail

**Waarde:** ★★★★ (bread & butter)
**Vervangt:** Handmatig bellen/mailen
**Afhankelijk van:** Backlog 2 (cockpit, orderstatus)
**Status:** Todo

**Scope:**
- Per opdrachtgever: overzicht openstaande akkoorden
- Geleverde orders zonder bevestiging
- Template-gebaseerde email (Jinja2)
- Automatisch elke maandag OF handmatig triggeren
- Preview per klant voordat je verstuurt
- Reply-to: Martien's email

**Acceptatiecriteria:**
- Email per opdrachtgever met correcte orders
- Preview toont juiste data
- Email verzonden via SMTP

**Testcases (eerste opzet):**
```
TC-mail-A  3D-Drilling → 2 openstaande akkoorden in mail
TC-mail-B  Preview toont correcte orders per klant
TC-mail-C  Handmatig trigger → mail verstuurd
```

---

### Backlog 5 — GWSW riool BOB + gemeente-mail

**Waarde:** ★★★★
**Vervangt:** Handmatig mailen
**Afhankelijk van:** Backlog 3
**Status:** Todo

**Scope:**
- GWSW riool BOB data ophalen
- Gemeente-mail automatisch genereren

**Acceptatiecriteria:**
- BOB-data correct opgehaald voor projectlocatie
- Gemeente-mail gegenereerd met juiste gegevens

**Testcases (eerste opzet):**
```
TC-gwsw-A  Projectlocatie → BOB-data opgehaald
TC-gwsw-B  Gemeente-mail gegenereerd met correcte BOB-gegevens
```

---

### Backlog 6 — Sleufloze leidingen detectie

**Waarde:** ★★★★
**Vervangt:** Handmatig uitzoeken
**Afhankelijk van:** Backlog 3
**Status:** Todo

**Scope:**
- Sleufloze leidingen detecteren uit KLIC-data
- Markering en rapportage in UI

**Acceptatiecriteria:**
- Sleufloze leidingen correct gedetecteerd
- Duidelijke markering in overzicht

**Testcases (eerste opzet):**
```
TC-sleufloos-A  KLIC met sleufloze leiding → correct gedetecteerd
TC-sleufloos-B  Markering zichtbaar in leidingoverzicht
```

---

### Backlog 7 — Conflictcheck K&L 3D

**Waarde:** KERN
**Vervangt:** Altijd WAARSCHUWING
**Afhankelijk van:** Backlog 3
**Status:** Todo

**Scope:**
- 3D conflictcheck tussen boortracé en kabels & leidingen
- Automatische waarschuwing bij te kleine afstand

**Acceptatiecriteria:**
- Conflicten correct gedetecteerd in 3D
- Waarschuwing met specifieke leiding en afstand

**Testcases (eerste opzet):**
```
TC-conflict-A  Boortracé kruist leiding op <0.5m → conflict gedetecteerd
TC-conflict-B  Geen conflict → groene status
```

---

### Backlog 8 — Boogzinker profiel (type Z)

**Waarde:** ★★★★ ("we maken er best veel")
**Vervangt:** Handmatig tekenen
**Afhankelijk van:** Backlog 0 (datamodel)
**Status:** Todo

**Scope:**
- Boogzinker profielgeometrie: 1 segment, 1 vaste boog
- Parameters: booghoek (5/7.5/10°) + stand (1-10)
- Platform berekent lengte automatisch
- DXF: 1 ARC, geen Rv-cirkels
- PDF: vereenvoudigd profiel
- Conditionele UI: bij type Z andere invoervelden dan B/N

**Acceptatiecriteria:**
- Type Z boring aanmaken met booghoek en stand
- Lengte automatisch berekend
- DXF bevat 1 ARC op BOORLIJN, geen horizontaal segment

**Testcases (eerste opzet):**
```
TC-bz-A  Type Z boring → booghoek + stand invoervelden
TC-bz-B  Booghoek 10° stand 5 → correcte lengte berekend
TC-bz-C  DXF → 1 ARC op BOORLIJN, geen horizontaal segment
```

---

### Backlog 9 — Boorprofiel geometrie ARCs

**Waarde:** KERN
**Vervangt:** Handmatige hoeken
**Afhankelijk van:** Backlog 0
**Status:** Todo

**Scope:**
- Boorprofiel geometrie met ARC-segmenten
- Automatische hoekberekening
- Grafisch lengteprofiel in DXF als aparte view
- Grafisch lengteprofiel in PDF (NAP, schaal 1:250)
- Bovenaanzicht in PDF (schaal 1:2000 of 1:4000)
- Situatietekening met K&L in PDF (schaal 1:250)

**Acceptatiecriteria:**
- Boorprofiel correct gegenereerd met ARCs
- Hoeken automatisch berekend

**Testcases (eerste opzet):**
```
TC-profiel-A  Boorprofiel → ARCs correct geplaatst
TC-profiel-B  Hoekberekening klopt met referentie
```

---

### Backlog 10 — AHN5 maaiveld + PDOK waterschap URL

**Waarde:** KERN
**Vervangt:** Handmatig MVin/MVuit + knip/plak URLs
**Afhankelijk van:** Backlog 0
**Status:** Todo

**Scope:**
- AHN5 maaiveld ophalen voor in- en uittredepunt
- PDOK waterschap URL automatisch genereren

**Acceptatiecriteria:**
- MVin/MVuit automatisch opgehaald uit AHN5
- Waterschap URL correct gegenereerd

**Testcases (eerste opzet):**
```
TC-ahn5-A  Coördinaten → MVin/MVuit uit AHN5
TC-ahn5-B  Locatie → correcte waterschap PDOK URL
```

---

### Backlog 11 — Topotijdreis + wijzigingsdetectie

**Waarde:** ★★★★
**Vervangt:** Handmatige controle
**Afhankelijk van:** Backlog 0
**Status:** Todo

**Scope:**
- Topotijdreis integratie voor historische kaartdata
- Automatische wijzigingsdetectie op projectlocatie

**Acceptatiecriteria:**
- Historische kaartdata beschikbaar per locatie
- Wijzigingen gedetecteerd en gerapporteerd

**Testcases (eerste opzet):**
```
TC-topo-A  Locatie → historische kaarten opgehaald
TC-topo-B  Wijziging gedetecteerd → melding in UI
```

---

### Backlog 12 — Tracévarianten vergelijken

**Waarde:** ★★★★
**Vervangt:** Telefonisch overleg
**Afhankelijk van:** Backlog 9
**Status:** Todo

**Scope:**
- Meerdere tracévarianten naast elkaar vergelijken
- Visuele en numerieke vergelijking

**Acceptatiecriteria:**
- Meerdere varianten aanmaken per boring
- Vergelijking toont verschillen in lengte, diepte, conflicten

**Testcases (eerste opzet):**
```
TC-trace-A  2 varianten → vergelijkingstabel met delta's
TC-trace-B  Visuele overlay van varianten in kaart
```

---

### Backlog 13 — SnelStart koppeling

**Waarde:** ★★★ (bread & butter)
**Vervangt:** Handmatig factureren
**Afhankelijk van:** Backlog 2 (cockpit)
**Status:** Todo

**Scope:**
- SnelStart API integratie
- Facturatie vanuit platform

**Acceptatiecriteria:**
- Order → factuur aanmaken in SnelStart
- Factuurnummer teruggekoppeld naar platform

**Testcases (eerste opzet):**
```
TC-snelstart-A  Order geleverd → factuur aangemaakt in SnelStart
TC-snelstart-B  Factuurnummer zichtbaar in cockpit
```

---

### Backlog 14 — Vergunningscheck omgevingswet

**Waarde:** ★★★
**Vervangt:** Handmatig uitzoeken
**Afhankelijk van:** Backlog 0
**Status:** Todo

**Scope:**
- Automatische vergunningscheck op basis van locatie en omgevingswet
- Vergunning status (P/W/R/-) bepalen

**Acceptatiecriteria:**
- Locatie → vergunningsvereisten automatisch bepaald
- Status correct ingevuld

**Testcases (eerste opzet):**
```
TC-vergunning-A  Locatie in waterwingebied → vergunning P
TC-vergunning-B  Locatie zonder beperkingen → vergunning -
```

---

### Backlog 15 — Dinoloket sonderingen

**Waarde:** ★★★
**Vervangt:** Handmatig Dinoloket
**Afhankelijk van:** Backlog 0
**Status:** Todo

**Scope:**
- Dinoloket sonderingen ophalen voor projectlocatie
- Weergave in UI

**Acceptatiecriteria:**
- Sonderingen opgehaald voor locatie
- Data weergegeven in profiel

**Testcases (eerste opzet):**
```
TC-dino-A  Locatie → sonderingen opgehaald uit Dinoloket
TC-dino-B  Sondering weergegeven in boorprofiel
```

---

### Backlog 16 — GEF/CPT parser

**Waarde:** OPTIONEEL
**Vervangt:** Handmatig grondtype
**Afhankelijk van:** Backlog 15
**Status:** Todo

**Scope:**
- GEF/CPT bestanden parsen
- Grondtype classificatie

**Acceptatiecriteria:**
- GEF bestand correct geparsed
- Grondtype automatisch geclassificeerd

**Testcases (eerste opzet):**
```
TC-gef-A  GEF bestand → lagen correct geparsed
TC-gef-B  Grondtype classificatie klopt met handmatig
```

---

### Backlog 17 — NEN 3651 berekeningen

**Waarde:** OPTIONEEL
**Vervangt:** Handmatig Sigma
**Afhankelijk van:** Backlog 0
**Status:** Todo

**Scope:**
- NEN 3651 berekeningen implementeren
- Automatische spanningsberekening

**Acceptatiecriteria:**
- NEN 3651 berekening correct uitgevoerd
- Resultaten kloppen met handmatige Sigma-berekening

**Testcases (eerste opzet):**
```
TC-nen3651-A  Standaard casus → spanning klopt met Sigma
TC-nen3651-B  Grenswaarde overschreden → waarschuwing
```

---

### Backlog 18 — As-Built revisietekeningen

**Waarde:** ★★★ Martien
**Vervangt:** Handmatig revisie maken in AutoCAD
**Afhankelijk van:** Backlog 9 (boorprofiel geometrie)
**Status:** Todo

**Scope:**
- Werkelijke meetpunten invoeren na uitvoering boring
- Platform vergelijkt ontwerp vs. werkelijkheid
- Revisietekening (As-Built) genereren als DXF + PDF
- Revisienummer ophogen in bestandsnaam

**Acceptatiecriteria:**
- Werkelijke punten invoerbaar naast ontwerppunten
- As-Built DXF toont beide profielen (ontwerp + werkelijk)
- Revisienummer correct in bestandsnaam en titelblok

**Testcases (eerste opzet):**
```
TC-asbuilt-A  Werkelijke punten invoeren → opgeslagen naast ontwerp
TC-asbuilt-B  As-Built DXF → ontwerp (grijs) + werkelijk (kleur) zichtbaar
TC-asbuilt-C  Bestandsnaam = {ordernummer}-{volgnummer}-rev.2.dxf
```

---

## Afhankelijkheidsdiagram

```
Walking Skeleton (DONE)
  │
  ├─ [0] Datamodel refactor ─────┬─ [2] Cockpit UI ──── [4] Statusmail ── [13] SnelStart
  │                               ├─ [3] KLIC parser ─── [3b] EV-zone
  │                               │                  ├── [5] GWSW
  │                               │                  ├── [6] Sleufloze
  │                               │                  └── [7] Conflictcheck
  │                               ├─ [8] Boogzinker
  │                               ├─ [9] Boorprofiel ─┬─ [12] Tracévarianten
  │                               │                   └─ [18] As-Built
  │                               ├─ [10] AHN5 + PDOK
  │                               ├─ [11] Topotijdreis
  │                               ├─ [14] Vergunningscheck
  │                               ├─ [15] Dinoloket ── [16] GEF/CPT
  │                               └─ [17] NEN 3651
  │
  └─ [1] Werkplan generator (onafhankelijk, kan parallel)
```

---

## Nieuwe items (22 maart 2026)

### UX-1 — Handleiding / Help pagina
**Waarde:** Gebruiker kan zelfstandig werken zonder uitleg
**Prioriteit:** Middel
**Effort:** 2-3 uur
**Beschrijving:**
Aparte "Help" tab naast Orders en Admin. Server-side HTML (geen externe docs).
Secties:
1. Inloggen + uitloggen
2. Orders aanmaken + beheren
3. Boring invoeren (trace, maaiveld, doorsneden)
4. PDF + DXF downloaden
5. KLIC uploaden + conflictcheck
6. Admin panel (klanten, machines, eisenprofielen, gebruikers)

Doorzoekbaar via Ctrl+F (één pagina). Altijd up-to-date met huidige versie.

---

### OPS-1 — Automatische backup naar Cloudflare R2
**Waarde:** Data veiligheid — 357 orders op productie mogen niet verloren gaan
**Prioriteit:** Hoog
**Effort:** 2-3 uur
**Beschrijving:**
Dagelijkse automatische backup van SQLite DB + logo's naar Cloudflare R2 (S3-compatible).
- `boto3` library voor R2 API
- 3 env vars: `R2_ENDPOINT`, `R2_ACCESS_KEY`, `R2_SECRET_KEY`
- Railway cron job: dagelijks 02:00 UTC
- Admin knop voor handmatige on-demand backup
- Retentie: laatste 30 backups bewaren, oudere verwijderen
- Backup status zichtbaar op admin dashboard

---

### OPS-2 — Disaster recovery procedure
**Waarde:** Binnen 15 min terug online na dataverlies
**Prioriteit:** Hoog (na OPS-1)
**Effort:** 1-2 uur
**Afhankelijk van:** OPS-1 (backups moeten bestaan)
**Beschrijving:**
Gedocumenteerde en geteste restore procedure:
- Restore script: download laatste backup uit R2 → kopieer naar volume
- Stap-voor-stap guide in deployment docs
- Test restore op staging (bewijs dat het werkt)
- Recovery Time Objective (RTO): < 15 minuten
- Recovery Point Objective (RPO): < 24 uur (dagelijkse backup)

---

## Feedback Martien (23 maart 2026)

### MF-1 — Kaart zoekfunctie (adres/postcode)
**Waarde:** Sneller locatie vinden op trace kaart
**Prioriteit:** Middel
**Effort:** 2-3 uur
**Beschrijving:** Zoekbalk op de trace kaartpagina. Geocoding via PDOK Locatieserver (gratis, NL-dekkend). Zoek op adres, postcode+huisnummer, of plaatsnaam → kaart centreert op resultaat.

---

### MF-2 — Kaart in apart window
**Waarde:** Hogere nauwkeurigheid bij trace invoer
**Prioriteit:** Laag
**Effort:** 1 uur
**Beschrijving:** Knop "Open in groot venster" op trace pagina → opent kaart in fullscreen popup/nieuw tabblad. Zelfde functionaliteit, meer schermruimte.

---

### MF-3 — DXF layout (paperspace) met views
**Waarde:** Werkdocument voor AutoCAD — dit is wat Martien oplevert
**Prioriteit:** Hoog
**Effort:** 8-12 uur
**Beschrijving:**
DXF met model + paperspace layout (A3). Views in layout:
- BOVENAANZICHT: schaal 1:2000, 1:4000, 1:5000 of 1:10000
- SITUATIE: schaal 1:200-1:500, geroteerd zodat intree links, uittree rechts
- LENGTEPROFIEL: zelfde schaal als situatie, "platgeslagen dwarsprofiel"
- DOORSNEDE BOORGAT
- Titelblok met tekeningnummer + revisie rechtsonderin

Dit is de kernfunctie van het platform — Martien zegt "DXF is leidend, PDF is afgeleid".

---

### MF-4 — Parameter validatie + preview
**Waarde:** Voorkom fouten vóór generatie (bijv. boring te kort voor Rv)
**Prioriteit:** Hoog
**Effort:** 3-4 uur
**Beschrijving:**
- Validatie: check of L_totaal >= Tin_h + Tuit_h, waarschuw als Rv aangepast moet worden
- Preview: toon lengteprofiel schets + parameters tabel op boring detail pagina
- Toon berekende waarden: Rv, tangentlengtes, dekking, diepte
- Blokkeer niet — waarschuw alleen, laat gebruiker parameters aanpassen

---

### MF-5 — Lengteprofiel bij horizontale bochten
**Waarde:** Correcte profiellengte bij bochtige tracés
**Prioriteit:** Middel
**Effort:** 2-3 uur
**Beschrijving:**
Lengteprofiel is een "platgeslagen dwarsprofiel": bij een boorlijn met horizontale bochten is de profiellengte = de werkelijke booglengte over het maaiveld, niet de rechte lijn intree→uittree. Huidige engine gebruikt `trace_totale_afstand()` wat al de som van segmenten is — maar moet geverifieerd worden dat dit correct doorwerkt naar DXF/PDF schaal.

---

### MF-7 — DXF/PDF opslaan op Google Drive
**Waarde:** Martien en Ello werken vanuit gedeelde Drive, geen lokale downloads
**Prioriteit:** Hoog
**Effort:** 3-4 uur
**Afhankelijk van:** Google Cloud Service Account + Drive toegang
**Beschrijving:**
Bij DXF/PDF generatie: upload naar Google Drive i.p.v. download naar browser.
- Gedeelde drive: "Ello - Martien"
- Mapstructuur: `orders/{ordernummer} {locatie}/`
- Map wordt automatisch aangemaakt als die niet bestaat
- Bestandsnaam: `{ordernummer}-{volgnr} {naam}-rev.{rev}.dxf`
- Gebruiker krijgt link naar Drive bestand
- Optie: ook lokale download behouden als fallback

Technisch:
- `google-api-python-client` + `google-auth` dependencies
- Service Account met toegang tot gedeelde drive
- Env vars: `GOOGLE_SERVICE_ACCOUNT_JSON`, `GOOGLE_DRIVE_FOLDER_ID`

Stappen voor setup:
1. Google Cloud project aanmaken (of bestaand gebruiken)
2. Google Drive API inschakelen
3. Service Account aanmaken → JSON key downloaden
4. Service Account e-mail toevoegen aan gedeelde drive "Ello - Martien" als Editor
5. Folder ID van "orders" map ophalen uit Drive URL
6. Env vars op Railway instellen

---

### MF-6 — Tekeningnummer + revisie rechtsonderin [KLEIN]
**Waarde:** Standaard tekening conventie
**Prioriteit:** Hoog
**Effort:** 15 min
**Beschrijving:** Tekeningnummer (= ordernummer-boringnummer) + revisienummer rechtsonderin in titelblok. Formaat: "Nr: BT26V204 Zwolle-01 Rev: 0"
- Recovery Point Objective (RPO): < 24 uur (dagelijkse backup)

