# Architect Input — HDD Ontwerp Platform
**LeanAI Platform · Architect Agent input document**
Versie: 3.1 | 2026-03-13

---

## 1. Projectdoel en scope

Digitaal platform voor de voorbereiding van gestuurde boringen (HDD). Gebouwd door Inodus voor een klant in de HDD-engineeringsector (klein team, 2–5 engineers).

**Scope: uitsluitend engineeringvoorbereiding.** Uitvoering door aannemer, calculatie en offerte zijn expliciet buiten scope — alle iteraties.

**Kernoutput (altijd):** PDF tekening + DWG tekening
**Optionele output:** berekeningen, werkplan (iteratie 2+)

---

## 2. Alle genomen beslissingen

| Beslissing | Keuze | Reden |
|---|---|---|
| Hosting | Railway — hdd.inodus.nl | Inodus beheert, klant betaalt licentie/onderhoud |
| Database | PostgreSQL (Railway managed) | Direct productie-ready, geen SQLite |
| Datamodel | Workspace structuur in database | Gestructureerde scheiding van data per omgeving |
| Aantal gebruikers v1 | Klein team 2–5 engineers | Geen zware infra nodig |
| AI tekstgeneratie | Niet in iteratie 1 | Weinig waarde t.o.v. bouwkost |
| Async job queue | Niet in iteratie 1 | Synchroon is goed genoeg voor klein team |
| Gebruikersrollen | Niet in iteratie 1 | Iedereen kan alles, rollen in iteratie 2 |
| BGT API | Niet in iteratie 1 | Engineer gebruikt OSM achtergrond |
| Berekeningen | Niet in iteratie 1 | Engineer rekent buiten systeem in iteratie 1 |
| Calculatie/offerte | Nooit — alle iteraties | Expliciet buiten scope door opdrachtgever |

---

## 3. Hosting architectuur

```
GitHub (hdd-platform repo)
        ↓ git push main → GitHub Actions (deploy.yml)
Railway
  ├── Web service     Docker container (FastAPI backend + React frontend)
  ├── PostgreSQL      Managed database — Railway plugin
  └── Volume          Bestandsopslag iteratie 1 (later S3)

URL:  hdd.inodus.nl
DNS:  CNAME hdd → [railway-url].railway.app
      Beheerd in Netlify DNS (zelfde DNS als inodus.nl landingspagina)
```

**Kosten:** ~$5–15/maand op Railway afhankelijk van gebruik. Valt ruim binnen licentie/onderhoudsfee van de klant.

---

## 4. Iteratieplan

### Iteratie 1 — Werkende kern

**Wat het doet:**
- Project aanmaken en beheren
- KLIC GML uploaden + leidingen tonen op kaart (Leaflet + OSM)
- Start/eindpunt vastleggen op kaart
- Te kruisen object definiëren + eisenprofiel selecteren
- HDD design engine: boorcurve berekenen + conflict check
- Ontwerp tonen in bovenaanzicht + lengteprofiel
- Handmatig aanpassen + herberekenen
- PDF tekening genereren
- DWG tekening genereren
- Eenvoudige login (JWT, geen rollen)

**Wat de engineer handmatig doet:**
- KLIC aanvragen bij Kadaster, GML bestanden uploaden
- Werkplan zelf schrijven (systeem levert parameters)

**Expliciet niet in iteratie 1:**
AI, async queue, BGT API, berekeningen, gebruikersrollen, versiebeheer, werkplan generator

### Iteratie 2

BGT API, werkplan template, basis berekeningen (intrekkracht, buigstraal), versiebeheer ontwerp, gebruikersrollen

### Iteratie 3

AI werkplanteksten, eisenprofiel beheerscherm, volledige berekeningen (sterkte, slurrydruk), audittrail

---

## 5. Stack iteratie 1

| Laag | Keuze |
|---|---|
| Frontend | React + Vite |
| Kaart | Leaflet + OpenStreetMap |
| Backend | Python FastAPI |
| Database | PostgreSQL + PostGIS (Railway) |
| File opslag | Railway volumes |
| PDF | WeasyPrint |
| DWG | ezdxf |
| Auth | FastAPI JWT |
| CI/CD | GitHub Actions → Railway |

---

## 6. Workspace

De applicatie werkt met een workspace als organisatorische eenheid. Alle data — projecten, gebruikers, eisenprofielen, documenten — is gekoppeld aan een workspace.

**Tabel Workspace:** `id`, `naam`, `slug`

**Kolom `workspace_id`** op: `Project`, `Gebruiker`, `EisenProfiel`, `OutputDocument`

**Middleware:** `get_current_workspace()` in FastAPI core — filtert automatisch alle queries op de juiste workspace

**In iteratie 1:** één workspace, aangemaakt via seed script bij deployment.

---

## 7. Datamodel iteratie 1

