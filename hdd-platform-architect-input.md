# Architect Input — HDD Ontwerp Platform
**LeanAI Platform · Architect Agent input document**
Versie: 1.0 | Datum: 2026-03-12 | Opgesteld voor: LeanAI Architect Agent

---

## 1. Projectdoel en scope

Bouw een digitaal engineering platform voor het voorbereiden van gestuurde boringen (HDD — Horizontal Directional Drilling). Het platform ondersteunt het volledige engineering voorbereidingsproces: van project intake tot oplevering van tekeningen, berekeningen en een werkplan aan de aannemer.

**De scope is uitsluitend de voorbereidingsfase.** De daadwerkelijke uitvoering van de boring door een aannemer valt buiten scope. Calculatie en offertemodules zijn expliciet buiten scope gesteld door de opdrachtgever.

**Kernoutput van het platform (altijd):**
- PDF tekening (situatietekening + lengteprofiel)
- DWG tekening (met lagenstructuur voor gebruik in AutoCAD)

**Optionele output (afhankelijk van opdrachtgever of vergunningverlener):**
- Technische berekeningen (sterkte, intrekkracht, boorvloeistofdruk)
- Werkplan / boorplan (Word of PDF)

---

## 2. Domeinkennis voor de Architect

### Wat is een gestuurde boring (HDD)?

Bij HDD worden kabels en leidingen aangelegd zonder te graven door middel van gestuurde boortechnieken — onder wegen, water, spoorlijnen en waterkeringen door. Toepassingen: glasvezel, water, gas, elektriciteit.

Voor zulke boringen is vaak een vergunning nodig (gemeente, Rijkswaterstaat, waterschap). De vergunningverlener vraagt een werkplan / boorplan als bijlage bij de aanvraag.

### Hoe werkt het ontwerp van een HDD boring?

Een engineer ontwerpt een boortracé in 2D (situatietekening bovenaanzicht + lengteprofiel zijaanzicht) waarbij:
- start- en eindpunt bepaald worden
- diepte onder het te kruisen object vastgesteld wordt op basis van eisen van de beheerder
- boogstralen berekend worden op basis van leidingmateriaal en boormachine
- conflicten met bestaande kabels en leidingen (KLIC-data) vermeden worden

### Kritische brondata

**KLIC (Kadaster):** Bestaande kabels en leidingen in de ondergrond. Wordt aangevraagd bij Kadaster en opgeleverd als GML-bestanden. Bevat: elektriciteit, gas, telecom, water, riool — met geometrie, diepte en beheerder.

**BGT (Basisregistratie Grootschalige Topografie):** Open topografische data van Kadaster. Bevat: wegen, water, spoor, gebouwen, taluds. Beschikbaar via open API.

### Eisen per beheerder (voorbeelden)

| Beheerder | Type object | Min. diepte | Bijzonderheden |
|---|---|---|---|
| Rijkswaterstaat | Rijksweg | 3 m onder fundering | Beschermingszone 5 m buiten weg |
| Waterschap | Waterkering | 5–10 m onder dijkkern | Projectspecifiek bepaald |
| Gemeente | Gemeenteweg | 1–1,5 m | Afhankelijk van gemeente |
| ProRail | Spoorlijn | 3–5 m | Specifieke toestemming vereist |

### Technische berekeningen (optioneel)

- **Sterktecontrole:** toelaatbare trekspanning in leiding, combinatie van trek + buiging, controle op materiaalgrenzen (PE, staal).
- **Intrekkracht (pullback force):** modelleert weerstand langs het tracé op basis van leidinggewicht, boogstralen, wrijving, boorvloeistofdruk.
- **Boorvloeistofdruk (mud pressure):** hydrostatische druk, annulaire druk, risico op frac-out / uitspoeling.

---

## 3. Gebruikersrollen

| Rol | Verantwoordelijkheden |
|---|---|
| Werkvoorbereider | Project aanmaken, brondata invoeren, output selecteren |
| Engineer / ontwerper | Ontwerp beoordelen en aanpassen, berekeningen valideren, tekeningen accorderen |
| Beheerder | Eisenprofielen beheren, templates beheren, gebruikers beheren |

