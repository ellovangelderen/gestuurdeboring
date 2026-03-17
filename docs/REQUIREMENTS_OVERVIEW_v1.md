# HDD Ontwerp Platform — Requirements & Use Cases
**Ter review door Martien Luijben**
**Versie 1.0 | 17 maart 2026**
**Opgesteld door: Inodus (Ello van Gelderen)**

---

## Hoe dit document te lezen

Dit document beschrijft alles wat het platform gaat doen. Per onderdeel staat:
- **Wat**: wat het platform doet
- **Hoe nu**: hoe je het nu doet (handmatig)
- **Hoe straks**: hoe het platform het oplost
- **Jouw input nodig?**: of we nog iets van jou nodig hebben

Graag per punt aangeven:
- ✅ Klopt, zo wil ik het
- ❌ Klopt niet, moet anders (toelichting)
- ❓ Heb ik vragen over

---

## 1. Orderbeheer (Cockpit)

### 1.1 Orderoverzicht als startpagina
- **Wat**: Na inloggen zie je direct al je orders in één tabel
- **Hoe nu**: Google Sheets orderlijst, bijgehouden door Nid
- **Hoe straks**: Platform toont alle orders met status, deadline, KLIC-status, EV-waarschuwingen, tekenaar. Zoeken, filteren, sorteren.
- **Jouw input nodig?**: Nee

### 1.2 Order aanmaken
- **Wat**: Nieuwe order invoeren met basisgegevens
- **Velden**: Ordernummer, locatie, klantcode, opdrachtgever, deadline, type boringen, aantal, vergunning (P/W/R/geen)
- **Hoe nu**: Nid typt een nieuwe rij in GSheets
- **Hoe straks**: Formulier in het platform. Klantcodes als dropdown (22+ klanten). Meerdere boringen per order mogelijk.

### 1.3 Meerdere boringen per order
- **Wat**: Eén order kan meerdere boringen bevatten, elk met eigen type
- **Voorbeeld**: Order 3D26V810 → Boring 01 (B), Boring 02 (B), Boring 03 (Z/BZ)
- **Hoe nu**: In GSheets aparte rijen met hetzelfde ordernummer
- **Hoe straks**: Eén order met sub-boringen. Elke boring heeft eigen tracé, tekening, berekening.
- **Bestandsnamen**: 3D26V810-01-rev.1.dxf, 3D26V810-02-rev.1.dxf, 3D26V810-03-rev.1.dxf

### 1.4 Vier boringtypen
- **B** = Gestuurde boring (standaard)
- **N** = Nano boring (kleine gestuurde boring, zelfde werkwijze)
- **Z/BZ** = Boogzinker (vereenvoudigde boring, 1 boog)
- **C** = Calculatie (alleen Sigma berekeningen, geen tekening)
- **Hoe straks**: Bij type keuze toont platform de juiste invoervelden:
  - B/N: intreehoek, uittreehoek, Rv intrede, Rv uittrede, horizontale lengte
  - Z: booghoek (5° / 7,5° / 10°) + stand (1-10) → lengte automatisch berekend
  - C: alleen berekeningsinvoer, geen tracé of tekening

### 1.5 Status per order
Platform houdt de volgende statussen bij:
1. **Ontvangen** — order is binnengekomen
2. **In uitvoering** — tekenaar werkt eraan
3. **Geleverd** — ontwerp opgeleverd aan opdrachtgever
4. **Wacht op akkoord** — geleverd maar geen reactie ontvangen
5. **Afgerond** — akkoord ontvangen
6. **Geannuleerd** — order vervallen

### 1.6 Tekenaar per order
- **Wat**: Elke order is toegewezen aan een tekenaar
- **Default**: Martien Luijben
- **Wijzigbaar**: Ja, per order aanpasbaar
- **Filter**: "Mijn orders" filter in het overzicht
- **Hoe nu**: Niet systematisch bijgehouden
- **Hoe straks**: Dropdown met beschikbare tekenaars

### 1.7 PRIO-vlag
- **Wat**: Orders markeren als prioriteit
- **Hoe nu**: "PRIO" als tekst in de notitie-kolom van GSheets
- **Hoe straks**: Aparte PRIO-knop per order. Filteren op PRIO mogelijk.

### 1.8 Notities per order
- **Wat**: Vrije tekst per order voor opmerkingen
- **Voorbeeld**: "Rioolgegevens nog te bevestigen", "Nieuw ontwerp voor V661-15"
- **Hoe nu**: Note-kolom in GSheets
- **Hoe straks**: Notitieveld per order, altijd zichtbaar

