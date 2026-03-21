# Analyse — Feedback Martien 20 maart 2026 (live demo)
**Status: ANALYSE — geen implementatie zonder goedkeuring**

---

## Samenvatting

Martien's feedback is verdeeld in 12 onderwerpen. Hieronder per punt:
- Wat zegt Martien
- Impact op het platform
- Wat kunnen we doen (quick win / middelgroot / groot)
- Aanbeveling

---

## 1. Vergunning instantie-selectie (P/W/R is te beperkt)

**Martien zegt:** Het kan ook ProRail, gemeente, of asset owner zijn. En combinaties. Hij weet niet altijd welke instanties van toepassing zijn. Risico op onvolledige/onjuiste info. "Kunnen we eventueel ook gewoon aanzien hoe dit gaat."

**Analyse:**
- Huidige `Order.vergunning` is een enum: P (Provincie) / W (Waterschap) / R (RWS) / - (geen)
- Martien bevestigt dat dit te beperkt is maar ook niet kritisch
- Hij doet de vergunning niet zelf — hij ontwerpt, iemand anders vraagt aan

**Aanbeveling:** 🟡 LAAG PRIO. Vergunning-veld uitbreiden naar multi-select (tags) in plaats van single enum. Maar Martien zegt zelf: "aanzien hoe dit gaat". **Geen actie nu.**

---

## 2. Automatische detectie beheerorganen + zoneringen op kaart

**Martien zegt:** "Hoe bepaalt het Platform welk orgaan van toepassing is? Nu doen wij dat handmatig." Waterkering is lastig te zien, automatisch is interessant. Bij Rijksweg/waterkering: zoneringen tonen op de kaart.

**Analyse:**
- Waterschap detectie hebben we al (PDOK WMS → `bepaal_waterschap()`)
- RWS/ProRail zoneringen: er zijn publieke kaartservices
  - RWS beheerzones: `geoweb.rijkswaterstaat.nl` (Martien gaf URL)
  - ProRail: `maps.prorail.nl` (Martien gaf URL)
- Zoneringen op de kaart tonen = WMS overlay toevoegen aan Leaflet

**Mogelijke aanpak:**
- **Quick win:** Links naar RWS/ProRail toevoegen op vergunningscheck pagina (al gedaan voor Omgevingsloket)
- **Middelgroot:** WMS overlay van RWS beheerzones op de trace-kaart
- **Groot:** Automatische detectie of tracé in een zonering valt (spatial query)

**Aanbeveling:** 🟠 MIDDEL. Quick win: links toevoegen. Middelgroot: WMS overlay op kaart. Automatische detectie later.

---

## 3. Omgevingsloket standaard-antwoorden

**Martien zegt:** "Je moet heel veel vragen beantwoorden. We zouden er eens naar moeten kijken of we die standaard kunnen beantwoorden." Heeft iemand in netwerk die kan helpen.

**Analyse:**
- Het Omgevingsloket is een wizard met veel vragen
- Voor HDD is het type activiteit steeds (nagenoeg) gelijk
- Geen publieke API beschikbaar
- Dit is kenniswerk, niet softwareontwikkeling

**Aanbeveling:** 🟡 LAAG PRIO. Martien zoekt iemand met ervaring. Wij documenteren de standaard-antwoorden als ze beschikbaar zijn. **Geen platform-actie nu.**

---

## 4. Kaart interactie (drag, zoom, lagen, navigatie)

**Martien zegt:**
- Punten verslepen lukt niet (alleen plaatsen)
- Niet ver genoeg kunnen inzoomen
- KLIC, BGT, DKK, GWSW als schakelbare lagen
- Kaart altijd bereikbaar (knop)
- Terug-pijl naar vorige scherm

**Analyse:**
- Punt-versleep: Leaflet `L.marker` met `draggable: true` → RD update
- Zoom: we gebruiken OSM tiles (max zoom 19). BGT WMTS gaat tot zoom 14 in RD
- Lagen: BGT is al toegevoegd (verse checkout). KLIC/DKK/GWSW als WMS overlay nodig
- Navigatie: terug-knop is simpele `<a href>` toevoeging

**Impact:**
| Fix | Effort | Prioriteit |
|-----|--------|-----------|
| Punt verslepen | Middel (1-2 uur) | 🟠 HOOG voor Martien |
| Hogere zoom met BGT | Al gedaan in verse checkout | ✅ |
| KLIC lagen op kaart | Middel (2-3 uur, WMS overlay) | 🟠 |
| Kaart-knop altijd zichtbaar | Klein (15 min) | 🟡 |
| Terug-pijl | Klein (15 min, al deels aanwezig) | 🟡 |

**Aanbeveling:** 🔴 HOOG. Punt-versleep is een dagelijkse irritatie voor Martien. Dit eerst.

---

## 5. AHN maaiveld profiel (elke 20cm)

**Martien zegt:** "Om het maaiveld over de lengte van het profiel te laten zien, moet een lijst met coördinaten gecreëerd worden (bijv elke 20cm) en van die lijst de Z-waarden opgevraagd worden."

**Analyse:**
- Huidige aanpak: alleen MVin en MVuit (2 punten)
- Martien wil: maaiveldprofiel langs de hele boorlijn
- Nodig voor: watergangen, dijken, aardebanen zichtbaar maken in lengteprofiel
- Technisch: 226m / 0.20m = 1130 AHN5 WCS requests → te veel
- Betere aanpak: AHN5 WCS met grotere bbox → GeoTIFF → sample langs de lijn
- Of: 1 WCS request per 5m = ~45 requests (met rate limiting)

**Impact:** Dit verandert het lengteprofiel fundamenteel — maaiveldlijn wordt een golvende lijn ipv een rechte streep. Grote visuele verbetering.

