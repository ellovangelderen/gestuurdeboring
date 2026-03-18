# Mail aan Martien — 18 maart 2026
**Aan:** Martien Luijben
**Van:** Architect, Inodus LeanAI Platform
**Onderwerp:** Voortgang HDD Platform — volledige backlog afgerond, vragen + Excel-analyse

---

Hallo Martien,

Hierbij een update van de voortgang op het HDD Ontwerp Platform. We hebben vandaag een grote sprint gemaakt en de volledige backlog van 18 items afgerond. Daarnaast hebben we jouw Excel-werkboek geanalyseerd en daar komen een aantal vragen en keuzes uit voort.

## Wat is er gebouwd

Alle 18 backlog items zijn werkend, getest (199 tests groen) en beschikbaar op het platform:

| # | Feature | Kort |
|---|---------|------|
| 0 | Datamodel refactor | Order → meerdere boringen (B/N/Z/C) |
| 1 | Werkplan generator | Claude API, 6 hoofdstukken, CKB ST-A/B/C/D |
| 2 | Cockpit UI | Orderoverzicht, filters, zoeken, CSV export |
| 3 | KLIC IMKL parser | ZIP + GML V2, 11 beheerders, EV-detectie |
| 3b | EV-zone DXF | EV-zone als laag + waarschuwing |
| 4 | Statusmail | Concept-mails per klant, kopieerbaar |
| 5 | GWSW riool BOB | PDOK API + gemeente-mail als BOB ontbreekt |
| 6 | Sleufloze detectie | Materiaalregel (PE=geboord) + bijlage-heuristiek |
| 7 | Conflictcheck K&L | 3D afstand boortracé vs. leidingen |
| 8 | Boogzinker (type Z) | 1 ARC, booghoek 5/7.5/10°, stand 1-10 |
| 9 | Boorprofiel ARCs | 5-segment geometrie, lengteprofiel DXF + PDF |
| 10 | AHN5 maaiveld | Automatisch ophalen + waterschap detectie |
| 11 | Topotijdreis | Historische kaarten 1815-2015 met tijdslider |
| 12 | Tracévarianten | Meerdere tracés vergelijken op kaart + delta tabel |
| 13 | SnelStart concept | Factuurregels per boring, kopieerbaar |
| 14 | Vergunningscheck | Links naar Omgevingsloket, PDOK, BAG, Bodemloket |
| 15 | Dinoloket sonderingen | Links naar DINOloket en BRO |
| 18 | As-Built revisie | Werkelijke meetpunten invoeren, vergelijken met ontwerp |

## PDF tekening

De PDF-tekening is volledig herontworpen met een professionele layout:

- **Links-boven:** overzichtskaart (1:4000) met tracé
- **Rechts-boven:** situatietekening met luchtfoto + KLIC leidingen (NLCS kleuren) + sensorpuntlabels
- **Links-onder:** doorsneden tabel + legenda + doorsnede boorgat cirkel
- **Rechts-onder:** lengteprofiel met boorlijn, NAP grid, doorsnede-nummers
- **Titelblok:** 3D-Drilling + GBT logo's, projectinfo, revisietabel

We willen dit graag met je vergelijken met jouw huidige tekeningen om te kijken waar het nog beter kan.

## Testhandleiding

Er staat een testhandleiding klaar in `docs/TEST_HANDLEIDING_MARTIEN.md` met 80+ testscenario's verdeeld over 17 secties. Je kunt alles testen op http://localhost:8000 (of hdd.inodus.nl zodra we deployen). Elke sectie heeft stap-voor-stap instructies met verwachte resultaten.

## SnelStart

Voor de SnelStart koppeling hoef je geen maatwerk API-integratie te doen. Je kunt het zelf instellen via de SnelStart webportal. Het platform genereert concept-facturen met de juiste regels per boring die je kunt kopiëren en invoeren.

## Analyse van jouw Excel-werkboek

We hebben jouw Excel-werkboek geanalyseerd (alle sheets: INPUT, Ontwerp, CSV, Script, K&L, TOOLS). Hieruit komen een aantal punten waar we jouw keuze bij nodig hebben, plus informatie die we direct kunnen verwerken.

### Beslissingen — jouw keuze nodig