### 1.9 Vergunning
- **Wat**: Aangeven welke vergunning nodig is
- **Opties**: P (Provincie), W (Waterschap), R (Rijkswaterstaat), of geen
- **Hoe nu**: Kolom "Permit required" in GSheets
- **Hoe straks**: Dropdown per order

### 1.10 Eén klik navigatie
- **Wat**: Vanuit het orderoverzicht in één klik naar:
  - Tekening (per boring)
  - Berekening (per boring)
  - Werkplan (per boring)
  - KLIC data
  - Kaart (PDOK)
  - Waterschap kaart
- **Hoe nu**: Links in GSheets kolommen (PDOK, Google Maps, Waterkering)
- **Hoe straks**: Knoppen per order in de tabel. Inactieve knoppen als data nog niet beschikbaar.

### 1.11 Akkoord-contactpersoon per order
- **Wat**: Bij aanmaken order selecteer je de contactpersoon die het ontwerp accordeert
- **Invoer**: Dropdown met standaard namen per opdrachtgever + vrij invoerveld
- **Waar zichtbaar**: Titelblok op DXF en PDF tekening ("Akkoord: [naam]")
- **Standaard contactpersonen**:

| Opdrachtgever | Default contactpersoon |
|---|---|
| 3D-Drilling | Michel Visser |
| R&D Drilling | Marcel van Hoolwerff |
| Infra Elite | Erik Heijnekamp |
| Kappert Infra | Alice Kappert |
| BTL Drilling | Patricia |

- **Vrij invullen**: Ja, voor opdrachtgevers die niet in de lijst staan
- **Hoe nu**: Handmatig op de tekening zetten
- **Hoe straks**: Eenmalig invoeren per order, automatisch op alle tekeningen van die order
- **Jouw input nodig?**: Graag de volledige lijst met alle opdrachtgevers + contactpersonen aanleveren

---

## 2. KLIC beheer

### 2.1 KLIC upload
- **Wat**: KLIC ZIP-bestand uploaden in het platform
- **Hoe nu**: Bestand opslaan in Drive-map, KLIC-nummer noteren in GSheets
- **Hoe straks**: Upload in platform, automatisch verwerkt
- **Koppeling**: KLIC zit op order-niveau. Meerdere KLICs per order mogelijk.

### 2.2 KLIC versioning
- **Wat**: Eén KLIC-meldingnummer kan meerdere versies hebben
- **Voorbeeld**:
  - Versie 1: oriëntatiemelding (jan 2026)
  - Versie 2: hermelding na wijziging (feb 2026)
- **Hoe straks**: Platform slaat alle versies op. Jij kiest per boring welke versie geldt.

### 2.3 KLIC verwerking (automatisch)
- **Wat**: Platform leest de KLIC ZIP uit en toont:
  - Alle beheerders + aantal leidingen
  - Leidingtypen per beheerder
  - Sleufloze leidingen gedetecteerd (PE/staal = geboord)
  - EV-waarschuwingen met contactgegevens
  - Dieptes (als beschikbaar — altijd met waarschuwing "onbetrouwbaar")
- **Hoe nu**: Handmatig KLIC doornemen in AutoCAD
- **Jouw input nodig?**: Nee, maar we valideren met HDD11 KLIC data (11 beheerders, 1127 leidingen)

### 2.4 EV-zones (wettelijk verplicht)
- **Wat**: Leidingen met Eis Voorzorgsmaatregel prominent markeren
- **Risico**: Niet afhandelen → boetes van Agentschap Telecom
- **Hoe straks**:
  - EV-leidingen rood gemarkeerd in het overzicht
  - Contactgegevens netbeheerder opgeslagen
  - EV-zone als aparte laag in DXF
  - EV-zone zichtbaar in PDF situatietekening
  - Waarschuwing: "Altijd buiten EV-zonering ontwerpen"

### 2.5 KLIC meldingtypen
- **Oriëntatiemelding**: Standaard bij ontwerp, uitvoering > 4 weken. Mag NIET op worden gegraven.
- **Graafmelding**: Uitvoering ≤ 4 weken. Verloopt na 20 werkdagen.
- **Platform**: Toont tip als uitvoerdatum bekend is en < 4 weken → "Overweeg graafmelding"

---

## 3. Locatie & kaart

### 3.1 Tracé invoeren
- **Wat**: RD-coördinaten invoeren per punt (intrede, tussenpunten, uittrede)
- **Primair**: Coördinaten zijn de echte invoer (niet de kaart)
- **Kaart**: Leaflet kaart naast het formulier als oriëntatie
- **Hoe nu**: Coördinaten handmatig invoeren, kaart in AutoCAD

