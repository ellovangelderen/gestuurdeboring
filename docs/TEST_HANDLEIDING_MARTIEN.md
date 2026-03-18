# Testhandleiding HDD Platform — Martien Luijben
**Versie: 18 maart 2026 (v2 — volledige backlog)**
**URL: http://localhost:8000** (lokaal) / **https://hdd.inodus.nl** (productie)
**Inloggen: gebruiker `martien` + wachtwoord**

---

## Hoe te testen

Werk de testscenario's hieronder af. Noteer per scenario:
- Werkt het? (ja / nee / deels)
- Wat valt op? (fouten, onduidelijkheden, suggesties)

---

## 1. Cockpit (orderoverzicht)

**Wat:** Startpagina na inloggen. Overzicht van alle orders.

| Stap | Actie | Verwacht resultaat |
|------|-------|--------------------|
| 1.1 | Open http://localhost:8000 en log in | Cockpit met ordertabel verschijnt |
| 1.2 | Bekijk de stats-balk bovenaan | Totaal, In uitvoering, Wacht akkoord tellers kloppen |
| 1.3 | Typ een ordernummer in het zoekveld | Tabel filtert op dat ordernummer |
| 1.4 | Klik "Wacht akkoord" filter | Alleen orders met die status zichtbaar |
| 1.5 | Klik "Mijn orders" filter | Alleen jouw orders (tekenaar = martien) |
| 1.6 | Wijzig sortering naar "Klant" | Tabel sorteert op klantcode |
| 1.7 | Klik "CSV" | CSV-bestand downloadt met alle zichtbare orders |
| 1.8 | Klik "+ Order" | Formulier voor nieuwe order opent |

---

## 2. Order aanmaken

| Stap | Actie | Verwacht resultaat |
|------|-------|--------------------|
| 2.1 | Klik "+ Order" in cockpit | Nieuw order formulier |
| 2.2 | Vul in: ordernummer, locatie, klantcode, 1 boring type B | Order aangemaakt, redirect naar detail |
| 2.3 | Maak een order met type Z (boogzinker) boring | Boring detail toont booghoek + stand velden |
| 2.4 | Maak een order met meerdere boringen (bijv. 2x B, 1x N) | Alle boringen zichtbaar in order detail |

---

## 3. Tracé invoeren (kaart-klik)

**Wat:** Coördinaten invoeren door op de kaart te klikken.

| Stap | Actie | Verwacht resultaat |
|------|-------|--------------------|
| 3.1 | Ga naar een boring → klik "Trace" | Kaart met formulier verschijnt |
| 3.2 | Punt A (intree) is geselecteerd (blauw). Klik op de kaart | RD X en RD Y worden automatisch ingevuld |
| 3.3 | Actief punt schuift door naar B (uittree). Klik op de kaart | B coördinaten ingevuld, rode lijn verschijnt |
| 3.4 | Klik "+ Tussenpunt toevoegen" | Nieuw punt verschijnt tussen A en B |
| 3.5 | Klik "Trace opslaan" | Redirect naar boring detail, punten opgeslagen |
| 3.6 | Ga opnieuw naar Trace | Bestaande coördinaten zijn teruggeladen |
| 3.7 | Schakel kaartlaag naar "Luchtfoto" | PDOK luchtfoto verschijnt |
| 3.8 | Schakel BGT laag aan | BGT overlay zichtbaar |

---

## 4. KLIC upload

| Stap | Actie | Verwacht resultaat |
|------|-------|--------------------|
| 4.1 | Ga naar Brondata van een boring | KLIC upload sectie zichtbaar |
| 4.2 | Upload een KLIC ZIP (bijv. HDD11 Levering_25O0136974_1.zip) | Bestand geüpload, automatisch verwerkt |
| 4.3 | Na verwerking | Tabel met beheerders + leidingtypen + aantallen |
| 4.4 | Als er EV-leidingen zijn | Rode waarschuwingsbalk "EV-leidingen aanwezig" |

---

## 5. Maaiveld (AHN5)

| Stap | Actie | Verwacht resultaat |
|------|-------|--------------------|
| 5.1 | Ga naar Brondata | Maaiveld sectie met AHN5 knop |
| 5.2 | Klik "Ophalen via AHN5" | MVin en MVuit worden automatisch ingevuld (enkele seconden) |
| 5.3 | Bron-badges tonen "ahn5" | Groene badges bij MVin en MVuit |
| 5.4 | Overschrijf handmatig (bijv. MVin = 0.85) → Opslaan | Bron wordt "handmatig", AHN5 referentiewaarde blijft zichtbaar |
| 5.5 | Bekijk "Externe kaartlinks" sectie | PDOK Viewer link + Waterschap kaartlink (automatisch gegenereerd) |

---

## 6. Boorprofiel & DXF/PDF

### Type B/N (gestuurde boring)