**B1 — Buigradius per segment**
Jouw Excel heeft Rv_intrede, Rv_horizontaal en Rv_uittrede als aparte waarden. Het platform berekent nu één Rv (= 1200 × De) voor alles. Gebruik je in de praktijk verschillende stralen per segment, of is 1200×De altijd goed genoeg?

*Impact: nauwkeurigheid van de boogcurve in het lengteprofiel op de PDF.*

**B2 — Boorgat diameter automatisch uit bundelfactor**
Jouw Excel berekent Dg automatisch: bundelfactor × De × ruimfactor. Bundelfactoren: 1 buis=1.0, 2 buizen=2.0, 3=2.15, 4=2.73. Het platform heeft Dg nu als handmatig invoerveld (default 240mm). Wil je dat we Dg automatisch berekenen uit het aantal buizen?

*Impact: doorsnede boorgat op tekening en DXF.*

**B3 — Ruimfactoren per boringtype**
Jouw Excel: enkelbuis=1.5, bundel=1.2, boogzinker=1.1. Het platform past nu geen ruimfactor toe. Dat betekent dat de boogzinker boorgat diameter nu te groot is (1.5× ipv 1.1×). Moeten we dit automatisch toepassen?

*Impact: correcte Dg bij boogzinker boringen.*

**B4 — Boormachine selectie**
Jouw Excel selecteert een boormachine (VermeerD40, Pers) die als INSERT blok in de DXF komt. Is dit nodig in het platform, of doe je dit handmatig in AutoCAD?

*Impact: alleen visueel in DXF bovenaanzicht.*

**B5 — Type "W" (werkplan) als boringtype**
In jouw orderlijst heeft W (werkplan) een eigen rij naast B/N/Z/C. Het platform behandelt werkplan als een apart document op order-niveau, niet als boringtype. Moeten we W toevoegen als 5e type, of is de huidige aanpak goed?

*Impact: vooral bij migratie van jouw orderlijst naar het platform.*

**B6 — Standaard K&L dieptes als fallback**
Jouw Excel heeft indicatieve dieptes: LD-GAS=-0.70m, HD-GAS=-1.00m, BGI=-1.00m. Als de KLIC geen diepte levert (wat bij HDD11 voor alle 1127 leidingen het geval was), zou het platform deze standaardwaarden kunnen gebruiken in de conflictcheck in plaats van alleen "diepte onbekend" te melden. Mogen we dat doen (met een waarschuwing "indicatief")?

*Impact: grote verbetering van de conflictcheck — van "onbekend" naar een echte afstandsberekening.*

### Informatie die we direct verwerken

Zodra we jouw klantcodes bevestigd hebben, verwerken we deze verbeteringen:

- **V1:** Klantcodes uitbreiden naar 18+ klanten (inclusief Verbree, Hogenhout, Direxta, Circet, etc.) — codes graag bevestigen
- **V2:** Boogzinker hulptabel (10 standen × 3 hoeken) voor validatie
- **V3:** Opdrachtgever/aannemer keten — eventueel 3e logo op titelblok
- **V4:** EV-partijen handmatig invoerbaar (nu alleen uit KLIC parser)
- **V5:** Email-contacten koppelen aan EV-partijen
- **V6:** PDOK URLs met specifieke lagen overnemen bij migratie

### Toekomstige items (na jouw feedback)

- **T1:** CSV GPS export — 880 punten langs de boorlijn per meter, voor AutoCAD import
- **T2:** AutoCAD .scr scriptgenerator — `_PLINE`, `_INSERT`, `_LAYER` commando's
- **T3:** Horizontale bocht berekening — waarschuwen als bocht te scherp
- **T4:** BGT/KLIC/DKK laadscripts voor InfraCAD Map
- **T5:** Contactpersonen via klantbestanden (CC-MASTER, KB-MASTER)

## Volgende stappen

1. Kun je de beslissingen B1-B6 doornemen en laten weten wat je keuze is?
2. Kun je de klantcodes + contactpersonen in V1 bevestigen of aanvullen?
3. We plannen graag een moment om samen door de testhandleiding te lopen

De volledige analyse staat in `docs/Backlog/BACKLOG_EXCEL_ANALYSE.md` in de repository.

Met vriendelijke groet,

Architect
Inodus LeanAI Platform