### 3.2 PDOK link automatisch
- **Wat**: Platform genereert automatisch een PDOK-link zodra coördinaten zijn ingevoerd
- **Hoe nu**: Nid plakt handmatig een PDOK-URL per order
- **Hoe straks**: Automatisch, één klik om PDOK kaart te openen

### 3.3 Waterschap kaart automatisch
- **Wat**: Platform genereert automatisch de juiste waterschapskaart-link
- **Hoe nu**: Nid kopieert adres vanuit Google Maps en plakt in waterschapskaart
- **Hoe straks**: Platform bepaalt welk waterschap, opent juiste kaart op juiste locatie

### 3.4 Maaiveld (NAP)
- **Handmatig**: MVin en MVuit invoeren in meters t.o.v. NAP
- **Automatisch (later)**: AHN5 haalt maaiveld op via PDOK
- **Override**: Handmatige invoer overschrijft altijd de automatische waarde

### 3.5 Grondtype
- **Handmatig**: Dropdown Zand / Klei / Veen per doorsnede
- **Automatisch (later)**: Sonderingen uit Dinoloket

---

## 4. Ontwerp (per boring)

### 4.1 Boorprofiel gestuurde boring (B/N)
5 segmenten, tangentiaal aansluitend:
1. Neergaand recht (intreehoek)
2. Neergaande curve (boog, Rv intrede)
3. Horizontaal (rechte lijn)
4. Opgaande curve (boog, Rv uittrede)
5. Opgaand recht (uittreehoek)

Parameters: intreehoek (°), uittreehoek (°), Rv intrede (m), Rv uittrede (m), horizontale lengte (m)

### 4.2 Boorprofiel boogzinker (Z/BZ)
1 segment: één vaste boog
- Standaard bogen: 5° / 7,5° / 10°
- 10 mogelijke standen
- Lengte = booghoek x stand (automatisch berekend)
- Geen horizontaal deel

Parameters: booghoek (°), stand (1-10) → lengte volgt automatisch

### 4.3 Calculatie (C)
- Alleen Sigma berekeningen (sterkte, intrekkracht, boorspoeldruk)
- Geen tracé, geen tekening, geen werkplan
- Output: PDF met berekeningen
- Vooral voor: provincie Groningen

### 4.4 Eisenprofiel selecteren
- **Wat**: Per te kruisen object de eisen van de vergunningverlener selecteren
- **5 standaard profielen**: RWS, Waterschap, Provincie, Gemeente, ProRail
- **Per profiel**: minimale dekking weg (m), minimale dekking water (m), minimale boogstraal (m)
- **Override**: Als vergunning afwijkende eisen stelt, handmatig aanpassen

### 4.5 Intrekkracht
- **Handmatig**: Invoeren uit Sigma (bijv. Ttot = 30.106 N voor HDD11)
- **Alleen als gevraagd**: Niet elke opdrachtgever vraagt om intrekkrachtberekening
- **Automatisch (later)**: Platform berekent NEN 3651 (lage prioriteit)

### 4.6 Conflictcheck K&L
- **Wat**: Platform controleert of het boorprofiel conflicteert met bestaande kabels en leidingen
- **Waarschuwing**: KLIC dieptes zijn ALTIJD onbetrouwbaar → altijd waarschuwen
- **Hoe nu**: Handmatig beoordelen in AutoCAD

---

## 5. Output

### 5.1 DXF tekening
- **Formaat**: DXF R2013 (compatibel met AutoCAD 2014+)
- **Laagnamen**: Exact conform NLCS / HDD28 referentie (16 lagen)
- **Inhoud**: Boorlijn, boorgat, maaiveld, maatvoering, sensorpunten, titelblok, K&L lagen
- **Per boring**: Elk een apart DXF-bestand
- **Bestandsnaam**: {ordernummer}-{volgnummer}-rev.{revisie}.dxf

### 5.2 PDF tekening
- **Formaat**: A2Z4 (landscape)
- **Inhoud**:
  - Bovenaanzicht (1:4000, noorden boven)
  - Situatietekening (1:250, NLCS-kleuren, tracé A→B)
  - Lengteprofiel (1:250 op NAP, maatvoering bij elk sensorpunt)
  - Doorsnede boorgat
  - GPS punten (RD-coördinaten per sensorpunt)
  - Hoeken (intree + uittree in graden en %)
  - Titelblok (project, schaal, datum, getekend=M.Luijben, akkoord=[contactpersoon opdrachtgever], revisietabel)
  - Logo's (Logo3D.jpg + opdrachtgever logo)
  - OPMERKINGEN (KLIC-disclaimer, CROW 96b, walk-over meetsysteem)