```
Workspace
  └── id (UUID), naam, slug, aangemaakt_op

Gebruiker
  ├── id (UUID), workspace_id, naam, email, wachtwoord_hash
  └── aangemaakt_op

Project
  ├── id (UUID), workspace_id
  ├── naam, opdrachtgever, locatie_omschrijving
  ├── type_leiding (elektriciteit/gas/water/telecom/warmte/overig)
  ├── status (concept/ontwerp/review/opgeleverd)
  ├── aangemaakt_door (user_id), aangemaakt_op, gewijzigd_op
  │
  ├── Locatie
  │     └── startpunt_x, startpunt_y, eindpunt_x, eindpunt_y (WGS84)
  │
  ├── KlicUpload[]
  │     ├── bestandsnaam, bestandspad, geupload_op
  │     └── verwerkt (bool)
  │
  ├── TeKruisenObject
  │     ├── type (weg/water/spoor/waterkering/overig)
  │     ├── naam, breedte_m, eisenprofiel_id
  │
  ├── NieuwLeiding
  │     ├── materiaal (PE/staal/PVC/HDPE/overig)
  │     ├── buitendiameter_mm, wanddikte_mm
  │     ├── max_trekkracht_kn, min_boogstraal_m
  │     └── met_mantelbuis (bool)
  │
  ├── Ontwerp
  │     ├── status (concept/akkoord/waarschuwing/afkeur)
  │     ├── boorcurve_wkt (WKT LineString)
  │     ├── boorlengte_m, max_diepte_m
  │     ├── boogstraal_m, entry_angle_deg, exit_angle_deg
  │     ├── aangemaakt_op, herberekend_op
  │     └── Conflicten[]
  │           ├── klic_object_id, klic_type, klic_beheerder
  │           ├── afstand_m, diepte_leiding_m
  │           └── ernst (info/waarschuwing/kritiek)
  │
  └── OutputDocument[]
        ├── type (pdf_tekening/dwg_tekening), workspace_id
        ├── bestandspad, versie, gegenereerd_op

EisenProfiel
  ├── id, naam, workspace_id (null = globaal)
  ├── beheerder_type, object_type
  └── min_diepte_m, beschermingszone_m, min_boogstraal_m

Seed data eisenprofielen (hardcoded iteratie 1):
  - RWS Rijksweg: min_diepte 3.0m, bescherming 5.0m, boogstraal 150m
  - Waterschap Waterkering: min_diepte 5.0m, bescherming 10.0m, boogstraal 200m
  - Provincie Provinciale weg: min_diepte 2.0m, bescherming 3.0m, boogstraal 120m
  - Gemeente Gemeenteweg: min_diepte 1.2m, bescherming 1.5m, boogstraal 100m
```

---

## 8. HDD design engine

Deterministisch algoritme — geen AI.

**Input:** startpunt, eindpunt, te kruisen object (type, breedte, positie), eisenprofiel, leidingparameters, entry angle voorkeur (standaard 10–12°)

**Berekening:**
1. Benodigde diepte = eisenprofiel.min_diepte
2. Boogstraal = max(eisenprofiel.min_boogstraal, leiding.min_boogstraal)
3. Intree-segment op basis van entry angle + boogstraal
4. Horizontaal segment over obstakel + beschermingszones
5. Uittree-segment = spiegeling intree
6. Curve als WKT LineString
7. Conflict check: minimale afstand boorcurve tot elke KLIC-leiding

**Output:** boorcurve (WKT), parameters, conflictenlijst, status (akkoord / waarschuwing <0.5m / kritiek <0.1m)

---

## 9. MoSCoW backlog iteratie 1

### Must have

**Projectbeheer**
- Project aanmaken (naam, opdrachtgever, locatie, type leiding)
- Projectenoverzicht met status
- Project openen en bewerken
- Inloggen met eigen account

**Brondata**
- KLIC GML uploaden en leidingen tonen op kaart
- Start- en eindpunt vastleggen op kaart

**Eisen**
- Te kruisen object definiëren (type, breedte)
- Eisenprofiel selecteren per beheerder

**Ontwerp**
- Boorcurve automatisch berekenen
- Ontwerp-parameters tonen (lengte, diepte, boogstraal, hoeken)
- Conflicten markeren op kaart
- Handmatig aanpassen en herberekenen
- Bovenaanzicht + lengteprofiel tonen

**Output**
- PDF tekening genereren (titelblok + situatietekening + profiel)
- DWG tekening genereren (met lagenstructuur)

### Should have (iteratie 2)

BGT ophalen via PDOK API · werkplan template · intrekkracht berekening · versiebeheer ontwerp · gebruikersrollen

### Could have (iteratie 3)

AI werkplanteksten · eisenprofiel beheerscherm · sterkte- en slurrydrukberekening · audittrail

### Won't have (alle iteraties)

Calculatiemodule · offertemodule · geautomatiseerde KLIC-aanvraag · 3D visualisatie · koppeling financieel pakket

---

## 10. Acceptatiecriteria iteratie 1

- Engineer logt in op `hdd.inodus.nl`
- Maakt project aan, uploadt KLIC GML, ziet leidingen op kaart
- Legt start/eindpunt vast, selecteert eisenprofiel
- Ziet automatisch berekende boorcurve + conflictmarkeringen
- Ziet lengteprofiel (zijaanzicht)
- Past parameters aan en herberekent
- Downloadt PDF tekening met titelblok, situatietekening en profiel
- Downloadt DWG tekening met lagenstructuur
- Twee engineers kunnen gelijktijdig inloggen en werken

---

## 11. Openstaande vragen voor Architect Agent

1. **DWG lagenstructuur:** welke standaard laagnamen verwacht de klant? (bijv. HDD-BORING, HDD-KLIC-ELEKTRA, HDD-KLIC-GAS, HDD-OBJECT)
2. **PDF titelblok:** zijn er vaste velden die de klant vereist? Logo, projectnummer, revisieveld?
3. **Eisenprofielen seed data:** zijn de vier standaard profielen (RWS/waterschap/provincie/gemeente) voldoende voor de eerste oplevering?

---

*LeanAI Platform · Inodus · architect-input v3.1 · 2026-03-13*