**Aanbeveling:** 🟠 MIDDEL-HOOG. Significant voor de tekening maar technisch complex. Aparte taak.

---

## 6. Externe kaartlinks (waterschapskaarten werken niet)

**Martien zegt:** PDOK werkt. Waterschapskaarten niet (openen niet op locatie). Google Maps moet er ook bij. Voeg toe:
- RWS beheerzones: `geoweb.rijkswaterstaat.nl/...`
- ProRail beperkingengebied: `maps.prorail.nl/...`
- Gemeente-specifiek: bijv. `kaart.haarlem.nl/app/map/18`

**Analyse:**
- Waterschapskaarten zijn ArcGIS Experience apps — die accepteren geen coördinaten in de URL (anders dan PDOK)
- Google Maps URL is al in het model (`Order.google_maps_url`) maar niet auto-gegenereerd
- RWS/ProRail links: vaste URLs, kunnen we toevoegen
- Gemeente-specifiek: varieert per gemeente, moeilijk te automatiseren

**Mogelijke aanpak:**
- Google Maps URL auto-genereren: `https://www.google.com/maps/@{lat},{lon},17z`
- RWS + ProRail links toevoegen op vergunningscheck pagina
- Waterschapskaart: onderzoeken of er een URL-patroon is met coördinaten

**Aanbeveling:** 🟠 MIDDEL. Google Maps + RWS + ProRail links = quick win. Waterschapskaart locatie-link = onderzoek nodig.

---

## 7. Doorsneden

**Martien zegt:** "Laten we dat nog even voor wat het is, komt later wel."

**Aanbeveling:** ✅ GEEN ACTIE. Geparkeerd.

---

## 8. Gemeente-mail met KLIC screenshot + boorlijn

**Martien zegt:** "Wij zijn gewend daar een boorlijn in te tekenen in een screenshot van de KLIC." Plaatje genereren met boorlijn erin, dan automatisch versturen.

**Analyse:**
- We genereren al een situatiekaart met tracélijn voor de PDF
- Die zelfde kaart (OSM + KLIC leidingen + tracé) kan ook in de gemeente-mail
- Auto-versturen = SMTP integratie (staat op backlog)

**Aanbeveling:** 🟠 MIDDEL. Kaart-image toevoegen aan gemeente-mail concept = hergebruik bestaande `_generate_werkplan_kaart()`. SMTP later.

---

## 9. Sonderingen bronnen

**Martien zegt:** BROloket/PDOK BRO tonen mogelijk dezelfde data als Dinoloket. Dinoloket toont meer formaten. Moet nagegaan worden.

**Analyse:** Alle drie tonen BRO-data maar Dinoloket heeft ook oudere DINO-data. Voor nu zijn de link-outs voldoende.

**Aanbeveling:** 🟡 LAAG. Link-outs werken. Verificatie van overlap is kenniswerk, geen software.

---

## 10. Vergunning checklist

**Martien zegt:** "Nu is het de bedoeling dat wij zelf handmatig de checklist doorlopen, toch?" Klopt. Platform neemt dit stapsgewijs over.

**Analyse:** De checklist staat op de pagina met checkboxen. Die worden nu niet opgeslagen (alleen client-side). Opslaan in DB = eenvoudige toevoeging.

**Aanbeveling:** 🟡 LAAG. Checklist state opslaan per boring. Later automatiseren.

---

## 11. Railway 401 probleem

**Screenshot:** Railway deployment toont "401 Niet ingelogd" pagina ipv browser login popup.

**Analyse:**
- De error handler voor 401 stuurt JSON terug met `WWW-Authenticate: Basic` header
- Maar de custom error template wordt gerenderd als HTML → browser toont de HTML pagina ipv de login popup
- In de verse checkout is dit al gefixed (`bfaa5b1 Fix 401: preserve WWW-Authenticate header`)

**Aanbeveling:** 🔴 MUST FIX maar waarschijnlijk al opgelost in verse checkout. Verifiëren op Railway.

---

## 12. Topotijdreis screenshot vraag

**Martien zegt over het topotijdreis scherm:** "Dit is wel heel interessant, al vraag ik me wel af wat ik hiermee kan."

**Analyse:** Martien ziet de waarde van historische kaarten maar weet niet precies hoe hij het in zijn workflow integreert. De use case is: funderingsresten detecteren (zijn 3 gedocumenteerde cases).

**Aanbeveling:** 🟡 Geen technische actie. Uitleg/workflow documentatie in testhandleiding verbeteren.

---

## Prioritering

### Status per 21 maart 2026

| # | Item | Status |
|---|------|--------|
| F4 | Punt verslepen op kaart | ✅ Done |
| F4b | KLIC lagen op trace-kaart | ✅ Done |
| F5 | AHN maaiveldprofiel langs boorlijn (per 1m) | ✅ Done |
| F6a | Google Maps + RWS + ProRail links | ✅ Done |
| F2a | RWS/ProRail links op vergunningscheck | ✅ Done |
| F8 | Kaart-image in gemeente-mail | ✅ Done |
| F10 | Checklist opslaan in DB | ✅ Done |
| F11 | Railway 401 fix | ✅ Done (verse checkout) |
| F1 | Vergunning multi-select | 🟡 Later (Martien: "aanzien") |
| F2b | Automatische zonering-detectie | 🟡 Later |
| F3 | Omgevingsloket standaard-antwoorden | 🟡 Kenniswerk |
| F12 | Topotijdreis workflow documentatie | 🟡 Later |
| F7 | Doorsneden | Geparkeerd (Martien: "later") |
| F9 | Sonderingen bronverificatie | Kenniswerk |