- **Per boring**: Elk een apart PDF-bestand

### 5.3 Werkplan (automatisch gegenereerd)
- **Wat**: Automatisch werkplan genereren op basis van projectgegevens
- **6 hoofdstukken** + bijlagen A-G
- **Automatisch (boilerplate)**: Secties 3.2.1-3.2.4, 5.1-5.2, 6.2, 6.4 — identiek voor elk project
- **Automatisch (data)**: Titelblok, buis-specs, CKB-tabel, tijdsplanning, berekeningsresultaten
- **AI-gegenereerd (projectspecifiek)**: 2.1 Locatie, 2.2 Historie, 2.3 K&L, 2.3 Geotechniek
- **CKB-categorie**: Op basis van trekkracht: ST-A (<9T), ST-B (10-39T), ST-C (40-149T), ST-D (>150T)
- **Formaat B** (huidig, niet Formaat A)
- **Stijlreferenties**: 3D25V679 HDD1 + 3D25V638
- **Hoe nu**: ~2 uur per werkplan, deels met ChatGPT/NotebookLM
- **Hoe straks**: Platform genereert concept in minuten. Jij reviewt en past aan.
- **Jouw input nodig?**: Locatiespecifieke secties (2.1, 2.2) vereisen jouw kennis

### 5.4 Download
- **Hoe nu**: Bestanden in Drive-map
- **Hoe straks**: Downloadknoppen in het platform per boring (DXF, PDF, werkplan)
- **Later**: Automatische sync naar Google Drive

---

## 6. Wekelijkse statusmail

### 6.1 Automatisch overzicht per opdrachtgever
- **Wat**: Elke maandag automatisch een email per opdrachtgever met:
  - Openstaande orders die wachten op akkoord
  - Recent geleverde orders zonder bevestiging
  - Orders die al lang open staan (bijv. >4 weken)
- **Hoe nu**: Niet systematisch. Vaak geen akkoord ontvangen, order wordt toch afgerekend.
- **Hoe straks**: Automatische herinnering. Opdrachtgever kan antwoorden → mail komt bij jou.
- **Handmatig triggeren**: Ook mogelijk om direct te versturen (niet alleen op maandag)
- **Preview**: Eerst bekijken voordat het verstuurd wordt

---

## 7. Sleufloze leidingen

### 7.1 Detectie
- **Primaire regel (materiaal)**:
  - PE (HPE, HDPE, PE100, PE80) = ALTIJD geboord
  - Staal = KAN geboord zijn (markeren als "mogelijk sleufloos")
  - PVC, beton, asbestcement = gegraven (nooit sleufloos)
- **Aanvullende regel (KLIC bijlagen)**: Mantelbuis zonder diepte + PDF-bijlage = sleufloze techniek
- **Hoe nu**: Handmatig KLIC doornemen
- **Hoe straks**: Platform detecteert automatisch en markeert sleufloze leidingen

---

## 8. Riooldata (GWSW)

### 8.1 Riool-taxonomie
- **Persriool**: Onder druk, geen BOB-afschot
- **Vrijverval DWA** (vuilwater): BOB-maten standaard beschikbaar
- **Vrijverval HWA** (hemelwater): BOB-maten NIET standaard. Diepte 80-120cm. Niet op afschot.
- **Vrijverval GWA** (gemengd): BOB-maten standaard beschikbaar

### 8.2 BOB-bronnen
Volgorde van betrouwbaarheid:
1. GWSW via apps.gwsw.nl
2. Gemeente-portaal (bijv. kaart.haarlem.nl — heeft BOB + bomendata)
3. Gemeente per mail opvragen

### 8.3 BOB uit vrije tekstvelden
- BOB-info zit soms in vrije tekstvelden in de KLIC (niet in gestructureerde velden)
- Voorbeelden: "R 234, +/-2.58 -NAP", "diepte gem. -2.6m tov NAP"
- Platform extraheert dit maar markeert ALTIJD als onzeker

---

## 9. Topotijdreis

### 9.1 Historische kaarten
- **Wat**: Automatisch historische kaarten tonen voor het tracégebied
- **Waarde**: Detectie van gesloopte objecten (viaducten, bruggen, tunnels) waarvan funderingen mogelijk nog aanwezig zijn
- **Jouw werkwijze nu**: Handmatig op topotijdreis.nl, soms heen en weer schakelen tussen jaren
- **Hoe straks**: Platform toont wanneer er iets veranderd is (wijzigingsdetectie). Voor/na vergelijking.
- **Jouw cases**:
  1. Viaduct A2: gesloopt maar heipalen mogelijk nog aanwezig
  2. Boring gestopt op 9m/12m: achteraf water en brug op die locatie
  3. Boring langs tunnel: stoomtramverbinding uit 1912