---

## 4. Systeem workflow (7 stappen)

```
1. Project intake        → naam, opdrachtgever, locatie, type leiding, gewenste output
        ↓
2. Brondata              → KLIC GML upload, BGT ophalen, DWG upload (optioneel)
        ↓
3. Eisen laden           → eisenprofiel per beheerder (RWS / waterschap / gemeente)
        ↓
4. Ontwerp genereren     → boorcurve, tracé, conflict check met KLIC
        ↓
5. Review + aanpassen    → engineer beoordeelt, past aan, herberekent
        ↓
6. Berekeningen          → optioneel: trek, sterkte, slurrydruk
        ↓
7. Output genereren      → PDF tekening, DWG tekening, werkplan, berekening
        ↓
   Oplevering aan aannemer (buiten scope van dit systeem)
```

---

## 5. Systeemarchitectuur (LeanAI aanpak)

### Architectuurprincipes

- Modulaire monoliet als startvorm — geen microservices in MVP
- Duidelijke scheiding tussen domeinlogica, integraties en UI
- AI alleen inzetten voor tekst (werkplan, toelichtingen) — niet voor kernberekeningen
- Berekeningen zijn deterministisch en expliciet gemodelleerd in een rule/calculation engine
- Data één keer invoeren, daarna hergebruiken in alle stappen
- Output altijd gegenereerd uit gestructureerde projectdata via templates

### Technische stack (aanbevolen)

| Laag | Technologie |
|---|---|
| Frontend | React / Next.js, kaartcomponent (Leaflet of MapLibre) |
| Backend API | Python FastAPI |
| Database | PostgreSQL met PostGIS extensie |
| File storage | S3-compatibele object storage |
| Async jobs | Background job queue (Celery of ARQ) voor PDF/DWG generatie |
| DWG output | ezdxf (Python library) |
| PDF output | WeasyPrint of ReportLab |

### Vijf domeinservices

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React)                          │
│  Intake wizard · Kaart + brondata · Ontwerp review · Output  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│          Application API (FastAPI) — orkestratie             │
│          Auth · Workflow · Versiebeheer · Projectstatus       │
└─┬──────────┬────────────┬────────────┬───────────┬──────────┘
  │          │            │            │           │
  ▼          ▼            ▼            ▼           ▼
Geo &     Rule          HDD         Doc &       AI
Brondata  Engine        Design      Drawing     Assist
Service               Engine      Generator
KLIC/BGT  Eisen per    Tracé +     PDF · DWG   Werkplan-
DWG imp.  beheerder    conflict    Berekening  teksten
normalis. RWS/WS/gem.  check       Werkplan
  │          │            │            │
  └──────────┴────────────┴────────────┘
                    │
┌───────────────────▼─────────────────────────────────────────┐
│  PostgreSQL/PostGIS  │  File Storage (S3)  │  Async Queue    │
└─────────────────────────────────────────────────────────────┘
```

### Datamodel (hoofdobjecten)

```
Project
  ├── Locatie (coordinaten, startpunt, eindpunt, tracégebied)
  ├── Brondata (KLIC bestanden, BGT objecten, DWG uploads)
  ├── TeKruisenObject (type, naam, breedte, eisenprofiel)
  ├── NieuwLeiding (materiaal, diameter, wanddikte, limieten)
  ├── Ontwerp (curve, parameters, status, versie)
  │     ├── Ontwerpparameters (lengte, diepte, boogstraal, angles)
  │     └── Conflicten (lijst van KLIC-conflicten met afstand)
  ├── Berekening (optioneel — sterkte, trek, slurry)
  └── OutputDocumenten (PDF, DWG, werkplan, berekening)

EisenProfiel (beheerd door admin)
  └── Regels (min_diepte, beschermingszone, etc.)

Gebruiker
  └── Rol (werkvoorbereider / engineer / beheerder)