| Stap | Actie | Verwacht resultaat |
|------|-------|--------------------|
| 6.1 | Boring met trace + maaiveld → klik "DXF" | DXF-bestand downloadt |
| 6.2 | Open DXF in AutoCAD | Boorlijn met 2 ARCs (intree + uittree) + horizontaal segment |
| 6.3 | Controleer lagen | LP-BOORLIJN, LP-MAAIVELD, LP-MAATVOERING aanwezig |
| 6.4 | Controleer maatvoering | Intreehoek, uittreehoek, L, Rv, diepte NAP labels |
| 6.5 | Klik "PDF" | PDF downloadt als A3 landscape |
| 6.6 | Controleer PDF layout | 4 zones: links-boven (overzichtskaart + GPS + doorsnede), rechts-boven (situatiekaart met KLIC), links-onder (doorsneden + legenda), rechts-onder (lengteprofiel + titelblok) |
| 6.7 | Situatiekaart rechts-boven | OSM kaart ingezoomd op tracé, rode lijn met sensorpuntlabels, KLIC leidingen als gekleurde lijnen |
| 6.8 | Lengteprofiel rechts-onder | Vloeiende boorlijn van maaiveld naar diepte, sensorpunten langs maaiveld, doorsnede-nummers, NAP grid per 1m |
| 6.9 | Titelblok rechts-onder | 3D-Drilling + GBT logo's, projectinfo, opmerkingen, revisietabel |
| 6.10 | Overzichtskaart links-boven | Kleine OSM kaart 1:4000 met tracé in rode lijn |
| 6.11 | Doorsnede links-boven | Cirkel met ruimer (gestreept) en buis (gevuld), Dg/De labels |

### Type Z (boogzinker)

| Stap | Actie | Verwacht resultaat |
|------|-------|--------------------|
| 6.12 | Boring type Z met booghoek 10° en stand 5 → DXF | DXF met 1 ARC (geen horizontaal segment) |
| 6.13 | Controleer labels in DXF | "Booghoek 10.0 graden", "Stand 5", "Booglengte = X m" |
| 6.14 | PDF downloaden | Vereenvoudigd lengteprofiel met 1 boog |

---

## 7. Conflictcheck K&L

| Stap | Actie | Verwacht resultaat |
|------|-------|--------------------|
| 7.1 | Boring met trace + maaiveld + KLIC → Brondata → "Conflictcheck K&L" | Conflictcheck pagina opent |
| 7.2 | Stats-balk bovenaan | Totaal leidingen, aantal in corridor, categorieën |
| 7.3 | Rode sectie "Diepte onbekend" | Leidingen zonder diepte worden altijd getoond |
| 7.4 | Gele sectie "Waarschuwing" | Leidingen met 0.5-1.5m afstand |
| 7.5 | Groene sectie "Veilig" (inklapbaar) | Leidingen >1.5m afstand |
| 7.6 | Zonder KLIC upload | Melding "Geen KLIC leidingen beschikbaar" |

---

## 8. Topotijdreis (historische kaarten)

| Stap | Actie | Verwacht resultaat |
|------|-------|--------------------|
| 8.1 | Brondata → "Topotijdreis" | Kaart met tijdslider verschijnt |
| 8.2 | Sleep de slider van 2015 naar 1900 | Kaart wisselt naar historische topo van 1900 |
| 8.3 | Klik "Afspelen" | Kaart loopt automatisch door alle jaren |
| 8.4 | Rode tracélijn zichtbaar | Tracé van de boring als overlay op de historische kaart |
| 8.5 | Klik "Open in Topotijdreis.nl" | Externe topotijdreis.nl opent op de juiste locatie |
| 8.6 | Controleer of je oude objecten ziet | Gesloopte gebouwen, bruggen, waterlopen die relevant kunnen zijn |

---

## 9. GWSW Riool BOB + gemeente-mail

| Stap | Actie | Verwacht resultaat |
|------|-------|--------------------|
| 9.1 | Brondata → "Riool BOB (GWSW)" | GWSW pagina opent |
| 9.2 | Bekijk resultaat | Tabel met riooldata: naam, BOB begin/eind (NAP), materiaal, diameter |
| 9.3 | Als BOB beschikbaar | Groene teller "Met BOB data" |
| 9.4 | Als BOB niet beschikbaar | Gemeente-mail concept verschijnt |
| 9.5 | Bekijk gemeente-mail | Bevat locatie, ordernummer, RD-coördinaten |
| 9.6 | Klik "Kopieer mail" | Onderwerp + bericht gekopieerd, plak in mailprogramma |

---

## 10. Statusmail

| Stap | Actie | Verwacht resultaat |
|------|-------|--------------------|
| 10.1 | Cockpit → "Statusmail" knop | Statusmail pagina met concepten per klant |
| 10.2 | Per klant een conceptmail | "Hallo [contact], Hierbij een overzicht..." |
| 10.3 | Klik "Kopieer mail" | Onderwerp + bericht naar klembord gekopieerd |
| 10.4 | Plak in je mailprogramma | Tekst is netjes geformateerd |
| 10.5 | Klap "Alle orders tonen" open | Tabel met orders per klant + status |