---

## 10. Bomen als obstakel

- **Wat**: Bomen zijn beschermd. Wortelradius is ongeveer gelijk aan de kruindiameter. Worteldiepte is circa 1 meter.
- **Bij conflict**: Altijd boren i.p.v. graven
- **Databron**: kaart.haarlem.nl (kruindiameter per boom) — per gemeente verschillend

---

## 11. Opdrachtketen

Formele keten:
```
Asset owner (Liander, KPN, Ziggo, Delta, Relined)
  → Aannemer (DMMB, van Baarsen, van Gelder)
    → Boorbedrijf (3D-Drilling, R&D Drilling)
      → GestuurdeBoringTekening.nl (Martien)
```

- Soms werk je rechtstreeks voor de aannemer of asset owner
- Alle partijen staan op de tekening (titelblok + logo's)
- Tekenaar: altijd Martien (ook als Nid de uitwerking heeft gedaan)
- Tekenaar: altijd Martien (ook als Nid de uitwerking heeft gedaan)
- Akkoord: contactpersoon van de opdrachtgever (invoerveld per order, zie 1.11)

---

## 12. Migratie GSheets

### 12.1 Aanpak
- **Alles migreren**: Alle ~2454 orders uit GSheets worden geïmporteerd
- **Wat niet compleet is**: Vul je later aan in het platform
- **GSheets wordt archief**: Na migratie is het platform de bron

### 12.2 Wat wordt automatisch overgenomen
- Ordernummer, locatie, klant, status, deadline, leverdatum
- Type boringen + aantal
- KLIC-nummer
- Vergunning type
- PRIO-markering
- Alle URLs (Google Maps, PDOK, waterkering, oppervlaktewater, peil)
- EV-partijen (max 5 per order)
- Email-contacten (max 6 per order)
- RD-coördinaten (automatisch uit PDOK-URLs)

### 12.3 Wat jij later aanvult
- Tracé-coördinaten (exacte RD-punten per boring)
- Leidingparameters (materiaal, SDR, De, etc.)
- Doorsneden en berekeningen

---

## 13. SnelStart koppeling (toekomst)

- **Wat**: Facturatie-informatie automatisch naar SnelStart sturen
- **Hoe nu**: Handmatig factureren
- **Hoe straks**: Platform stuurt afgeronde orders door naar SnelStart
- **Status**: Lage prioriteit, later in te bouwen

---

## 14. Vergunningscheck (toekomst)

- **Wat**: Automatisch checken welke vergunningen nodig zijn via omgevingswet.overheid.nl
- **Per tracé**: RWS, Provincie, Waterschap, Gemeente
- **Status**: Onderzoeken of dit automatisch kan

---

## 15. Gebruikers

### Platformgebruikers

| Persoon | Rol | Wat ze doen in het platform |
|---|---|---|
| Martien Luijben | Eigenaar, hoofdtekenaar | Reviewt/accordeert alle ontwerpen, maakt tekeningen |
| Nid (Sopa Choychod) | Orderadministratie, tekenaar | Houdt orderlijst bij, maakt uitwerkingen |

### Akkoord-contactpersonen (niet in platform, wel op tekening)

Deze personen staan in het "Akkoord" veld op de tekening. Ze zijn geen platformgebruikers maar contactpersonen bij de opdrachtgever. Zie ook 1.11.

| Opdrachtgever | Contactpersoon |
|---|---|
| 3D-Drilling | Michel Visser |
| R&D Drilling | Marcel van Hoolwerff |
| Infra Elite | Erik Heijnekamp |
| Kappert Infra | Alice Kappert |
| BTL Drilling | Patricia |
| *Overige* | *Vrij in te vullen per order* |

---

## 16. Wat het platform NIET doet

- Offerte of calculatie genereren (behalve Sigma via type C)
- Projectmanagement (geen Jira/Asana)
- Automatisch uploaden naar Omgevingsloket
- BIM / IFC export
- Klant-intakeformulier
- Multi-tenant (Inodus beheert het platform)

---

## Vragen aan Martien

Graag per onderdeel aangeven:
1. ✅ / ❌ / ❓
2. Eventuele correcties of aanvullingen
3. Specifiek: klopt de boogzinker beschrijving (4.2)?
4. Specifiek: klopt de status-workflow (1.5)?
5. Specifiek: missen er klantcodes?
6. Specifiek: zijn er meer boringtypen dan B/N/Z/C?

---

*Opgesteld door Inodus · 17 maart 2026*