```

---

## 6. Epics en User Stories (MoSCoW)

---

### Epic 1 — Projectbeheer

**Must have**

- Als werkvoorbereider wil ik een nieuw project aanmaken met projectnaam, opdrachtgever, locatie en type leiding, zodat alle vervolgstappen aan het juiste project gekoppeld zijn.
- Als werkvoorbereider wil ik de status van een project kunnen bijhouden (concept → ontwerp → review → opgeleverd), zodat ik altijd weet waar een project staat.
- Als werkvoorbereider wil ik een overzicht zien van alle projecten met status en datum, zodat ik snel het juiste project kan openen.
- Als engineer wil ik een bestaand project kunnen openen en verder bewerken, zodat ik het ontwerp kan aanvullen of aanpassen.

**Should have**

- Als werkvoorbereider wil ik een project kunnen kopiëren als nieuwe versie, zodat ik variantstudies kan maken zonder het origineel te overschrijven.
- Als engineer wil ik revisies van een ontwerp kunnen bewaren met datum en omschrijving, zodat wijzigingen traceerbaar zijn.

**Could have**

- Als beheerder wil ik meerdere boringen binnen één project kunnen aanmaken, zodat projecten met meerdere kruisingen op één plek beheerd kunnen worden.

**Won't have (deze fase)**

- Koppeling met extern projectmanagementsysteem.
- Tijdregistratie per project.

---

### Epic 2 — Locatie en brondata

**Must have**

- Als werkvoorbereider wil ik een locatie kunnen selecteren via kaart, adres of coördinaten, zodat het projectgebied precies vastgelegd is.
- Als werkvoorbereider wil ik start- en eindpunt van de boring kunnen vastleggen op de kaart, zodat het tracégebied duidelijk is voor het ontwerp.
- Als werkvoorbereider wil ik een KLIC GML-bestand kunnen uploaden, zodat bestaande kabels en leidingen in het ontwerp meegenomen worden.
- Als engineer wil ik de geïmporteerde KLIC-objecten op de kaart zien met type, beheerder en bekende diepte, zodat ik conflicten kan beoordelen.
- Als werkvoorbereider wil ik BGT-data kunnen ophalen voor het projectgebied, zodat wegen, water, spoor en gebouwen zichtbaar zijn als achtergrond.

**Should have**

- Als engineer wil ik een bestaande DWG of DXF tekening kunnen uploaden als projecttekening, zodat bestaande ontwerpen als basis gebruikt kunnen worden.
- Als engineer wil ik ontbrekende of incomplete KLIC-data gesignaleerd krijgen, zodat ik weet waar gegevens handmatig aangevuld moeten worden.
- Als engineer wil ik de diepte van een bestaande leiding handmatig kunnen corrigeren, zodat ik met juiste gegevens kan ontwerpen als de KLIC-diepte onbekend is.

**Could have**

- Als werkvoorbereider wil ik BGT en KLIC-data automatisch kunnen ophalen op basis van het ingetekende tracégebied zonder handmatige exportstap.

**Won't have (deze fase)**

- Geautomatiseerde KLIC-melding indienen bij het Kadaster vanuit de applicatie.

---

### Epic 3 — Te kruisen object en eisen

**Must have**

- Als engineer wil ik het te kruisen object kunnen definiëren (weg, water, spoor, waterkering), zodat de juiste minimale eisen automatisch geladen worden.
- Als engineer wil ik een eisenprofiel kunnen laden per beheerder (Rijkswaterstaat, provincie, waterschap, gemeente), zodat de minimumeisen voor diepte, afstand en boogstraal automatisch ingevuld zijn.
- Als engineer wil ik de breedte en naam van het te kruisen object kunnen opgeven, zodat de ontwerpcurve de juiste horizontale marge aanhoudt.

**Should have**

- Als beheerder wil ik eisenprofielen kunnen beheren en aanpassen in een beheerscherm, zodat nieuwe of gewijzigde normen zonder code-aanpassing doorgevoerd kunnen worden.
- Als engineer wil ik projectspecifieke aanvullende eisen kunnen invoeren bovenop het gekozen profiel, zodat bijzondere opdrachtgeverseisen ook meegenomen worden.

**Could have**

- Als engineer wil ik meerdere te kruisen objecten in één boring kunnen definiëren, zodat complexe tracés met meerdere obstakels ondersteund worden.

**Won't have (deze fase)**

- Automatische toetsing aan Europese of internationale HDD-normen.

---

### Epic 4 — HDD ontwerp engine

**Must have**

- Als engineer wil ik op basis van locatie, brondata en eisenprofiel een automatisch gegenereerde boorcurve zien, zodat ik niet handmatig een tracé hoef te tekenen.
- Als engineer wil ik de berekende ontwerp-parameters zien (boorlengte, maximale diepte, boogstraal, entry angle, exit angle), zodat ik het ontwerp direct kan beoordelen.
- Als engineer wil ik waarschuwingen zien wanneer het ontwerp een conflict heeft met bestaande kabels of leidingen, zodat ik gerichte aanpassingen kan maken.
- Als engineer wil ik het ontwerp handmatig kunnen aanpassen en daarna opnieuw laten doorrekenen, zodat ik de uiteindelijke keuze zelf kan maken.

**Should have**

- Als engineer wil ik het ontwerp zien in zowel bovenaanzicht als zijaanzicht (lengteprofiel), zodat de boring in twee vlakken beoordeeld kan worden.
- Als engineer wil ik de minimale vrije ruimte tot bestaande leidingen zien als getal en als kleurcodering in de kaartweergave, zodat ik snel zie waar het krap is.
- Als engineer wil ik een statusindicatie van het ontwerp zien (akkoord / waarschuwing / afkeur) op basis van de uitgevoerde controles.

**Could have**

- Als engineer wil ik meerdere ontwerpalternatieven naast elkaar kunnen bewaren en vergelijken, zodat ik de beste variant kan kiezen.
- Als engineer wil ik automatisch een optimale entry- en exitzone voorgesteld krijgen op basis van de beschikbare ruimte.

**Won't have (deze fase)**

- Volledige 3D visualisatie van het boortracé.
- Optimalisatie-algoritme dat automatisch de kortste of goedkoopste route berekent.

---

### Epic 5 — Technische berekeningen (optioneel per project)

**Must have**

- Als engineer wil ik een sterktecontrole kunnen uitvoeren op de aan te leggen leiding, zodat ik kan aantonen dat de leiding de trekbelasting aankan.
- Als engineer wil ik de intrekkracht (pullback force) kunnen berekenen op basis van boorlengte, diameter, boogstralen en wrijvingsfactoren, zodat de boorinstallatie op juiste capaciteit gekozen wordt.
- Als engineer wil ik de boorvloeistofdruk kunnen berekenen en een risico-indicatie op frac-out krijgen, zodat ik kan beoordelen of de bodem de druk aankan.

**Should have**

- Als engineer wil ik de berekeningsresultaten gekoppeld zien aan de bijbehorende ontwerpparameters, zodat bij een ontwerpwijziging duidelijk is welke berekeningen opnieuw uitgevoerd moeten worden.
- Als engineer wil ik een waarschuwing krijgen wanneer een berekende waarde buiten de norm valt, zodat ik direct zie welke parameters aangepast moeten worden.

**Could have**

- Als engineer wil ik de berekeningen kunnen uitvoeren voor verschillende leidingmaterialen (PE, staal, PVC), zodat ik alternatieven door kan rekenen.

**Won't have (deze fase)**

- Gecertificeerde eindberekening die direct als formeel ingenieursdocument ingediend kan worden zonder review.

---

### Epic 6 — Document en tekeningleverancier

**Must have**

- Als engineer wil ik een PDF tekening kunnen genereren met titelblok, situatietekening, lengteprofiel, maatvoering en legenda, zodat ik een indienbaar document heb voor vergunning of opdrachtgever.
- Als engineer wil ik een DWG tekening kunnen genereren met correcte lagenstructuur, zodat de output verder bewerkt kan worden in AutoCAD.
- Als engineer wil ik de gewenste outputbestanden per project kunnen kiezen (PDF, DWG, berekening, werkplan), zodat alleen relevante documenten gegenereerd worden.

**Should have**

- Als engineer wil ik een automatisch samengesteld werkplan / boorplan kunnen genereren op basis van projectgegevens en ontwerp, zodat ik niet handmatig een document hoef te schrijven.
- Als engineer wil ik gegenereerde documenten per versie kunnen bewaren en terugvinden, zodat ik altijd bij een eerdere versie kan.
- Als beheerder wil ik een documenttemplate kunnen instellen per opdrachtgever, zodat de output direct voldoet aan de indieningsvereisten van die opdrachtgever.

**Could have**

- Als engineer wil ik het werkplan automatisch laten aanvullen door AI op basis van projectgegevens en ontwerptoelichting, zodat de tekstuele secties al grotendeels gevuld zijn.
- Als engineer wil ik een DXF export als extra formaat naast DWG, zodat de output ook bruikbaar is in andere CAD-pakketten.

**Won't have (deze fase)**

- Directe indiening van vergunningdocumenten via een API-koppeling met gemeente of Rijkswaterstaat.
- Automatisch genereren van een verkeersplan of BLVC-plan.

---

### Epic 7 — Gebruikersbeheer en instellingen

**Must have**

- Als beheerder wil ik gebruikers kunnen aanmaken met een rol (werkvoorbereider, engineer, beheerder), zodat toegang per functie geregeld is.
- Als gebruiker wil ik kunnen inloggen met een eigen account, zodat projecten en documenten aan de juiste persoon gekoppeld zijn.

**Should have**

- Als beheerder wil ik eisenprofielen en normbibliotheeken kunnen beheren, zodat nieuwe beheerderseisen zonder software-update doorgevoerd kunnen worden.

**Could have**

- Als beheerder wil ik een audittrail kunnen inzien van wijzigingen per project, zodat ik achteraf kan zien wie wat wanneer aangepast heeft.

**Won't have (deze fase)**

- SSO-koppeling met externe identity providers.
- Fijnmazige rechtenstructuur op documentniveau.

---

## 7. MVP scope (release 1)

De eerste release bevat uitsluitend de Must Have stories uit de volgende epics:

| Epic | In MVP |
|---|---|
| Epic 1 — Projectbeheer | Ja — Must have |
| Epic 2 — Locatie en brondata | Ja — Must have |
| Epic 3 — Te kruisen object en eisen | Ja — Must have |
| Epic 4 — HDD ontwerp engine | Ja — Must have |
| Epic 5 — Berekeningen | Ja — Must have (optionele module, aan/uit per project) |
| Epic 6 — Document en tekening | Ja — Must have (PDF + DWG verplicht) |
| Epic 7 — Gebruikersbeheer | Ja — Must have |

Should have, Could have en Won't have stories zijn expliciet buiten MVP scope.

---

## 8. Openstaande architectuurvragen voor de Architect Agent

De volgende punten zijn nog niet definitief besloten en moeten door de Architect Agent uitgewerkt of bevraagd worden:

1. **KLIC import:** Alleen handmatige GML upload in MVP, of ook geautomatiseerde BGT API-aanroep in dezelfde release?
2. **DWG kwaliteit:** Welk niveau van titelblok en lagenstructuur is minimaal vereist voor vergunningindiening? Zijn er referentie-DWG templates beschikbaar?
3. **Meerdere boringen per project:** Must have voor MVP of explicitly later?
4. **Eisenprofiel beheer:** Worden de eerste eisenprofielen hardcoded in de engine meegeleverd, of direct via een beheerscherm configureerbaar?
5. **AI werkplan:** In welke stap wordt AI ingezet — volledig automatisch bij output genereren, of als optionele actie door de engineer?
6. **Hosting:** Doelomgeving voor MVP — on-premise bij klant, cloud (AWS/Azure/GCP), of Antagonist-achtige VPS?

---

*Dit document is opgesteld als input voor de LeanAI Architect Agent. De Architect Agent wordt gevraagd op basis van dit document een volledig architectuurdocument op te stellen inclusief: component diagram, API design, datamodel, integratiepunten en MVP bouwplan.*