---

## 11. Sleufloze leidingen

| Stap | Actie | Verwacht resultaat |
|------|-------|--------------------|
| 11.1 | Brondata → "Sleufloze leidingen" | Overzicht sleufloze leidingen uit KLIC |
| 11.2 | Stats-balk | Totaal leidingen, sleufloze (rood), mogelijk sleufloze (geel) |
| 11.3 | Rode sectie | PE/HDPE leidingen + mantelbuizen → "sleufloze techniek gedetecteerd" |
| 11.4 | Gele sectie | Stalen leidingen → "mogelijk sleufloze techniek" |
| 11.5 | Geen sleufloze | Groene melding "Geen sleufloze leidingen gedetecteerd" |
| 11.6 | Detectieregels (inklapbaar) | Uitleg materiaalregel + bijlage-heuristiek |

---

## 12. Tracévarianten vergelijken

| Stap | Actie | Verwacht resultaat |
|------|-------|--------------------|
| 12.1 | Boring detail → "Varianten" link | Varianten pagina met kaart |
| 12.2 | Hoofdtracé zichtbaar als rode lijn | Rode lijn op kaart |
| 12.3 | Klik "+ Nieuwe variant toevoegen" | Formulier opent |
| 12.4 | Klik op kaart voor alternatief A en B punt | Coördinaten worden ingevuld |
| 12.5 | "Variant opslaan" | Variant verschijnt als gestreepte blauwe lijn op kaart |
| 12.6 | Vergelijkingstabel | Lengte + delta per variant |
| 12.7 | "Verwijder" bij variant | Variant verwijderd, hoofd blijft |

---

## 13. Factuur concept (SnelStart)

| Stap | Actie | Verwacht resultaat |
|------|-------|--------------------|
| 13.1 | Order detail → "Factuur concept" | Factuur pagina opent |
| 13.2 | Factuurregels | Per boring een regel (type + locatie + lengte) |
| 13.3 | Werkplan regel | Als er type B boringen zijn |
| 13.4 | Klantgegevens | Naam, opdrachtgever, contact correct |
| 13.5 | "Kopieer" | Tekst naar klembord, plak in SnelStart |

---

## 14. Vergunningscheck

| Stap | Actie | Verwacht resultaat |
|------|-------|--------------------|
| 14.1 | Brondata → "Vergunningscheck" | Vergunningscheck pagina opent |
| 14.2 | Links naar portalen | Omgevingsloket, PDOK, BAG Viewer, Bodemloket |
| 14.3 | Klik "Open" bij Omgevingsloket | Omgevingsloket opent op de juiste coördinaten |
| 14.4 | Checklist | Afvinken welke vergunningen gecontroleerd zijn |

---

## 15. Sonderingen (DINOloket)

| Stap | Actie | Verwacht resultaat |
|------|-------|--------------------|
| 15.1 | Brondata → "Sonderingen" | Sonderingen pagina opent |
| 15.2 | Links naar DINOloket en BRO | Klik opent op juiste locatie |
| 15.3 | Werkwijze instructies | Stappen voor het opzoeken van sonderingen |

---

## 16. EV-zones

| Stap | Actie | Verwacht resultaat |
|------|-------|--------------------|
| 16.1 | Upload KLIC met EV-leidingen | Rode waarschuwing op brondata pagina |
| 16.2 | Download DXF | Laag "EV-ZONE" aanwezig met polygonen |
| 16.3 | Download PDF | EV-waarschuwing in het document |

---

## 17. As-Built revisietekeningen

| Stap | Actie | Verwacht resultaat |
|------|-------|--------------------|
| 17.1 | Boring detail → "As-Built" link | As-Built pagina opent |
| 17.2 | Ontwerp-tracé zichtbaar als grijze lijn | Grijze gestreepte lijn op kaart |
| 17.3 | Vul werkelijke meetpunten in (of klik op kaart) | Coördinaten ingevuld per punt |
| 17.4 | "As-Built opslaan" | Revisienummer verhoogd, groene lijn op kaart |
| 17.5 | Afwijkingstabel | Per punt: ontwerp vs. werkelijk + afwijking in meters |
| 17.6 | Download DXF | Bestandsnaam bevat rev.1 (of hoger) |

---

## Bekende beperkingen (optioneel, niet gebouwd)

- **GEF/CPT parser** (backlog 16) — handmatig grondtype bepalen
- **NEN 3651 berekeningen** (backlog 17) — Sigma override (handmatig invoeren)
- **SMTP statusmail** — nu kopiëren, later automatisch versturen
- **SnelStart API** — nu kopiëren, Martien voert zelf in via webportal

---

## Feedback

Noteer per scenario wat werkt en wat niet. Stuur naar Ello:
- Screenshots van fouten
- Wat je verwachtte vs. wat er gebeurde
- Suggesties voor verbetering
